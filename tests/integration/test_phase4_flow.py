"""Phase 4 API integration flow tests."""

from typing import Any

from fastapi.testclient import TestClient

from api.main import create_app
from models.itinerary import Itinerary, ItineraryDay


class GraphStub:
    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "itinerary": Itinerary(
                destination=str(state["destination"]),
                days=[ItineraryDay(date="2026-07-05", spots=[], total_cost=0)],
                total_cost=0,
            ),
            "weather_info": {},
        }


def test_create_session_then_connect_stream() -> None:
    client = TestClient(create_app(graph=GraphStub()))
    response = client.post("/api/v1/chat", json={"content": "周末去杭州2日游预算500元"})
    session_id = response.json()["session_id"]

    with client.websocket_connect(f"/api/v1/chat/{session_id}/stream") as websocket:
        websocket.receive_json()
        websocket.receive_json()
        websocket.receive_json()
        event = websocket.receive_json()

    assert event["type"] == "result"
