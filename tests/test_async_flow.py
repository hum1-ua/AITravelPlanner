import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

import app
import backend


class FakeAsyncLLM:
    async def ainvoke(self, messages, **kwargs):
        return AIMessage(content="Generated async test response")


class AsyncFlowTests(unittest.TestCase):
    def test_health_endpoint(self):
        with TestClient(app.app) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["status"] == "ok")

    def test_travel_route_is_async(self):
        request = app.TravelRequest(
            message="Quiero viajar a Valencia",
            thread_id="test-thread"
        )

        async def run_test():
            with patch(
                "app.run_travel_agent",
                new=AsyncMock(return_value={
                    "thread_id": "test-thread",
                    "answer": "Respuesta",
                    "flight_results": "Vuelos",
                    "hotel_results": "Hoteles",
                    "itinerary": "Itinerario",
                    "llm_calls": 4,
                })
            ):
                response = await app.travel_planner(request)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.body is not None, True)

        asyncio.run(run_test())

    def test_async_graph_flow(self):
        async def fake_destination(query):
            return "Valencia"

        async def fake_weather(city):
            return "Sunny"

        async def fake_forecast(city):
            return "Rain later"

        async def fake_tavily(query):
            return "Hotel suggestions"

        async def fake_aviation(tool_name, tool_args=None):
            return [{"text": '{"ok": true, "data": []}'}]

        async def run_test():
            with (
                patch.object(backend, "llm", FakeAsyncLLM()),
                patch.object(backend, "extract_destination", fake_destination),
                patch.object(backend, "weather_mcp_search", fake_weather),
                patch.object(backend, "forecast_mcp_search", fake_forecast),
                patch.object(backend, "tavily_mcp_search", fake_tavily),
                patch.object(backend, "aviation_mcp_call", fake_aviation),
            ):
                result = await backend.travel_graph.ainvoke({
                    "messages": [],
                    "user_query": "Plan a trip to Valencia",
                    "flight_results": "",
                    "hotel_results": "",
                    "weather_results": "",
                    "itinerary": "",
                    "llm_calls": 0,
                }, config={"configurable": {"thread_id": "async-unit-test"}})

            self.assertIn("Valencia", result["user_query"])
            self.assertIn("Generated async test response", result["itinerary"])
            self.assertEqual(result["llm_calls"], 4)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
