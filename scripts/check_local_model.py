"""Prove local inference and actual framework tool execution without a wiki dependency."""
import asyncio

from agent_framework import Agent
from dotenv import load_dotenv

from witcher_magentic.model_client import create_model_client
from witcher_magentic.telemetry import Trace
from witcher_magentic.tools import inspect_bestiary, inspect_inventory


async def main():
    load_dotenv()
    queue = asyncio.Queue()
    agent = Agent(
        client=create_model_client(),
        name="LocalModelCheck",
        instructions=("Call inspect_bestiary for Katakan and inspect_inventory before answering. "
                      "Give a two-sentence recommendation using only their results. /no_think"),
        tools=[inspect_bestiary, inspect_inventory],
        middleware=Trace(queue).middleware("LocalModelCheck"),
    )
    async with asyncio.timeout(240):
        response = await agent.run("Which available potion and oil should I use for a Katakan? /no_think")
    events = [queue.get_nowait() for _ in range(queue.qsize())]
    completed = {event["title"] for event in events if event["kind"] == "tool_end"}
    print("Completed tools:", ", ".join(sorted(completed)))
    print(response.text)
    if not {"inspect_bestiary", "inspect_inventory"} <= completed:
        raise RuntimeError("The model did not execute both required tools.")


if __name__ == "__main__":
    asyncio.run(main())
