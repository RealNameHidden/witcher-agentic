"""Observe public agent outputs and tool evidence, never private reasoning tokens."""
import json
import time
from uuid import uuid4

from agent_framework import AgentMiddleware, FunctionMiddleware


def readable(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(readable(item) for item in value)
    if getattr(value, "type", None) == "text":
        return value.text or ""
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    elif hasattr(value, "model_dump"):
        value = value.model_dump()
    return json.dumps(value, default=str, ensure_ascii=False, indent=2)


class Trace:
    def __init__(self, queue):
        self.queue = queue
        self.started = time.monotonic()

    def emit(self, kind, agent="MagenticManager", **fields):
        self.queue.put_nowait(dict(id=uuid4().hex, kind=kind, agent=agent,
                                  elapsed=round(time.monotonic() - self.started, 2), **fields))

    def middleware(self, name):
        trace = self

        class AgentTrace(AgentMiddleware):
            async def process(self, context, call_next):
                trace.emit("agent_start", name, title="Working on assignment")

                def completed(result):
                    trace.emit("agent_end", name, title="Response ready", text=result.text or "")
                    return result

                if context.stream:
                    context.stream_result_hooks.append(completed)
                await call_next()
                if not context.stream and context.result is not None:
                    completed(context.result)

        class ToolTrace(FunctionMiddleware):
            async def process(self, context, call_next):
                call_id = uuid4().hex
                trace.emit("tool_start", name, title=context.function.name,
                           call_id=call_id, text=readable(context.arguments))
                try:
                    await call_next()
                except Exception as exc:
                    trace.emit("tool_error", name, title=context.function.name,
                               call_id=call_id, text=str(exc)[:2000])
                    raise
                trace.emit("tool_end", name, title=context.function.name,
                           call_id=call_id, text=readable(context.result)[:40000])

        return [AgentTrace(), ToolTrace()]
