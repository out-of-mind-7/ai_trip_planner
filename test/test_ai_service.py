import pytest
from types import SimpleNamespace
from services import ai_service
from services.ai_schemas import AIItinerary
import httpx


def test_gemini_manual_json_parsing(monkeypatch):
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

    fake_response = SimpleNamespace(
        parsed=None,
        text=itinerary.model_dump_json(),
    )

    fake_client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **kwargs: fake_response
        )
    )

    monkeypatch.setattr(ai_service, "client", fake_client)

    result = ai_service.generate_itinerary(
        city="Ooty",
        days=1,
        travellers=1,
        budget_per_person=1000,
    )

    assert isinstance(result, AIItinerary)
    assert result.city == "Ooty"


def test_gemini_invalid_json(monkeypatch):
    fake_response = SimpleNamespace(
        parsed=None,
        text="Invalid JSON response",
    )

    fake_client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **kwargs: fake_response
        )
    )

    monkeypatch.setattr(ai_service, "client", fake_client)

    with pytest.raises(ValueError, match="response schema"):
        ai_service.generate_itinerary(
            city="Ooty",
            days=1,
            travellers=1,
            budget_per_person=1000,
        )



def test_gemini_timeout(monkeypatch):

    def fake_generate_content(**kwargs):
        raise httpx.ReadTimeout("Gemini request timed out")

    fake_client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=fake_generate_content
        )
    )

    monkeypatch.setattr(
        ai_service,
        "client",
        fake_client,
    )

    with pytest.raises(
        ai_service.AIServiceError,
        match="temporarily unavailable",
    ):
        ai_service.generate_itinerary(
            city="Ooty",
            days=1,
            travellers=1,
            budget_per_person=1000,
        )
