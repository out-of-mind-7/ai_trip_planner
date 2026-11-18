from datetime import time
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from typing import Literal


class AIActivity(BaseModel):
    title: str
    location: str

    activity_type: Literal[
        "attraction",
        "transport",
        "accommodation",
        "food",
        "other",
    ] = "other"

    estimated_cost: int = Field(ge=0)
    notes: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    place_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    
    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def require_local_time(cls, value):
        if isinstance(value, str):
            if value.endswith("Z"):
                value = value[:-1]

            return value

        if isinstance(value, time) and value.tzinfo is not None:
            raise ValueError(
                "Activity times must not contain timezone information"
            )

        return value
    
    

class AIItineraryDay(BaseModel):
    day_number: int = Field(ge=1)
    title: str
    activities: list[AIActivity]


class AIItinerary(BaseModel):
    city: str
    days: list[AIItineraryDay]
    
    

class RoadTravelLegResponse(BaseModel):
    day: int
    from_activity: str
    to_activity: str
    from_place_id: str
    to_place_id: str
    straight_line_distance_km: float
    road_distance_km: float
    driving_minutes: float
    available_minutes: float
    road_travel_warning: bool


class TripRoadTravelResponse(BaseModel):
    trip_id: UUID
    eligible_legs: int
    checked_legs: int
    routes: list[RoadTravelLegResponse]
