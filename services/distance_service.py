
from math import radians, sin, cos, sqrt, atan2
from services.ai_schemas import AIItinerary
from services.routing_service import (
    get_cached_driving_route as get_driving_route,
)

def calculate_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calculate straight-line distance using Haversine."""

    earth_radius_km = 6371.0

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(max(0.0, 1 - a)))

    return earth_radius_km * c



def get_attraction_distances(
    itinerary: AIItinerary,
    places: list[dict],
) -> list[dict]:
    """Calculate distances between successive mapped attractions."""

    places_by_id = {
        place["place_id"]: place
        for place in places
        if place.get("place_id")
    }

    distances = []

    for day in itinerary.days:
        previous = None

        for activity in day.activities:
            if (
                activity.activity_type != "attraction"
                or not activity.place_id
            ):
                continue

            place = places_by_id.get(activity.place_id)

            if (
                place is None
                or place.get("latitude") is None
                or place.get("longitude") is None
            ):
                previous = None
                continue

            if previous is not None:
                previous_activity, previous_place = previous

                distance = calculate_distance_km(
                    previous_place["latitude"],
                    previous_place["longitude"],
                    place["latitude"],
                    place["longitude"],
                )
                
                
                # Minimum travel time at an assumed maximum
                # average speed of 120 km/h
                minimum_minutes = (distance / 120) * 60

                available_minutes = None
                travel_warning = False

                if (
                    previous_activity.end_time is not None
                    and activity.start_time is not None
                ):
                    previous_end = previous_activity.end_time
                    next_start = activity.start_time

                    end_minutes = (
                        previous_end.hour * 60
                        + previous_end.minute
                        + previous_end.second / 60
                    )

                    start_minutes = (
                        next_start.hour * 60
                        + next_start.minute
                        + next_start.second / 60
                    )

                    available_minutes = (
                        start_minutes - end_minutes
                    )

                    travel_warning = (
                        available_minutes < minimum_minutes
                    )

                distances.append({
                    "day": day.day_number,
                    "from": previous_activity.title,
                    "to": activity.title,
                    "from_place_id": previous_activity.place_id,
                    "to_place_id": activity.place_id,
                    "distance_km": round(distance, 2),
                    "available_minutes": available_minutes,
                    "minimum_minutes": round(minimum_minutes, 1),
                    "travel_warning": travel_warning,
                })

            previous = (activity, place)

    return distances




def get_road_travel_estimates(
    itinerary: AIItinerary,
    places: list[dict],
    max_routes: int = 5,
) -> list[dict]:
    """Estimate driving time between mapped attractions."""

    if max_routes <= 0:
        return []

    places_by_id = {
        place["place_id"]: place
        for place in places
        if place.get("place_id")
    }

    legs = get_attraction_distances(
        itinerary=itinerary,
        places=places,
    )

    results = []
    requests_made = 0

    for leg in legs:
        if requests_made >= max_routes:
            break

        if leg["available_minutes"] is None:
            continue

        start = places_by_id.get(leg["from_place_id"])
        end = places_by_id.get(leg["to_place_id"])

        if not start or not end:
            continue

        try:
            requests_made += 1

            route = get_driving_route(
                start["latitude"],
                start["longitude"],
                end["latitude"],
                end["longitude"],
            )
        except (ValueError, KeyError, TypeError):
            continue

        if route is None:
            continue

        results.append({
            **leg,
            "road_distance_km": route["distance_km"],
            "driving_minutes": route["duration_minutes"],
            "road_travel_warning": (
                leg["available_minutes"]
                < route["duration_minutes"]
            ),
        })

    return results
