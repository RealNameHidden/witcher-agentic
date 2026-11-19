import unittest
import asyncio
from unittest.mock import Mock, patch

from agent_framework import Agent, BaseChatClient, ChatResponse, ChatResponseUpdate, Content, Message

from witcher_magentic.agents import (
    build_magentic_workflow,
    create_specialist_agents,
)


class MicrosoftAgentFrameworkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = Mock()
        self.client.model = "test-model"

    def test_creates_real_framework_agents(self) -> None:
        specialists = create_specialist_agents(self.client)

        self.assertTrue(all(isinstance(agent, Agent) for agent in specialists))
        self.assertEqual(
            ["PotionAgent", "OilAgent", "RitualAgent"],
            [agent.name for agent in specialists],
        )

    def test_specialists_receive_their_tools(self) -> None:
        potion_agent, oil_agent, ritual_agent = create_specialist_agents(self.client)

        def tool_names(agent: Agent) -> set[str]:
            return {tool.name for tool in agent.default_options["tools"]}

        self.assertEqual(
            {"inspect_bestiary", "inspect_inventory", "read_witcher_potion_lore"},
            tool_names(potion_agent),
        )
        self.assertEqual(
            {"inspect_bestiary", "inspect_inventory", "read_witcher_oil_lore"},
            tool_names(oil_agent),
        )
        self.assertEqual(
            {"inspect_bestiary", "read_witcher_ritual_and_curse_lore"},
            tool_names(ritual_agent),
        )

    def test_builds_a_magentic_workflow(self) -> None:
        workflow = build_magentic_workflow(self.client)

        self.assertEqual("WitcherParallelPreparationWorkflow", workflow.name)


class ParallelWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_specialists_enter_before_any_can_finish_and_manager_reviews_all(self):
        started = set()
        finished = set()
        all_started = asyncio.Event()
        order = []

        class FixtureClient(BaseChatClient):
            def __init__(self, name):
                super().__init__()
                self.model = "fixture"
                self.name = name
                self.calls = 0

            async def reply(self, messages):
                self.calls += 1
                if self.name == "manager":
                    if self.calls == 1:
                        order.append("plan")
                        return "PotionAgent: research potions. OilAgent: research oils. RitualAgent: research rituals."
                    assert finished == {"PotionAgent", "OilAgent", "RitualAgent"}
                    text = "\n".join(message.text or "" for message in messages)
                    assert all(f"{name} findings" in text for name in finished)
                    order.append("review")
                    return "Combined final plan from all three specialists."
                assert order[0] == "plan"
                started.add(self.name)
                order.append(f"start:{self.name}")
                if len(started) == 3:
                    all_started.set()
                # A sequential implementation deadlocks here and fails the test.
                await asyncio.wait_for(all_started.wait(), timeout=3)
                finished.add(self.name)
                order.append(f"end:{self.name}")
                return f"{self.name} findings"

            def _inner_get_response(self, *, messages, stream, options, **kwargs):
                if stream:
                    async def chunks():
                        text = await self.reply(messages)
                        yield ChatResponseUpdate(role="assistant", contents=[Content.from_text(text)])
                    return self._build_response_stream(chunks())
                async def result():
                    return ChatResponse(messages=[Message(role="assistant", contents=[await self.reply(messages)])])
                return result()

        names = ["PotionAgent", "OilAgent", "RitualAgent"]
        specialists = tuple(Agent(client=FixtureClient(name), name=name) for name in names)
        with patch("witcher_magentic.agents.create_specialist_agents", return_value=specialists):
            workflow = build_magentic_workflow(FixtureClient("manager"))
        outputs = []
        async with asyncio.timeout(8):
            async for event in workflow.run("Prepare for Katakan", stream=True):
                if event.type == "output":
                    outputs.append(event.data.text)
        self.assertEqual(["Combined final plan from all three specialists."], outputs)
        self.assertLess(max(order.index(f"start:{name}") for name in names),
                        min(order.index(f"end:{name}") for name in names))
        self.assertEqual("review", order[-1])


if __name__ == "__main__":
    unittest.main()
