
import pytest

from services.distance_service import calculate_distance_km
from services.ai_schemas import AIItinerary
from services.distance_service import get_attraction_distances
from services.distance_service import get_road_travel_estimates


def test_distance_between_coordinates():
    distance = calculate_distance_km(
        0.0, 0.0,
        0.0, 1.0,
    )

    # One degree of longitude at the equator
    # is approximately 111.2 km.
    assert distance == pytest.approx(111.2, abs=0.1)


def test_distance_between_same_location():
    distance = calculate_distance_km(
        11.4041834, 76.6803739,
        11.4041834, 76.6803739,
    )

    assert distance == pytest.approx(0.0)



def test_get_attraction_distances():
    itinerary = AIItinerary.model_validate({
        "city": "Test City",
        "days": [
            {
                "day_number": 1,
                "title": "Sightseeing",
                "activities": [
                    {
                        "title": "Place A",
                        "location": "Place A",
                        "activity_type": "attraction",
                        "place_id": "id-a",
                        "estimated_cost": 0,
                        "start_time": "09:00:00",
                        "end_time": "10:00:00",
                    },
                    {
                        "title": "Lunch",
                        "location": "Restaurant",
                        "activity_type": "food",
                        "estimated_cost": 100,
                        "start_time": "10:00:00",
                        "end_time": "11:00:00",
                    },
                    {
                        "title": "Place B",
                        "location": "Place B",
                        "activity_type": "attraction",
                        "place_id": "id-b",
                        "estimated_cost": 0,
                        "start_time": "11:00:00",
                        "end_time": "12:00:00",
                    },
                ],
            }
        ],
    })

    places = [
        {
            "name": "Place A",
            "place_id": "id-a",
            "latitude": 0.0,
            "longitude": 0.0,
        },
        {
            "name": "Place B",
            "place_id": "id-b",
            "latitude": 0.0,
            "longitude": 1.0,
        },
    ]

    distances = get_attraction_distances(
        itinerary=itinerary,
        places=places,
    )

    assert len(distances) == 1
    assert distances[0]["day"] == 1
    assert distances[0]["from"] == "Place A"
    assert distances[0]["to"] == "Place B"
    assert distances[0]["distance_km"] == pytest.approx(
        111.19, abs=0.1
    )
    
    
    

def test_warns_about_unrealistic_travel_time():
    itinerary = AIItinerary.model_validate({
        "city": "Test City",
        "days": [
            {
                "day_number": 1,
                "title": "Sightseeing",
                "activities": [
                    {
                        "title": "Place A",
                        "location": "Place A",
                        "activity_type": "attraction",
                        "place_id": "id-a",
                        "estimated_cost": 0,
                        "start_time": "09:00:00",
                        "end_time": "10:00:00",
                    },
                    {
                        "title": "Place B",
                        "location": "Place B",
                        "activity_type": "attraction",
                        "place_id": "id-b",
                        "estimated_cost": 0,
                        "start_time": "10:10:00",
                        "end_time": "11:00:00",
                    },
                ],
            }
        ],
    })

    places = [
        {
            "name": "Place A",
            "place_id": "id-a",
            "latitude": 0.0,
            "longitude": 0.0,
        },
        {
            "name": "Place B",
            "place_id": "id-b",
            "latitude": 0.0,
            "longitude": 1.0,
        },
    ]

    distances = get_attraction_distances(
        itinerary=itinerary,
        places=places,
    )

    assert len(distances) == 1
    assert distances[0]["distance_km"] == pytest.approx(
        111.19, abs=0.1
    )
    assert distances[0]["available_minutes"] == 10
    assert distances[0]["travel_warning"] is True



def test_road_travel_estimates(monkeypatch):
    itinerary = AIItinerary.model_validate({
        "city": "Ooty",
        "days": [
            {
                "day_number": 1,
                "title": "Sightseeing",
                "activities": [
                    {
                        "title": "Botanical Garden",
                        "location": "Botanical Garden",
                        "activity_type": "attraction",
                        "place_id": "place-a",
                        "estimated_cost": 100,
                        "start_time": "09:00:00",
                        "end_time": "10:00:00",
                    },
                    {
                        "title": "Tea Museum",
                        "location": "Tea Museum",
                        "activity_type": "attraction",
                        "place_id": "place-b",
                        "estimated_cost": 100,
                        "start_time": "10:10:00",
                        "end_time": "11:00:00",
                    },
                ],
            }
        ],
    })

    places = [
        {
            "name": "Botanical Garden",
            "place_id": "place-a",
            "latitude": 11.4175169,
            "longitude": 76.7105539,
        },
        {
            "name": "Tea Museum",
            "place_id": "place-b",
            "latitude": 11.4143402,
            "longitude": 76.7224149,
        },
    ]

    calls = []

    def fake_get_driving_route(lat1, lon1, lat2, lon2):
        calls.append((lat1, lon1, lat2, lon2))

        return {
            "distance_km": 3.5,
            "duration_minutes": 15.0,
        }

    monkeypatch.setattr(
        "services.distance_service.get_driving_route",
        fake_get_driving_route,
    )

    results = get_road_travel_estimates(
        itinerary=itinerary,
        places=places,
        max_routes=5,
    )

    assert len(calls) == 1
    assert len(results) == 1

    assert results[0]["road_distance_km"] == 3.5
    assert results[0]["driving_minutes"] == 15.0
    assert results[0]["available_minutes"] == 10.0
    assert results[0]["road_travel_warning"] is True
