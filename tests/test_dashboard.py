import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from unittest.mock import AsyncMock
import time
import importlib
from azure.core.credentials import AccessToken

from aiohttp.test_utils import TestClient, TestServer
from agent_framework import Agent, AgentResponse, BaseChatClient, ChatResponse, ChatResponseUpdate, Message, Content

from witcher_magentic.server import create_app
from witcher_magentic.telemetry import Trace
from witcher_magentic.model_client import create_model_client


class CloudClientTests(unittest.TestCase):
    def test_actual_foundry_client_can_be_constructed_without_model_call(self):
        from agent_framework.openai import OpenAIChatCompletionClient
        with patch.dict("os.environ", {"MODEL_PROVIDER": "foundry", "FOUNDRY_ENDPOINT": "https://example.cognitiveservices.azure.com", "FOUNDRY_MODEL": "witcher-mini"}):
            client = create_model_client()
        self.assertIsInstance(client, OpenAIChatCompletionClient)
        self.assertEqual("witcher-mini", client.model)


class FixtureClient(BaseChatClient):
    def _inner_get_response(self, *, messages, stream, options, **kwargs):
        if stream:
            async def chunks():
                yield ChatResponseUpdate(role="assistant", contents=[Content.from_text("Evidence-based response")])
            return self._build_response_stream(chunks())
        async def response():
            return ChatResponse(messages=[Message(role="assistant", contents=[Content.from_text("Evidence-based response")])])
        return response()


class TraceTests(unittest.IsolatedAsyncioTestCase):
    async def test_foundry_async_token_is_sent_on_model_request(self):
        credential = SimpleNamespace(get_token=AsyncMock(return_value=AccessToken("fixture-access-token", int(time.time()) + 3600)))
        observed = []

        async def fake_send(http_client, request, **kwargs):
            observed.append(request.headers.get("Authorization"))
            transport_module = importlib.import_module(type(request).__module__.split(".")[0])
            return transport_module.Response(200, request=request, json={
                "id": "fixture-completion", "object": "chat.completion", "created": 1,
                "model": "witcher-mini", "choices": [{"index": 0, "finish_reason": "stop",
                "message": {"role": "assistant", "content": "Connected through managed identity."}}],
            })

        with patch.dict("os.environ", {"MODEL_PROVIDER": "foundry", "FOUNDRY_ENDPOINT": "https://example.cognitiveservices.azure.com", "FOUNDRY_MODEL": "witcher-mini"}), patch("azure.identity.aio.DefaultAzureCredential", return_value=credential):
            client = create_model_client()
            try:
                with patch.object(type(client.client._client), "send", new=fake_send):
                    response = await client.get_response([Message(role="user", contents=["Test"] )])
            finally:
                await client.client.close()
        self.assertEqual("Connected through managed identity.", response.text)
        self.assertEqual(["Bearer fixture-access-token"], observed)

    async def test_real_agent_stream_emits_start_and_completed_public_output(self):
        queue = asyncio.Queue()
        agent = Agent(client=FixtureClient(), name="PotionAgent", middleware=Trace(queue).middleware("PotionAgent"))
        async for _ in agent.run("Test", stream=True):
            pass
        events = [queue.get_nowait() for _ in range(queue.qsize())]
        self.assertEqual(["agent_start", "agent_end"], [event["kind"] for event in events])
        self.assertEqual("Evidence-based response", events[-1]["text"])

    async def test_tool_failure_preserves_correlation_and_propagates(self):
        queue = asyncio.Queue()
        middleware = Trace(queue).middleware("OilAgent")[1]
        context = SimpleNamespace(function=SimpleNamespace(name="read_witcher_oil_lore"), arguments={})
        async def fail():
            raise RuntimeError("Wiki unavailable")
        with self.assertRaises(RuntimeError):
            await middleware.process(context, fail)
        start, error = queue.get_nowait(), queue.get_nowait()
        self.assertEqual("tool_error", error["kind"])
        self.assertEqual(start["call_id"], error["call_id"])


class DashboardApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = TestClient(TestServer(create_app()))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_invalid_inputs_do_not_start_a_workflow(self):
        for payload in ({"monster": ""}, {"monster": 42}, {"monster": "x" * 121}, []):
            response = await self.client.post("/api/run", json=payload)
            self.assertEqual(400, response.status)

    async def test_paid_runs_require_configured_key(self):
        with patch.dict("os.environ", {"APP_ACCESS_KEY": "test-only-key"}):
            for headers in ({}, {"Authorization": "Bearer wrong"}):
                response = await self.client.post("/api/run", json={"monster": "Katakan"}, headers=headers)
                self.assertEqual(401, response.status)
            # An authenticated malformed request reaches validation, not inference.
            response = await self.client.post("/api/run", json={"monster": ""}, headers={"Authorization": "Bearer test-only-key"})
            self.assertEqual(400, response.status)

    async def test_parallel_run_is_rejected(self):
        from witcher_magentic.server import RUN_LOCK
        async with self.client.server.app[RUN_LOCK]:
            response = await self.client.post("/api/run", json={"monster": "Katakan"})
            self.assertEqual(429, response.status)

    async def test_foundry_health_uses_direct_endpoint(self):
        with patch.dict("os.environ", {"MODEL_PROVIDER": "foundry", "FOUNDRY_ENDPOINT": "https://example.cognitiveservices.azure.com", "FOUNDRY_MODEL": "witcher-mini", "APP_ACCESS_KEY": "test-key"}):
            response = await self.client.get("/api/health")
            data = await response.json()
        self.assertTrue(data["ready"])
        self.assertTrue(data["access_required"])
        self.assertNotIn("test-key", json.dumps(data))

    async def test_final_answer_is_streamed(self):
        class Workflow:
            async def run(self, *args, **kwargs):
                yield SimpleNamespace(type="output", data=AgentResponse(messages=[Message(role="assistant", contents=["Use available supplies."])]))
        with patch("witcher_magentic.server.create_model_client"), patch("witcher_magentic.server.build_magentic_workflow", return_value=Workflow()):
            response = await self.client.post("/api/run", json={"monster": "Katakan"})
            events = [json.loads(line) for line in (await response.text()).splitlines() if line]
        self.assertEqual(["run_start", "final"], [event["kind"] for event in events])
        self.assertEqual("Use available supplies.", events[-1]["text"])

    async def test_model_failure_is_a_visible_stream_event(self):
        with patch("witcher_magentic.server.create_model_client", side_effect=RuntimeError("Model offline")):
            response = await self.client.post("/api/run", json={"monster": "Katakan"})
            events = [json.loads(line) for line in (await response.text()).splitlines() if line]
        self.assertEqual("error", events[-1]["kind"])
        self.assertIn("Model offline", events[-1]["text"])


if __name__ == "__main__":
    unittest.main()
