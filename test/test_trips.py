from services.ai_schemas import AIItinerary




def test_create_trip(auth_client):
    response = auth_client.post(
        "/trips",
        json={
            "city": "Jaipur",
            "origin": "Kozhikode",
            "travellers": 2,
            "budget_of_a_person": 15000,
            "days": 3,
            "start_date": "2026-11-08",
            "end_date": "2026-11-10",
            "preferences": "food, forts and photography",
            "transport_preference": "train",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["city"] == "Jaipur"
    assert data["origin"] == "Kozhikode"
    assert data["travellers"] == 2
    assert data["budget_of_a_person"] == 15000
    assert data["days"] == 3
    assert data["preferences"] == "food, forts and photography"
    assert data["transport_preference"] == "train"

    assert "id" in data
    
    
    
def test_create_trip_with_invalid_dates_fails(auth_client):
    response = auth_client.post(
        "/trips",
        json={
            "city": "Jaipur",
            "origin": "Kozhikode",
            "travellers": 2,
            "budget_of_a_person": 15000,
            "days": 3,
            "start_date": "2026-11-10",
            "end_date": "2026-11-08",
            "preferences": "food and forts",
            "transport_preference": "train",
        },
    )

    assert response.status_code == 422
    
    
    
def test_get_trip(auth_client):
    # First create a trip
    create_response = auth_client.post(
        "/trips",
        json={
            "city": "Jaipur",
            "origin": "Kozhikode",
            "travellers": 2,
            "budget_of_a_person": 15000,
            "days": 3,
            "start_date": "2026-11-08",
            "end_date": "2026-11-10",
            "preferences": "food and forts",
            "transport_preference": "train",
        },
    )

    assert create_response.status_code == 200

    trip_id = create_response.json()["id"]

    # Now retrieve the same trip
    response = auth_client.get(f"/trips/{trip_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == trip_id
    assert data["city"] == "Jaipur"
    assert data["origin"] == "Kozhikode"
    assert data["travellers"] == 2
    
    
    
def test_update_trip(auth_client):
    # Create trip
    create_response = auth_client.post(
        "/trips",
        json={
            "city": "Jaipur",
            "origin": "Kozhikode",
            "travellers": 2,
            "budget_of_a_person": 15000,
            "days": 3,
            "start_date": "2026-11-08",
            "end_date": "2026-11-10",
            "preferences": "food and forts",
            "transport_preference": "train",
        },
    )

    assert create_response.status_code == 200

    trip_id = create_response.json()["id"]

    # Update trip
    response = auth_client.put(
        f"/trips/{trip_id}",
        json={
            "city": "Jaipur",
            "origin": "Kozhikode",
            "travellers": 3,
            "budget_of_a_person": 18000,
            "days": 3,
            "start_date": "2026-11-08",
            "end_date": "2026-11-10",
            "preferences": "photography and local food",
            "transport_preference": "flight",
        },
    )

    assert response.status_code == 200

    data = response.json()
    
    print("Update response:", data)

    assert data["id"] == trip_id
    assert data["travellers"] == 3
    assert data["budget_of_a_person"] == 18000
    assert data["preferences"] == "photography and local food"
    assert data["transport_preference"] == "flight"
    
    
    
    
    
    
def test_user_cannot_access_another_users_trip(client):
    # Register User A
    client.post(
        "/auth/register",
        json={
            "email": "usera@example.com",
            "password": "password123",
        },
    )

    # Login User A
    login_a = client.post(
        "/auth/login",
        data={
            "username": "usera@example.com",
            "password": "password123",
        },
    )

    token_a = login_a.json()["access_token"]

    # User A creates a trip
    create_response = client.post(
        "/trips",
        headers={
            "Authorization": f"Bearer {token_a}",
        },
        json={
            "city": "Jaipur",
            "travellers": 2,
            "budget_of_a_person": 15000,
            "days": 1,
            "start_date": "2026-11-08",
            "end_date": "2026-11-08",
        },
    )

    assert create_response.status_code == 200

    trip_id = create_response.json()["id"]

    # Register User B
    client.post(
        "/auth/register",
        json={
            "email": "userb@example.com",
            "password": "password123",
        },
    )

    # Login User B
    login_b = client.post(
        "/auth/login",
        data={
            "username": "userb@example.com",
            "password": "password123",
        },
    )

    token_b = login_b.json()["access_token"]

    # User B tries to access User A's trip
    response = client.get(
        f"/trips/{trip_id}",
        headers={
            "Authorization": f"Bearer {token_b}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found"
    
    
def test_user_cannot_update_another_users_trip(client):
    # Register and login User A
    client.post(
        "/auth/register",
        json={
            "email": "usera@example.com",
            "password": "password123",
        },
    )

    login_a = client.post(
        "/auth/login",
        data={
            "username": "usera@example.com",
            "password": "password123",
        },
    )

    token_a = login_a.json()["access_token"]

    # User A creates a trip
    create_response = client.post(
        "/trips",
        headers={
            "Authorization": f"Bearer {token_a}",
        },
        json={
            "city": "Jaipur",
            "travellers": 2,
            "budget_of_a_person": 15000,
            "days": 1,
            "start_date": "2026-11-08",
            "end_date": "2026-11-08",
        },
    )

    trip_id = create_response.json()["id"]

    # Register and login User B
    client.post(
        "/auth/register",
        json={
            "email": "userb@example.com",
            "password": "password123",
        },
    )

    login_b = client.post(
        "/auth/login",
        data={
            "username": "userb@example.com",
            "password": "password123",
        },
    )

    token_b = login_b.json()["access_token"]

    # User B attempts to update User A's trip
    response = client.put(
        f"/trips/{trip_id}",
        headers={
            "Authorization": f"Bearer {token_b}",
        },
        json={
            "city": "Kochi",
            "travellers": 2,
            "budget_of_a_person": 20000,
            "days": 1,
            "start_date": "2026-11-08",
            "end_date": "2026-11-08",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found"
    
    
def test_user_cannot_delete_another_users_trip(client):
    # Register and login User A
    client.post(
        "/auth/register",
        json={
            "email": "usera@example.com",
            "password": "password123",
        },
    )

    login_a = client.post(
        "/auth/login",
        data={
            "username": "usera@example.com",
            "password": "password123",
        },
    )

    token_a = login_a.json()["access_token"]

    # User A creates a trip
    create_response = client.post(
        "/trips",
        headers={
            "Authorization": f"Bearer {token_a}",
        },
        json={
            "city": "Jaipur",
            "travellers": 2,
            "budget_of_a_person": 15000,
            "days": 1,
            "start_date": "2026-11-08",
            "end_date": "2026-11-08",
        },
    )

    assert create_response.status_code == 200
    trip_id = create_response.json()["id"]

    # Register and login User B
    client.post(
        "/auth/register",
        json={
            "email": "userb@example.com",
            "password": "password123",
        },
    )

    login_b = client.post(
        "/auth/login",
        data={
            "username": "userb@example.com",
            "password": "password123",
        },
    )

    token_b = login_b.json()["access_token"]

    # User B attempts to delete User A's trip
    response = client.delete(
        f"/trips/{trip_id}",
        headers={
            "Authorization": f"Bearer {token_b}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found"

    # Confirm User A's trip still exists
    owner_response = client.get(
        f"/trips/{trip_id}",
        headers={
            "Authorization": f"Bearer {token_a}",
        },
    )

    assert owner_response.status_code == 200
    
    
def test_user_cannot_view_another_users_budget_summary(client):
    # Register User A
    client.post(
        "/auth/register",
        json={
            "email": "usera@example.com",
            "password": "password123",
        },
    )

    login_a = client.post(
        "/auth/login",
        data={
            "username": "usera@example.com",
            "password": "password123",
        },
    )

    token_a = login_a.json()["access_token"]

    # User A creates a trip
    trip_response = client.post(
        "/trips",
        headers={
            "Authorization": f"Bearer {token_a}",
        },
        json={
            "city": "Jaipur",
            "travellers": 2,
            "budget_of_a_person": 18000,
            "days": 3,
        },
    )

    assert trip_response.status_code == 200

    trip_id = trip_response.json()["id"]

    # Register User B
    client.post(
        "/auth/register",
        json={
            "email": "userb@example.com",
            "password": "password123",
        },
    )

    login_b = client.post(
        "/auth/login",
        data={
            "username": "userb@example.com",
            "password": "password123",
        },
    )

    token_b = login_b.json()["access_token"]

    # User B tries to access User A's budget
    response = client.get(
        f"/trips/{trip_id}/budget-summary",
        headers={
            "Authorization": f"Bearer {token_b}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found"
    
    
def test_user_cannot_view_another_users_activities(client):
    # Register and login User A
    client.post(
        "/auth/register",
        json={
            "email": "activityusera@example.com",
            "password": "password123",
        },
    )

    login_a = client.post(
        "/auth/login",
        data={
            "username": "activityusera@example.com",
            "password": "password123",
        },
    )

    token_a = login_a.json()["access_token"]
    headers_a = {
        "Authorization": f"Bearer {token_a}"
    }

    # User A creates a trip
    trip_response = client.post(
        "/trips",
        headers=headers_a,
        json={
            "city": "Jaipur",
            "travellers": 2,
            "budget_of_a_person": 18000,
            "days": 3,
        },
    )

    assert trip_response.status_code == 200
    trip_id = trip_response.json()["id"]

    # User A creates an itinerary day
    day_response = client.post(
        f"/trips/{trip_id}/itinerary-days",
        headers=headers_a,
        json={
            "day_number": 1,
            "title": "Explore Jaipur",
        },
    )

    assert day_response.status_code == 200
    itinerary_day_id = day_response.json()["id"]

    # Register and login User B
    client.post(
        "/auth/register",
        json={
            "email": "activityuserb@example.com",
            "password": "password123",
        },
    )

    login_b = client.post(
        "/auth/login",
        data={
            "username": "activityuserb@example.com",
            "password": "password123",
        },
    )

    token_b = login_b.json()["access_token"]
    headers_b = {
        "Authorization": f"Bearer {token_b}"
    }

    # User B tries to read User A's activities
    response = client.get(
        f"/itinerary-days/{itinerary_day_id}/activities",
        headers=headers_b,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found"
    
    
def test_user_cannot_delete_another_users_activity(client):
    # Register and login User A
    client.post(
        "/auth/register",
        json={
            "email": "deleteactivitya@example.com",
            "password": "password123",
        },
    )

    login_a = client.post(
        "/auth/login",
        data={
            "username": "deleteactivitya@example.com",
            "password": "password123",
        },
    )

    token_a = login_a.json()["access_token"]
    headers_a = {
        "Authorization": f"Bearer {token_a}"
    }

    # User A creates a trip
    trip_response = client.post(
        "/trips",
        headers=headers_a,
        json={
            "city": "Jaipur",
            "travellers": 2,
            "budget_of_a_person": 18000,
            "days": 3,
        },
    )

    assert trip_response.status_code == 200
    trip_id = trip_response.json()["id"]

    # User A creates an itinerary day
    day_response = client.post(
        f"/trips/{trip_id}/itinerary-days",
        headers=headers_a,
        json={
            "day_number": 1,
            "title": "Explore Jaipur",
        },
    )

    assert day_response.status_code == 200
    itinerary_day_id = day_response.json()["id"]

    # User A creates an activity
    activity_response = client.post(
        f"/itinerary-days/{itinerary_day_id}/activities",
        headers=headers_a,
        json={
            "title": "Visit Amber Fort",
            "location": "Amber Fort",
            "estimated_cost": 1000,
            "notes": "Morning visit",
            "start_time": "09:00:00",
            "end_time": "11:00:00",
        },
    )

    assert activity_response.status_code == 200
    activity_id = activity_response.json()["id"]

    # Register and login User B
    client.post(
        "/auth/register",
        json={
            "email": "deleteactivityb@example.com",
            "password": "password123",
        },
    )

    login_b = client.post(
        "/auth/login",
        data={
            "username": "deleteactivityb@example.com",
            "password": "password123",
        },
    )

    token_b = login_b.json()["access_token"]
    headers_b = {
        "Authorization": f"Bearer {token_b}"
    }

    # User B tries to delete User A's activity
    delete_response = client.delete(
        f"/activities/{activity_id}",
        headers=headers_b,
    )

    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Trip not found"

    # Verify User A's activity still exists
    activities_response = client.get(
        f"/itinerary-days/{itinerary_day_id}/activities",
        headers=headers_a,
    )

    assert activities_response.status_code == 200

    activity_ids = [
        activity["id"]
        for activity in activities_response.json()
    ]

    assert activity_id in activity_ids
    
    

def test_full_itinerary_returns_coordinates(
    auth_client, monkeypatch
):
    # Create a trip
    response = auth_client.post(
        "/trips",
        json={
            "city": "Ooty",
            "origin": "Kozhikode",
            "travellers": 2,
            "budget_of_a_person": 5000,
            "days": 3,
            "start_date": "2026-12-08",
            "end_date": "2026-12-10",
            "preferences": "nature",
            "transport_preference": "car",
        },
    )

    assert response.status_code == 200
    trip_id = response.json()["id"]

    # Mock Geoapify data
    places = [
        {
            "name": "Botanical Garden",
            "place_id": "garden-id",
            "latitude": 11.4175169,
            "longitude": 76.7105539,
        }
    ]

    # Mock generated itinerary
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
                        "place_id": "garden-id",
                        "estimated_cost": 200,
                        "start_time": "09:00:00",
                        "end_time": "11:00:00",
                    }
                ],
            },
            {
                "day_number": 2,
                "title": "Relaxation",
                "activities": [],
            },
            {
                "day_number": 3,
                "title": "Departure",
                "activities": [],
            },
        ],
    })

    monkeypatch.setattr(
        "main.get_places_by_city",
        lambda city: [],
    )

    monkeypatch.setattr(
        "main.clean_places",
        lambda raw_places: places,
    )

    monkeypatch.setattr(
        "main.filter_places",
        lambda cleaned_places: cleaned_places,
    )

    monkeypatch.setattr(
        "main.generate_valid_itinerary",
        lambda **kwargs: itinerary,
    )

    # Generate and save itinerary
    response = auth_client.post(
        f"/trips/{trip_id}/generate-itinerary"
    )

    assert response.status_code == 200

    # Retrieve saved itinerary
    response = auth_client.get(
        f"/trips/{trip_id}/full-itinerary"
    )

    assert response.status_code == 200

    data = response.json()

    activity = next(
        activity
        for day in data["itinerary_days"]
        for activity in day["activities"]
        if activity["title"] == "Botanical Garden"
    )

    assert activity["activity_type"] == "attraction"
    assert activity["place_id"] == "garden-id"
    assert activity["latitude"] == 11.4175169
    assert activity["longitude"] == 76.7105539
    
    
    
    activity_id = activity["id"]

    update_data = {
        "title": activity["title"],
        "location": activity["location"],
        "estimated_cost": 300,
        "notes": activity["notes"],
        "start_time": activity["start_time"],
        "end_time": activity["end_time"],
    }

    # Changing only the cost should preserve coordinates
    response = auth_client.put(
        f"/activities/{activity_id}",
        json=update_data,
    )

    assert response.status_code == 200
    updated = response.json()

    assert updated["estimated_cost"] == 300
    assert updated["place_id"] == "garden-id"
    assert updated["latitude"] == 11.4175169
    assert updated["longitude"] == 76.7105539

    # Changing the attraction should clear coordinates
    update_data["title"] = "Tea Museum"
    update_data["location"] = "Tea Museum"

    response = auth_client.put(
        f"/activities/{activity_id}",
        json=update_data,
    )

    assert response.status_code == 200
    updated = response.json()

    assert updated["place_id"] is None
    assert updated["latitude"] is None
    assert updated["longitude"] is None





def test_trip_road_estimates(auth_client, monkeypatch):
    response = auth_client.post(
        "/trips",
        json={
            "city": "Ooty",
            "origin": "Kozhikode",
            "travellers": 2,
            "budget_of_a_person": 5000,
            "days": 1,
            "preferences": "nature",
            "transport_preference": "car",
        },
    )

    assert response.status_code == 200
    trip_id = response.json()["id"]

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
                    "estimated_cost": 200,
                    "start_time": "09:00:00",
                    "end_time": "10:00:00",
                },
                {
                    "title": "Tea Museum",
                    "location": "Tea Museum",
                    "activity_type": "attraction",
                    "place_id": "place-b",
                    "estimated_cost": 200,
                    "start_time": "10:30:00",
                    "end_time": "12:00:00",
                },
            ],
        }],
    })

    monkeypatch.setattr(
        "main.get_places_by_city",
        lambda city: [],
    )

    monkeypatch.setattr(
        "main.clean_places",
        lambda raw_places: places,
    )

    monkeypatch.setattr(
        "main.filter_places",
        lambda cleaned_places: cleaned_places,
    )

    monkeypatch.setattr(
        "main.generate_valid_itinerary",
        lambda **kwargs: itinerary,
    )

    monkeypatch.setattr(
        "services.distance_service.get_driving_route",
        lambda *args: {
            "distance_km": 3.5,
            "duration_minutes": 15.0,
        },
    )

    response = auth_client.post(
        f"/trips/{trip_id}/generate-itinerary"
    )

    assert response.status_code == 200

    response = auth_client.get(
        f"/trips/{trip_id}/road-estimates"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["eligible_legs"] == 1
    assert data["checked_legs"] == 1

    route = data["routes"][0]

    assert route["from_activity"] == "Botanical Garden"
    assert route["to_activity"] == "Tea Museum"
    assert route["road_distance_km"] == 3.5
    assert route["driving_minutes"] == 15.0
    assert route["available_minutes"] == 30.0
    assert route["road_travel_warning"] is False



def test_budget_category_breakdown(auth_client, monkeypatch):
    response = auth_client.post(
        "/trips",
        json={
            "city": "Ooty",
            "travellers": 2,
            "budget_of_a_person": 2000,
            "days": 1,
        },
    )

    assert response.status_code == 200
    trip_id = response.json()["id"]

    expenses = [
        ("Transport", "transport", 1000),
        ("Hotel", "accommodation", 800),
        ("Lunch", "food", 400),
        ("Botanical Garden", "attraction", 200),
        ("Miscellaneous", "other", 100),
    ]

    itinerary = AIItinerary.model_validate({
        "city": "Ooty",
        "days": [{
            "day_number": 1,
            "title": "Sightseeing",
            "activities": [
                {
                    "title": title,
                    "location": "Ooty",
                    "activity_type": category,
                    "estimated_cost": cost,
                    "start_time": f"{9 + i:02d}:00:00",
                    "end_time": f"{10 + i:02d}:00:00",
                }
                for i, (title, category, cost)
                in enumerate(expenses)
            ],
        }],
    })

    monkeypatch.setattr(
        "main.get_places_by_city",
        lambda city: [],
    )

    monkeypatch.setattr(
        "main.generate_valid_itinerary",
        lambda **kwargs: itinerary,
    )

    response = auth_client.post(
        f"/trips/{trip_id}/generate-itinerary"
    )

    assert response.status_code == 200

    response = auth_client.get(
        f"/trips/{trip_id}/budget-summary"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_budget"] == 4000
    assert data["estimated_spent"] == 2500
    assert data["remaining_budget"] == 1500
    assert data["estimated_cost_per_person"] == 1250
    assert data["budget_utilization_percentage"] == 62.5

    assert data["category_breakdown"] == {
        "transport": 1000,
        "accommodation": 800,
        "food": 400,
        "attraction": 200,
        "other": 100,
    }
    
    assert data["daily_breakdown"] == [
        {
            "day_number": 1,
            "title": "Sightseeing",
            "estimated_spent": 2500,
        }
    ]
    assert sum(
        day["estimated_spent"]
        for day in data["daily_breakdown"]
    ) == data["estimated_spent"]



def test_activity_creation_authorization(auth_client):
    # Create a trip as User A
    response = auth_client.post(
        "/trips",
        json={
            "city": "Ooty",
            "travellers": 2,
            "budget_of_a_person": 5000,
            "days": 1,
        },
    )

    assert response.status_code == 200
    trip_id = response.json()["id"]

    # Create an itinerary day
    response = auth_client.post(
        f"/trips/{trip_id}/itinerary-days",
        json={
            "day_number": 1,
            "title": "Sightseeing",
        },
    )

    assert response.status_code == 200
    day_id = response.json()["id"]

    activity_data = {
        "title": "Visit Botanical Garden",
        "location": "Ooty",
        "estimated_cost": 200,
        "start_time": "09:00:00",
        "end_time": "11:00:00",
    }

    url = f"/itinerary-days/{day_id}/activities"

    # Save User A's authorization header
    owner_auth = auth_client.headers.pop("Authorization")

    # Test unauthenticated access
    response = auth_client.post(url, json=activity_data)

    assert response.status_code == 401

    # Register User B
    response = auth_client.post(
        "/auth/register",
        json={
            "email": "otheruser@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 201

    # Login as User B
    response = auth_client.post(
        "/auth/login",
        data={
            "username": "otheruser@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200
    token = response.json()["access_token"]

    auth_client.headers["Authorization"] = f"Bearer {token}"

    # User B attempts to modify User A's itinerary
    response = auth_client.post(url, json=activity_data)

    assert response.status_code == 404

    # Restore User A's authorization
    auth_client.headers["Authorization"] = owner_auth

    # The actual owner should succeed
    response = auth_client.post(url, json=activity_data)

    assert response.status_code == 200
    
    
    activity_id = response.json()["id"]
    activity_url = f"/activities/{activity_id}"

    update_data = {
        **activity_data,
        "estimated_cost": 500,
    }

    # Test unauthenticated access
    auth_client.headers.pop("Authorization")

    response = auth_client.put(
        activity_url, json=update_data
    )
    assert response.status_code == 401

    response = auth_client.delete(activity_url)
    assert response.status_code == 401

    # Login as User B using existing token
    auth_client.headers["Authorization"] = f"Bearer {token}"

    response = auth_client.put(
        activity_url, json=update_data
    )
    assert response.status_code == 404

    response = auth_client.delete(activity_url)
    assert response.status_code == 404

    # Restore User A's authorization
    auth_client.headers["Authorization"] = owner_auth

    response = auth_client.put(
        activity_url, json=update_data
    )
    assert response.status_code == 200
    assert response.json()["estimated_cost"] == 500

    response = auth_client.delete(activity_url)
    assert response.status_code == 200
