
import httpx

from services.routing_service import get_driving_route

import pytest
import httpx

from services import routing_service

def test_get_driving_route(monkeypatch):
    # Use a fake API key for testing
    monkeypatch.setenv(
        "GEOAPIFY_API_KEY",
        "test-api-key",
    )

    # Mock Geoapify response
    def mock_get(url, params, timeout):
        assert params["mode"] == "drive"

        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "distance": 3200,
                        "time": 600,
                    }
                ]
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(
        "services.routing_service.httpx.get",
        mock_get,
    )

    result = get_driving_route(
        11.4175169,
        76.7105539,
        11.4143402,
        76.7224149,
    )

    assert result == {
        "distance_km": 3.2,
        "duration_minutes": 10.0,
    }



def test_returns_none_when_no_route(monkeypatch):
    monkeypatch.setenv(
        "GEOAPIFY_API_KEY",
        "test-api-key",
    )

    def mock_get(url, params, timeout):
        return httpx.Response(
            200,
            json={"results": []},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(
        "services.routing_service.httpx.get",
        mock_get,
    )

    result = get_driving_route(
        11.4175169,
        76.7105539,
        11.4143402,
        76.7224149,
    )

    assert result is None



def test_driving_route_cache(monkeypatch):
    # Start with an empty, isolated cache
    monkeypatch.setattr(
        routing_service,
        "route_cache",
        routing_service.OrderedDict(),
    )

    calls = []

    def fake_route(*args):
        calls.append(args)

        return {
            "distance_km": 4.5,
            "duration_minutes": 12.0,
        }

    monkeypatch.setattr(
        routing_service,
        "get_driving_route",
        fake_route,
    )

    coordinates = (
        11.4175, 76.7105,
        11.4117, 76.7207,
    )

    first = routing_service.get_cached_driving_route(
        *coordinates
    )

    second = routing_service.get_cached_driving_route(
        *coordinates
    )

    assert first == second
    assert len(calls) == 1



def test_driving_route_cache_expiration(monkeypatch):
    monkeypatch.setattr(
        routing_service,
        "route_cache",
        routing_service.OrderedDict(),
    )

    current_time = [1000.0]
    calls = []

    monkeypatch.setattr(
        routing_service,
        "monotonic",
        lambda: current_time[0],
    )

    def fake_route(*args):
        calls.append(args)

        return {
            "distance_km": 4.5,
            "duration_minutes": 12.0,
        }

    monkeypatch.setattr(
        routing_service,
        "get_driving_route",
        fake_route,
    )

    coordinates = (11.4175, 76.7105, 11.4117, 76.7207)

    routing_service.get_cached_driving_route(*coordinates)

    # Before expiration
    current_time[0] += 300

    routing_service.get_cached_driving_route(*coordinates)

    assert len(calls) == 1

    # After expiration
    current_time[0] += 301

    routing_service.get_cached_driving_route(*coordinates)

    assert len(calls) == 2


def test_failed_routes_are_not_cached(monkeypatch):
    monkeypatch.setattr(
        routing_service,
        "route_cache",
        routing_service.OrderedDict(),
    )

    calls = []

    def fake_route(*args):
        calls.append(args)

        if len(calls) == 1:
            return None

        return {
            "distance_km": 4.5,
            "duration_minutes": 12.0,
        }

    monkeypatch.setattr(
        routing_service,
        "get_driving_route",
        fake_route,
    )

    coordinates = (11.4175, 76.7105, 11.4117, 76.7207)

    first = routing_service.get_cached_driving_route(*coordinates)
    second = routing_service.get_cached_driving_route(*coordinates)
    third = routing_service.get_cached_driving_route(*coordinates)

    assert first is None
    assert second is not None
    assert second == third
    assert len(calls) == 2



@pytest.mark.parametrize("status_code, content", [
    (429, b'{"error": "Rate limit exceeded"}'),
    (500, b'{"error": "Server error"}'),
    (200, b'invalid json'),
    (200, b'{"results": [{}]}'),
    (200, b'{"results": [{"distance": -100, "time": 60}]}'),
])
def test_invalid_routing_responses(
    monkeypatch, status_code, content
):
    monkeypatch.setenv(
        "GEOAPIFY_API_KEY", "test-api-key"
    )

    def mock_get(url, params, timeout):
        return httpx.Response(
            status_code,
            content=content,
        )

    monkeypatch.setattr(
        "services.routing_service.httpx.get",
        mock_get,
    )

    result = get_driving_route(
        11.4175, 76.7105,
        11.4117, 76.7207,
    )

    assert result is None


def test_routing_timeout(monkeypatch):
    monkeypatch.setenv(
        "GEOAPIFY_API_KEY", "test-api-key"
    )

    def mock_get(*args, **kwargs):
        raise httpx.ReadTimeout("Request timed out")

    monkeypatch.setattr(
        "services.routing_service.httpx.get",
        mock_get,
    )

    result = get_driving_route(
        11.4175, 76.7105,
        11.4117, 76.7207,
    )

    assert result is None
