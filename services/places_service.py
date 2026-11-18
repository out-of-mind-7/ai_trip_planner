import os

import logging
import httpx
from dotenv import load_dotenv

from services.weather_service import get_coordinates
from functools import lru_cache

load_dotenv()

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")

GEOAPIFY_URL = "https://api.geoapify.com/v2/places"

logger = logging.getLogger(__name__)


class PlacesServiceError(ValueError):
    pass

def get_places_by_coordinates(
    latitude: float,
    longitude: float,
    radius: int = 5000,
) -> list[dict]:

    if not GEOAPIFY_API_KEY:
        raise PlacesServiceError(
            "Geoapify API key is missing"
        )

    params = {
        "categories": "tourism.attraction",
        "filter": f"circle:{longitude},{latitude},{radius}",
        "bias": f"proximity:{longitude},{latitude}",
        "limit": 100,
        "apiKey": GEOAPIFY_API_KEY,
    }

    try:
        response = httpx.get(
            GEOAPIFY_URL,
            params=params,
            timeout=httpx.Timeout(
                10.0,
                connect=3.0,
            ),
        )

    except httpx.TimeoutException:
        logger.warning("Geoapify Places request timed out")

        raise PlacesServiceError(
            "Geoapify Places request timed out"
        ) from None

    except httpx.RequestError:
        logger.warning("Geoapify Places network error")

        raise PlacesServiceError(
            "Geoapify Places is unavailable"
        ) from None

    if response.status_code != 200:
        logger.warning(
            "Geoapify Places returned HTTP %s",
            response.status_code,
        )

        raise PlacesServiceError(
            f"Geoapify Places returned HTTP {response.status_code}"
        )

    try:
        data = response.json()

        if not isinstance(data, dict):
            raise ValueError("Invalid response")

        features = data.get("features")

        if not isinstance(features, list):
            raise ValueError("Invalid features")

    except ValueError:
        logger.warning("Invalid Geoapify Places response")

        raise PlacesServiceError(
            "Invalid Geoapify Places response"
        ) from None

    return features


@lru_cache(maxsize=100)
def get_places_by_city(city: str):
    coordinates = get_coordinates(city)

    if coordinates is None:
        raise ValueError(f"City '{city}' not found")

    return get_places_by_coordinates(
        latitude=coordinates["latitude"],
        longitude=coordinates["longitude"],
        radius=5000,
    )
    

def clean_places(places: list[dict]) -> list[dict]:
    cleaned_places = []

    for place in places:
        if not isinstance(place, dict):
            continue

        properties = place.get("properties")
        geometry = place.get("geometry")

        if not isinstance(properties, dict):
            continue

        if not isinstance(geometry, dict):
            continue

        name = properties.get("name")
        coordinates = geometry.get("coordinates")

        # Validate place name
        if not isinstance(name, str) or not name.strip():
            continue

        # Validate coordinate structure
        if not isinstance(coordinates, (list, tuple)):
            continue

        if len(coordinates) < 2:
            continue

        longitude, latitude = coordinates[:2]

        # Validate coordinate types
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            for value in (latitude, longitude)
        ):
            continue

        # Validate geographic boundaries
        if not (
            -90 <= latitude <= 90
            and -180 <= longitude <= 180
        ):
            continue

        place_id = properties.get("place_id")

        if not isinstance(place_id, str) or not place_id.strip():
            place_id = None

        cleaned_places.append({
            "name": name.strip(),
            "address": properties.get("formatted"),
            "latitude": latitude,
            "longitude": longitude,
            "categories": properties.get("categories", []),
            "place_id": place_id,
        })

    return cleaned_places



def filter_places(places: list[dict]) -> list[dict]:
    filtered = []
    seen_ids = set()
    seen_names = set()

    for place in places:
        name = place["name"].strip()
        place_id = place.get("place_id")

        # Skip short or meaningless names
        if len(name) < 4:
            continue

        # Skip names without enough letters
        letter_count = sum(
            character.isalpha() for character in name
        )

        if letter_count < 4:
            continue

        # Skip duplicate names
        normalized_name = " ".join(name.casefold().split())

        if normalized_name in seen_names:
            continue

        # Skip duplicate place IDs
        if place_id and place_id in seen_ids:
            continue

        seen_names.add(normalized_name)

        if place_id:
            seen_ids.add(place_id)

        filtered.append(place)

    return filtered