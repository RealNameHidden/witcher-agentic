import asyncio
import sys

from agent_framework import AgentResponse, AgentResponseUpdate
from dotenv import load_dotenv

from witcher_magentic.agents import build_magentic_workflow
from witcher_magentic.model_client import create_model_client


async def run(monster_name: str) -> None:
    load_dotenv()

    client = create_model_client()
    workflow = build_magentic_workflow(client)

    final_text: str | None = None
    async for event in workflow.run(
        f"Prepare a Witcher encounter plan for a {monster_name}.", stream=True
    ):
        if event.type == "intermediate" and isinstance(
            event.data, (AgentResponse, AgentResponseUpdate)
        ):
            if event.data.text:
                print(f"[{event.executor_id}] {event.data.text}")
        elif event.type == "output" and isinstance(
            event.data, (AgentResponse, AgentResponseUpdate)
        ):
            final_text = event.data.text

    if final_text is None:
        raise RuntimeError("The Magentic workflow completed without a final answer.")

    print(f"\nFinal encounter plan:\n{final_text}")


def main() -> None:
    monster_name = " ".join(sys.argv[1:]).strip() or "Katakan"
    asyncio.run(run(monster_name))


if __name__ == "__main__":
    main()
