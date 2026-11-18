from services import planner_service
from services.ai_schemas import AIItinerary
import pytest
from services.ai_service import AIServiceError


def test_retries_on_insufficient_driving_time(monkeypatch):

    def make_itinerary(start_time):
        return AIItinerary.model_validate({
            "city": "Ooty",
            "days": [{
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
                        "start_time": start_time,
                        "end_time": "12:00:00",
                    },
                ],
            }],
        })

    places = [
        {
            "name": "Botanical Garden",
            "place_id": "place-a",
            "latitude": 11.4175,
            "longitude": 76.7105,
        },
        {
            "name": "Tea Museum",
            "place_id": "place-b",
            "latitude": 11.4117,
            "longitude": 76.7207,
        },
    ]

    feedback_history = []

    def fake_generate_itinerary(**kwargs):
        feedback_history.append(kwargs.get("feedback"))

        if len(feedback_history) == 1:
            return make_itinerary("10:05:00")

        return make_itinerary("10:30:00")

    def fake_road_estimates(**kwargs):
        first_attempt = len(feedback_history) == 1

        return [{
            "day": 1,
            "from": "Botanical Garden",
            "to": "Tea Museum",
            "road_distance_km": 4.0,
            "driving_minutes": 15.0,
            "available_minutes": 5.0 if first_attempt else 30.0,
            "road_travel_warning": first_attempt,
        }]

    monkeypatch.setattr(
        planner_service,
        "generate_itinerary",
        fake_generate_itinerary,
    )

    monkeypatch.setattr(
        planner_service,
        "get_road_travel_estimates",
        fake_road_estimates,
    )

    monkeypatch.setattr(
        planner_service,
        "get_weather_context",
        lambda *args, **kwargs: None,
    )

    result = planner_service.generate_valid_itinerary(
        city="Ooty",
        days=1,
        travellers=1,
        budget_per_person=1000,
        places_context=places,
        max_attempts=2,
    )

    assert len(feedback_history) == 2
    assert feedback_history[0] is None
    assert "15.0" in feedback_history[1]

    assert (
        result.days[0].activities[1].start_time.isoformat()
        == "10:30:00"
    )




def test_enrich_activity_coordinates():
    itinerary = AIItinerary.model_validate({
        "city": "Ooty",
        "days": [{
            "day_number": 1,
            "title": "Sightseeing",
            "activities": [
                {
                    "title": "Botanical Garden",
                    "location": "Botanical Garden",
                    "activity_type": "attraction",
                    "place_id": "place-a",
                    "estimated_cost": 100,
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "start_time": "09:00:00",
                    "end_time": "10:00:00",
                },
                {
                    "title": "Lunch",
                    "location": "Ooty",
                    "activity_type": "food",
                    "estimated_cost": 200,
                    "latitude": 20.0,
                    "longitude": 30.0,
                    "start_time": "12:00:00",
                    "end_time": "13:00:00",
                },
            ],
        }],
    })

    places = [
        {
            "name": "Botanical Garden",
            "place_id": "place-a",
            "latitude": 11.4175169,
            "longitude": 76.7105539,
        }
    ]

    result = planner_service.enrich_activity_coordinates(
        itinerary=itinerary,
        places=places,
    )

    attraction = result.days[0].activities[0]
    food = result.days[0].activities[1]

    assert attraction.latitude == 11.4175169
    assert attraction.longitude == 76.7105539
    assert attraction.place_id == "place-a"

    assert food.latitude is None
    assert food.longitude is None
    assert food.place_id is None



def test_retries_after_invalid_gemini_response(monkeypatch):
    feedback_history = []

    itinerary = AIItinerary.model_validate({
        "city": "Ooty",
        "days": [{
            "day_number": 1,
            "title": "Sightseeing",
            "activities": [{
                "title": "Botanical Garden",
                "location": "Ooty",
                "activity_type": "attraction",
                "estimated_cost": 200,
                "start_time": "09:00:00",
                "end_time": "11:00:00",
            }],
        }],
    })

    def fake_generate_itinerary(**kwargs):
        feedback_history.append(kwargs.get("feedback"))

        # First attempt returns an invalid response
        if len(feedback_history) == 1:
            raise ValueError(
                "Generate a valid itinerary matching "
                "the required response schema."
            )

        # Second attempt returns a valid itinerary
        return itinerary

    monkeypatch.setattr(
        planner_service,
        "generate_itinerary",
        fake_generate_itinerary,
    )

    monkeypatch.setattr(
        planner_service,
        "get_weather_context",
        lambda *args, **kwargs: None,
    )

    result = planner_service.generate_valid_itinerary(
        city="Ooty",
        days=1,
        travellers=1,
        budget_per_person=1000,
        places_context=[],
        max_attempts=2,
    )

    assert len(feedback_history) == 2
    assert feedback_history[0] is None
    assert "response schema" in feedback_history[1]
    assert result.city == "Ooty"



def test_stops_after_max_attempts(monkeypatch):
    calls = []

    def fake_generate_itinerary(**kwargs):
        calls.append(kwargs.get("feedback"))

        raise ValueError("Invalid itinerary response")

    monkeypatch.setattr(
        planner_service,
        "generate_itinerary",
        fake_generate_itinerary,
    )

    monkeypatch.setattr(
        planner_service,
        "get_weather_context",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(
        ValueError,
        match="after 2 attempts",
    ):
        planner_service.generate_valid_itinerary(
            city="Ooty",
            days=1,
            travellers=1,
            budget_per_person=1000,
            places_context=[],
            max_attempts=2,
        )

    assert len(calls) == 2
    assert calls[0] is None
    assert calls[1] == "Invalid itinerary response"




def test_planner_handles_service_failure(monkeypatch):
    calls = []

    def fake_generate_itinerary(**kwargs):
        calls.append(kwargs)

        raise AIServiceError(
            "AI service is temporarily unavailable"
        )

    monkeypatch.setattr(
        planner_service,
        "generate_itinerary",
        fake_generate_itinerary,
    )

    monkeypatch.setattr(
        planner_service,
        "get_weather_context",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(AIServiceError):
        planner_service.generate_valid_itinerary(
            city="Ooty",
            days=1,
            travellers=1,
            budget_per_person=1000,
            places_context=[],
            max_attempts=2,
        )

    assert len(calls) == 1
