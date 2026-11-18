
import os

import httpx
from collections import OrderedDict
from threading import Lock
from time import monotonic
import logging
from math import isfinite

from collections import OrderedDict
from threading import Lock
from time import monotonic

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def get_driving_route(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> dict | None:

    api_key = os.getenv("GEOAPIFY_API_KEY")

    if not api_key:
        logger.warning("Geoapify API key is missing")
        return None

    params = {
        "waypoints": f"{lat1},{lon1}|{lat2},{lon2}",
        "mode": "drive",
        "format": "json",
        "apiKey": api_key,
    }

    try:
        response = httpx.get(
            "https://api.geoapify.com/v1/routing",
            params=params,
            timeout=httpx.Timeout(10.0, connect=3.0),
        )

    except httpx.TimeoutException:
        logger.warning("Geoapify routing request timed out")
        return None

    except httpx.RequestError:
        logger.warning("Geoapify routing network error")
        return None

    if response.status_code != 200:
        logger.warning(
            "Geoapify routing failed with HTTP %s",
            response.status_code,
        )
        return None

    try:
        data = response.json()
        routes = data["results"]

        if not isinstance(routes, list) or not routes:
            return None

        route = routes[0]

        distance = route["distance"]
        duration = route["time"]

        for value in (distance, duration):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value < 0
            ):
                raise ValueError("Invalid route measurement")

    except (ValueError, KeyError, TypeError, OverflowError):
        logger.warning("Invalid Geoapify routing response")
        return None

    return {
        "distance_km": round(distance / 1000, 2),
        "duration_minutes": round(duration / 60, 1),
    }

ROUTE_CACHE_TTL = 600
ROUTE_CACHE_MAX_SIZE = 256

route_cache = OrderedDict()
cache_lock = Lock()

def get_cached_driving_route(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> dict | None:

    key = (lat1, lon1, lat2, lon2)

    with cache_lock:
        cached = route_cache.get(key)

        if cached is not None:
            expires_at, route = cached

            if monotonic() < expires_at:
                route_cache.move_to_end(key)
                return route.copy()

            del route_cache[key]

    # Request a fresh route
    route = get_driving_route(
        lat1, lon1, lat2, lon2
    )

    # Do not cache failed requests
    if route is None:
        return None

    with cache_lock:
        route_cache[key] = (
            monotonic() + ROUTE_CACHE_TTL,
            route.copy(),
        )

        route_cache.move_to_end(key)

        while len(route_cache) > ROUTE_CACHE_MAX_SIZE:
            route_cache.popitem(last=False)

    return route
