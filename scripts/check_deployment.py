"""Check the actual HTTPS app, paid-run gate, tools and final model output."""
import argparse
import asyncio
import json
from pathlib import Path

from aiohttp import ClientSession, ClientTimeout

parser = argparse.ArgumentParser()
parser.add_argument("url")
parser.add_argument("--require-parallel", action="store_true")
args = parser.parse_args()


async def main():
    base = args.url.rstrip("/")
    async with ClientSession(timeout=ClientTimeout(total=220)) as session:
        async with session.get(base) as response:
            response.raise_for_status()
            assert "<div id=\"root\">" in await response.text(), "UI not served"
        async with session.get(base + "/api/health") as response:
            response.raise_for_status()
            health = await response.json()
            print("Health:", health, flush=True)
            assert health["ready"] and health["access_required"]
        async with session.post(base + "/api/run", json={"monster": "Katakan"}) as response:
            assert response.status == 401, "Unauthenticated paid run was not blocked"
            print("Unauthenticated paid run blocked.", flush=True)
        headers = {"Authorization": "Bearer " + Path(".azure/test-access.txt").read_text().strip()}
        kinds = []
        tools = []
        starts, ends, manager_starts = {}, {}, []
        async with session.post(base + "/api/run", json={"monster": "Katakan"}, headers=headers) as response:
            response.raise_for_status()
            async for line in response.content:
                if not line.strip():
                    continue
                event = json.loads(line)
                kinds.append(event["kind"])
                if event["kind"] == "agent_start":
                    if event["agent"] == "MagenticManager":
                        manager_starts.append(event["elapsed"])
                    else:
                        starts[event["agent"]] = event["elapsed"]
                if event["kind"] == "agent_end" and event["agent"] != "MagenticManager":
                    ends[event["agent"]] = event["elapsed"]
                print(f"{event['elapsed']:6.1f}s {event['agent']} {event['kind']}: {event['title']}", flush=True)
                if event["kind"] == "tool_end":
                    tools.append(event["title"])
                if event["kind"] in ("error", "final"):
                    print(event.get("text", ""), flush=True)
        assert "final" in kinds and "error" not in kinds, "Live workflow did not complete"
        assert {"inspect_bestiary", "inspect_inventory"} <= set(tools), "Required evidence tools not observed"
        if args.require_parallel:
            names = {"PotionAgent", "OilAgent", "RitualAgent"}
            assert set(starts) == names and set(ends) == names
            assert max(starts.values()) < min(ends.values()), "Specialist research did not overlap"
            assert len(manager_starts) == 2 and manager_starts[-1] >= max(ends.values()), "Manager review started too early"
            print("Verified parallel specialist intervals:", {name: [starts[name], ends[name]] for name in sorted(names)})
        print("PASS: HTTPS UI, auth gate, actual model/tool calls and final response.")


asyncio.run(main())
