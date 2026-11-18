from datetime import time

from services.ai_schemas import AIActivity, AIItineraryDay, AIItinerary
from services.ai_validator import validate_itinerary
import pytest
from services.ai_validator import validate_place_locations
from services.ai_validator import validate_place_ids

def test_valid_itinerary_passes_validation():
    itinerary = AIItinerary(
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

    result = validate_itinerary(
        itinerary=itinerary,
        expected_days=1,
        total_budget=5000,
    )

    assert result == itinerary
    
    

def test_itinerary_exceeding_budget_fails():
    itinerary = AIItinerary(
        city="Jaipur",
        days=[
            AIItineraryDay(
                day_number=1,
                title="Expensive Jaipur Day",
                activities=[
                    AIActivity(
                        title="Expensive Activity",
                        location="Jaipur",
                        estimated_cost=6000,
                        start_time=time(9, 0),
                        end_time=time(11, 0),
                    )
                ],
            )
        ],
    )

    with pytest.raises(ValueError, match="exceeds budget"):
        validate_itinerary(
            itinerary=itinerary,
            expected_days=1,
            total_budget=5000,
        )
        
def test_overlapping_activities_fail():
    itinerary = AIItinerary(
        city="Jaipur",
        days=[
            AIItineraryDay(
                day_number=1,
                title="Jaipur Sightseeing",
                activities=[
                    AIActivity(
                        title="Amber Fort",
                        location="Amber Fort",
                        estimated_cost=1000,
                        start_time=time(9, 0),
                        end_time=time(12, 0),
                    ),
                    AIActivity(
                        title="City Palace",
                        location="City Palace",
                        estimated_cost=800,
                        start_time=time(11, 0),
                        end_time=time(13, 0),
                    ),
                ],
            )
        ],
    )

    with pytest.raises(ValueError, match="Overlapping activities"):
        validate_itinerary(
            itinerary=itinerary,
            expected_days=1,
            total_budget=5000,
        )
        
        
def test_activity_end_time_before_start_time_fails():
    itinerary = AIItinerary(
        city="Jaipur",
        days=[
            AIItineraryDay(
                day_number=1,
                title="Jaipur Sightseeing",
                activities=[
                    AIActivity(
                        title="Amber Fort",
                        location="Amber Fort",
                        estimated_cost=1000,
                        start_time=time(12, 0),
                        end_time=time(10, 0),
                    )
                ],
            )
        ],
    )

    with pytest.raises(ValueError, match="Invalid activity time"):
        validate_itinerary(
            itinerary=itinerary,
            expected_days=1,
            total_budget=5000,
        )
        
        
def test_itinerary_over_budget_fails():
    itinerary = AIItinerary(
        city="Jaipur",
        days=[
            AIItineraryDay(
                day_number=1,
                title="Day 1",
                activities=[
                    AIActivity(
                        title="Expensive activity",
                        location="Jaipur",
                        estimated_cost=6000,
                        start_time=time(9, 0),
                        end_time=time(11, 0),
                    )
                ],
            )
        ],
    )

    with pytest.raises(ValueError, match="exceeds budget"):
        validate_itinerary(
            itinerary=itinerary,
            expected_days=1,
            total_budget=5000,
        )
        
def test_overlapping_activities_fail():
    itinerary = AIItinerary(
        city="Jaipur",
        days=[
            AIItineraryDay(
                day_number=1,
                title="Explore Jaipur",
                activities=[
                    AIActivity(
                        title="Amber Fort",
                        location="Amber",
                        estimated_cost=1000,
                        start_time=time(9, 0),
                        end_time=time(11, 0),
                    ),
                    AIActivity(
                        title="City Palace",
                        location="Jaipur",
                        estimated_cost=800,
                        start_time=time(10, 30),
                        end_time=time(12, 0),
                    ),
                ],
            )
        ],
    )

    with pytest.raises(ValueError, match="Overlapping activities"):
        validate_itinerary(
            itinerary=itinerary,
            expected_days=1,
            total_budget=5000,
        )
        
def test_activity_end_time_before_start_time_fails():
    itinerary = AIItinerary(
        city="Jaipur",
        days=[
            AIItineraryDay(
                day_number=1,
                title="Explore Jaipur",
                activities=[
                    AIActivity(
                        title="Amber Fort",
                        location="Amber",
                        estimated_cost=1000,
                        start_time=time(12, 0),
                        end_time=time(10, 0),
                    )
                ],
            )
        ],
    )

    with pytest.raises(ValueError, match="Invalid activity time"):
        validate_itinerary(
            itinerary=itinerary,
            expected_days=1,
            total_budget=5000,
        )
        
        
        


def test_rejects_missing_activity_time():
    itinerary = AIItinerary.model_validate({
        "city": "Ooty",
        "days": [
            {
                "day_number": 1,
                "title": "Sightseeing",
                "activities": [
                    {
                        "title": "Visit Botanical Garden",
                        "location": "Ooty",
                        "activity_type": "attraction",
                        "estimated_cost": 200,
                        "start_time": None,
                        "end_time": "11:00:00",
                    }
                ],
            }
        ],
    })

    with pytest.raises(ValueError, match="both start_time and end_time"):
        validate_itinerary(
            itinerary=itinerary,
            expected_days=1,
            total_budget=1000,
        )
        
        
        

def test_partial_place_name_matching():
    itinerary = AIItinerary.model_validate({
        "city": "Ooty",
        "days": [
            {
                "day_number": 1,
                "title": "Sightseeing",
                "activities": [
                    {
                        "title": "Visit Botanical Garden",
                        "location": "Government Botanical Garden, Ooty",
                        "activity_type": "attraction",
                        "estimated_cost": 200,
                        "start_time": "09:00:00",
                        "end_time": "11:00:00",
                    },
                    {
                        "title": "Visit Unknown Place",
                        "location": "Imaginary Sky Castle, Ooty",
                        "activity_type": "attraction",
                        "estimated_cost": 100,
                        "start_time": "12:00:00",
                        "end_time": "13:00:00",
                    },
                ],
            }
        ],
    })

    places = [
        {
            "name": "Government Botanical Garden Entrance",
            "place_id": "test-place-123",
        }
    ]

    unmatched = validate_place_locations(
        itinerary=itinerary,
        places=places,
    )

    assert unmatched == ["Imaginary Sky Castle, Ooty"]




def test_rejects_invalid_geoapify_place_id():
    itinerary = AIItinerary.model_validate({
        "city": "Ooty",
        "days": [
            {
                "day_number": 1,
                "title": "Sightseeing",
                "activities": [
                    {
                        "title": "Visit Botanical Garden",
                        "location": "Government Botanical Garden",
                        "activity_type": "attraction",
                        "place_id": "fake-place-123",
                        "estimated_cost": 200,
                        "start_time": "09:00:00",
                        "end_time": "11:00:00",
                    }
                ],
            }
        ],
    })

    places = [
        {
            "name": "Government Botanical Garden",
            "place_id": "real-place-456",
        }
    ]

    with pytest.raises(ValueError, match="Invalid Geoapify place_id"):
        validate_place_ids(
            itinerary=itinerary,
            places=places,
        )



def test_rejects_place_id_for_wrong_attraction():
    itinerary = AIItinerary.model_validate({
        "city": "Ooty",
        "days": [
            {
                "day_number": 1,
                "title": "Sightseeing",
                "activities": [
                    {
                        "title": "Visit Doddabetta Viewpoint",
                        "location": "Doddabetta Viewpoint",
                        "activity_type": "attraction",
                        "place_id": "botanical-garden-id",
                        "estimated_cost": 200,
                        "start_time": "09:00:00",
                        "end_time": "11:00:00",
                    }
                ],
            }
        ],
    })

    places = [
        {
            "name": "Government Botanical Garden Entrance",
            "place_id": "botanical-garden-id",
        },
        {
            "name": "Doddabetta Viewpoint",
            "place_id": "doddabetta-id",
        },
    ]

    with pytest.raises(
        ValueError,
        match="does not match attraction",
    ):
        validate_place_ids(
            itinerary=itinerary,
            places=places,
        )



def test_accepts_tamil_geoapify_place_name():
    itinerary = AIItinerary.model_validate({
        "city": "Ooty",
        "days": [
            {
                "day_number": 1,
                "title": "Tea Museum Visit",
                "activities": [
                    {
                        "title": "Visit Tea Museum",
                        "location": "தேயிலை அருங்காட்சியகம், ஊட்டி",
                        "activity_type": "attraction",
                        "place_id": "tea-museum-id",
                        "estimated_cost": 200,
                        "start_time": "10:00:00",
                        "end_time": "12:00:00",
                    }
                ],
            }
        ],
    })

    places = [
        {
            "name": "தேயிலை அருங்காட்சியகம், ஊட்டி",
            "place_id": "tea-museum-id",
            "latitude": 11.4,
            "longitude": 76.7,
        }
    ]

    # Should not raise a validation error
    result = validate_place_ids(
        itinerary=itinerary,
        places=places,
    )

    assert result is None
