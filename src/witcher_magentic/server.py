"""Local dashboard API. Streams one isolated, cancellable workflow per request."""
import asyncio
import contextlib
import json
import os
import hmac
from pathlib import Path

from aiohttp import ClientSession, ClientTimeout, web
from agent_framework import AgentResponse, AgentResponseUpdate
from dotenv import load_dotenv

from witcher_magentic.agents import build_magentic_workflow
from witcher_magentic.model_client import create_model_client
from witcher_magentic.telemetry import Trace, readable


@web.middleware
async def run_access(request, handler):
    if request.path != "/api/run":
        return await handler(request)
    key = os.getenv("APP_ACCESS_KEY", "")
    supplied = request.headers.get("Authorization", "")
    if key and not hmac.compare_digest(supplied.encode(), f"Bearer {key}".encode()):
        return web.json_response({"error": "Enter the test access key to start a live run."}, status=401)
    lock = request.app[RUN_LOCK]
    if lock.locked():
        return web.json_response({"error": "A hunt is already running. Try again shortly."}, status=429)
    async with lock:
        return await handler(request)


RUN_LOCK = web.AppKey("run_lock", asyncio.Lock)


async def health(request):
    provider = os.getenv("MODEL_PROVIDER", "ollama").lower()
    model = os.getenv("OLLAMA_MODEL", "qwen3:8b") if provider == "ollama" else os.getenv("FOUNDRY_MODEL", "Not configured")
    ready, detail = False, "Configure a model in .env."
    if provider == "ollama":
        endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/v1/")
        try:
            async with ClientSession(timeout=ClientTimeout(total=2)) as session:
                async with session.get(endpoint.rstrip("/") + "/models") as response:
                    response.raise_for_status()
                    models = await response.json()
                    ready = model in [item["id"] for item in models.get("data", [])]
                    detail = "Local model ready" if ready else f"Download the model: ollama pull {model}"
        except Exception:
            detail = "Start Ollama, then refresh the connection."
    elif provider == "foundry":
        ready = bool((os.getenv("FOUNDRY_ENDPOINT") or os.getenv("FOUNDRY_PROJECT_ENDPOINT")) and os.getenv("FOUNDRY_MODEL"))
        detail = "Configured; credentials checked when a run starts" if ready else detail
    return web.json_response(dict(provider=provider, model=model, ready=ready, detail=detail,
                                  access_required=bool(os.getenv("APP_ACCESS_KEY"))))


async def stream_run(request):
    try:
        body = await request.json()
        monster = body.get("monster", "").strip()
        if not monster or len(monster) > 120:
            raise ValueError()
    except (ValueError, AttributeError, TypeError):
        return web.json_response({"error": "Enter a monster name between 1 and 120 characters."}, status=400)

    response = web.StreamResponse(headers={"Content-Type": "application/x-ndjson", "Cache-Control": "no-store"})
    await response.prepare(request)
    queue = asyncio.Queue()
    trace = Trace(queue)

    async def produce():
        final = ""
        try:
            async with asyncio.timeout(int(os.getenv("RUN_TIMEOUT_SECONDS", "180"))):
                trace.emit("run_start", title=f"Preparing for {monster}")
                workflow = build_magentic_workflow(create_model_client(), trace)
                async for event in workflow.run(f"Prepare a Witcher encounter plan for a {monster}.", stream=True):
                    if event.type == "magentic_orchestrator":
                        data = event.data
                        content = data.content
                        trace.emit("decision", title=data.event_type.value.replace("_", " ").capitalize(),
                                   text=getattr(content, "text", None) or readable(content))
                    elif event.type == "output" and isinstance(event.data, (AgentResponse, AgentResponseUpdate)):
                        if isinstance(event.data, AgentResponse):
                            final = event.data.text or final
                        else:
                            final += event.data.text or ""
                if not final:
                    raise RuntimeError("The workflow ended without a final answer. Try a stronger model.")
                trace.emit("final", title="Encounter plan", text=final)
        except Exception as exc:
            trace.emit("error", title="Run could not finish", text=f"{type(exc).__name__}: {str(exc)[:1500]}")
        finally:
            queue.put_nowait(None)

    task = asyncio.create_task(produce())
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=2)
            except TimeoutError:
                await response.write(b"\n")  # Detect closed browsers even during a model call.
                continue
            if event is None:
                break
            await response.write((json.dumps(event) + "\n").encode())
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    return response


def create_app():
    app = web.Application(client_max_size=4096, middlewares=[run_access])
    app[RUN_LOCK] = asyncio.Lock()
    app.router.add_get("/api/health", health)
    app.router.add_post("/api/run", stream_run)
    # Installed packages have a different path than an editable local checkout.
    default_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    dist = Path(os.getenv("FRONTEND_DIST", str(default_dist)))
    if dist.exists():
        async def index(request):
            return web.FileResponse(dist / "index.html")
        app.router.add_get("/", index)
        app.router.add_static("/assets/", dist / "assets")
    return app


def main():
    load_dotenv()
    if os.getenv("REQUIRE_ACCESS_KEY") == "true" and not os.getenv("APP_ACCESS_KEY"):
        raise RuntimeError("APP_ACCESS_KEY must be configured for this deployment.")
    web.run_app(create_app(), host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))


if __name__ == "__main__":
    main()
