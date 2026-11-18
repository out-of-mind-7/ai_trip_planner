from datetime import time

from services.ai_schemas import (
    AIActivity,
    AIItineraryDay,
    AIItinerary,
)

def test_generate_itinerary_endpoint(auth_client, monkeypatch):

    fake_itinerary = AIItinerary(
        city="Jaipur",
        days=[
            AIItineraryDay(
                day_number=1,
                title="Explore Jaipur",
                activities=[
                    AIActivity(
                        title="Amber Fort",
                        location="Amber Fort",
                        estimated_cost=1000,
                        start_time=time(9, 0),
                        end_time=time(11, 0),
                    )
                ],
            )
        ],
    )

    def fake_generate_valid_itinerary(**kwargs):
        return fake_itinerary

    monkeypatch.setattr(
        "main.generate_valid_itinerary",
        fake_generate_valid_itinerary,
    ) 
    
    # Create a trip first
    create_response = auth_client.post(
        "/trips",
        json={
            "city": "Jaipur",
            "origin": "Kozhikode",
            "travellers": 2,
            "budget_of_a_person": 15000,
            "days": 1,
            "start_date": "2026-11-08",
            "end_date": "2026-11-08",
            "preferences": "forts and photography",
            "transport_preference": "train",
        },
    )

    assert create_response.status_code == 200

    trip_id = create_response.json()["id"]

    # Generate itinerary
    response = auth_client.post(
        f"/trips/{trip_id}/generate-itinerary"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["city"] == "Jaipur"
    assert len(data["days"]) == 1
    assert data["days"][0]["day_number"] == 1
    assert data["days"][0]["title"] == "Explore Jaipur"
    assert data["days"][0]["activities"][0]["title"] == "Amber Fort"
    
    # Verify generated itinerary was persisted
    saved_response = auth_client.get(
        f"/trips/{trip_id}/full-itinerary"
    )

    assert saved_response.status_code == 200

    saved_data = saved_response.json()

    assert len(saved_data["itinerary_days"]) == 1

    saved_day = saved_data["itinerary_days"][0]

    assert saved_day["day_number"] == 1
    assert saved_day["title"] == "Explore Jaipur"
    assert len(saved_day["activities"]) == 1

    saved_activity = saved_day["activities"][0]

    assert saved_activity["title"] == "Amber Fort"
    assert saved_activity["location"] == "Amber Fort"
    assert saved_activity["estimated_cost"] == 1000
    
    
def test_generate_itinerary_ai_service_failure(auth_client,monkeypatch):
    from services.ai_service import AIServiceError

    def fake_generate_valid_itinerary(**kwargs):
        raise AIServiceError("AI ervice unavailable")

    monkeypatch.setattr(
        "main.generate_valid_itinerary",
        fake_generate_valid_itinerary,
    )

    create_response = auth_client.post(
        "/trips",
        json={
            "city": "Jaipur",
            "origin": "Kozhikode",
            "travellers": 2,
            "budget_of_a_person": 15000,
            "days": 1,
            "start_date": "2026-11-08",
            "end_date": "2026-11-08",
            "preferences": "forts",
            "transport_preference": "train",
        },
    )

    assert create_response.status_code == 200

    trip_id = create_response.json()["id"]

    response = auth_client.post(
        f"/trips/{trip_id}/generate-itinerary"
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "AI Service is temporarily unavailable"
    )
    
   
   
def test_generated_itinerary_is_saved(auth_client, monkeypatch):
    fake_itinerary = AIItinerary(
        city="Jaipur",
        days=[
            AIItineraryDay(
                day_number=1,
                title="Explore Jaipur",
                activities=[
                    AIActivity(
                        title="Visit Amber Fort",
                        location="Amber Fort",
                        estimated_cost=1000,
                        start_time=time(9, 0),
                        end_time=time(11, 0),
                    )
                ],
            )
        ],
    )

    def fake_generate(*args, **kwargs):
        return fake_itinerary

    monkeypatch.setattr(
        "main.generate_valid_itinerary",
        fake_generate,
    )

    create_response = auth_client.post(
        "/trips",
        json={
            "city": "Jaipur",
            "origin": "Kozhikode",
            "travellers": 2,
            "budget_of_a_person": 10000,
            "days": 1,
            "preferences": "forts",
            "transport_preference": "train",
        },
    )

    assert create_response.status_code == 200
    trip_id = create_response.json()["id"]

    generate_response = auth_client.post(
        f"/trips/{trip_id}/generate-itinerary"
    )

    assert generate_response.status_code == 200

    saved_response = auth_client.get(
        f"/trips/{trip_id}/full-itinerary"
    )

    assert saved_response.status_code == 200

    data = saved_response.json()

    assert len(data["itinerary_days"]) == 1
    assert data["itinerary_days"][0]["day_number"] == 1
    assert len(data["itinerary_days"][0]["activities"]) == 1
    assert (
        data["itinerary_days"][0]["activities"][0]["title"]
        == "Visit Amber Fort"
    )
    
    
    
    
def test_regenerating_itinerary_replaces_old_itinerary(
    auth_client,
    monkeypatch,
):
    first_itinerary = AIItinerary(
        city="Jaipur",
        days=[
            AIItineraryDay(
                day_number=1,
                title="First Itinerary",
                activities=[
                    AIActivity(
                        title="Amber Fort",
                        location="Amber Fort",
                        estimated_cost=1000,
                        start_time=time(9, 0),
                        end_time=time(11, 0),
                    )
                ],
            )
        ],
    )

    second_itinerary = AIItinerary(
        city="Jaipur",
        days=[
            AIItineraryDay(
                day_number=1,
                title="New Itinerary",
                activities=[
                    AIActivity(
                        title="City Palace",
                        location="City Palace",
                        estimated_cost=800,
                        start_time=time(10, 0),
                        end_time=time(12, 0),
                    )
                ],
            )
        ],
    )

    responses = iter([
        first_itinerary,
        second_itinerary,
    ])

    def fake_generate(**kwargs):
        return next(responses)

    monkeypatch.setattr(
        "main.generate_valid_itinerary",
        fake_generate,
    )
    
    # Create one trip
    create_response = auth_client.post(
        "/trips",
        json={
            "city": "Jaipur",
            "origin": "Kozhikode",
            "travellers": 2,
            "budget_of_a_person": 10000,
            "days": 1,
            "preferences": "forts and photography",
            "transport_preference": "train",
        },
    )

    assert create_response.status_code == 200
    trip_id = create_response.json()["id"]

    # Generate the first itinerary
    first_response = auth_client.post(
        f"/trips/{trip_id}/generate-itinerary"
    )

    assert first_response.status_code == 200

    # Generate again for the same trip
    second_response = auth_client.post(
        f"/trips/{trip_id}/generate-itinerary"
    )

    assert second_response.status_code == 200

    # Read what is actually stored in the database
    saved_response = auth_client.get(
        f"/trips/{trip_id}/full-itinerary"
    )

    assert saved_response.status_code == 200

    data = saved_response.json()

    # There must still be only one day
    assert len(data["itinerary_days"]) == 1

    saved_day = data["itinerary_days"][0]

    # It must be the SECOND itinerary
    assert saved_day["title"] == "New Itinerary"

    assert len(saved_day["activities"]) == 1

    saved_activity = saved_day["activities"][0]

    assert saved_activity["title"] == "City Palace"