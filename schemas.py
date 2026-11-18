from uuid import UUID
from pydantic import BaseModel,Field, ConfigDict,model_validator
from datetime import time,date

from models import Trip
from services.ai_schemas import RoadTravelLegResponse


class TripRequest(BaseModel):
    city: str
    origin : str | None = None
    travellers: int = Field(ge=1)
    budget_of_a_person: int = Field(ge=1)
    days: int = Field(ge=1)

    start_date: date | None = None
    end_date: date | None = None
    
    preferences : str | None = None
    
    transport_preference: str | None = None
    

    @model_validator(mode="after")
    def validate_trip_dates(self):
        if self.start_date is None or self.end_date is None:
            return self

        if self.end_date < self.start_date:
            raise ValueError(
                "end_date cannot be before start_date"
            )

        calculated_days = (
            self.end_date - self.start_date
        ).days + 1

        if calculated_days != self.days:
            raise ValueError(
                f"days must be {calculated_days} "
                f"for the selected travel dates"
            )

        return self
    
    
class TripResponse(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: UUID
    city:str
    travellers:int = Field(ge=1)
    budget_of_a_person:int = Field(ge=1)
    days:int
    
    start_date: date | None = None
        
    end_date : date | None = None
    
    preferences: str | None = None
    
    origin : str | None = None
    
    transport_preference : str | None = None
    
    
    
    
class ItineryDayRequest(BaseModel):
    day_number: int= Field(ge=1)
    title:str
    
class ItineryDayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:UUID
    trip_id:UUID
    day_number: int
    title:str
    
class ActivityRequest(BaseModel):
    title: str
    location: str
    estimated_cost: int = Field(ge=0)
    notes: str | None = None
    start_time: time | None = None
    end_time: time | None = None

    @model_validator(mode="after")
    def validate_activity_times(self):
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time <= self.start_time
        ):
            raise ValueError(
                "end_time must be later than start_time"
            )

        return self
    

class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    itinerary_day_id: UUID
    title: str
    location: str
    activity_type: str
    place_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    estimated_cost: int
    notes: str | None = None
    start_time: time | None = None
    end_time: time | None = None

    
class ItineraryDayDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trip_id: UUID
    day_number: int
    title: str
    activities: list[ActivityResponse]


class TripDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    city: str
    travellers: int
    budget_of_a_person: int
    days: int
    itinerary_days: list[ItineraryDayDetailResponse]
    
class DayBudgetResponse(BaseModel):
    day_number: int
    title: str
    estimated_spent: int

class BudgetSummaryResponse(BaseModel):
    total_budget: int
    estimated_spent: int
    remaining_budget: int
    estimated_cost_per_person: float
    budget_utilization_percentage: float
    category_breakdown: dict[str, int]
    daily_breakdown: list[DayBudgetResponse]

    

class UserRegisterRequest(BaseModel):
    email:str
    password: str = Field(min_length=8)
    
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id:UUID
    email:str

class UserLoginRequest(BaseModel):
    email:str
    password:str
    
class TokenResponse(BaseModel):
    access_token :str
    token_type:str
    
class TripRoadTravelResponse(BaseModel):
    trip_id: UUID
    eligible_legs: int
    checked_legs: int
    routes: list[RoadTravelLegResponse]