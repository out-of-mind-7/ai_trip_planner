from datetime import date
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel,Field,ConfigDict
from uuid import UUID, uuid4

from services.weather_service import get_coordinates

from sqlalchemy import select
from sqlalchemy.orm import Session , selectinload

from database import engine
from models import Base,Trip , ItineraryDay , Activity
from fastapi import Depends
from database import get_session
from schemas import TripRequest, TripResponse ,ItineryDayRequest , ItineryDayResponse , ActivityRequest, ActivityResponse ,TripDetailResponse , BudgetSummaryResponse, UserRegisterRequest, UserResponse,TokenResponse,UserLoginRequest
from schemas import TripRoadTravelResponse
from services.ai_schemas import AIItinerary
from services.itinerary_service import save_ai_itinerary

from services.planner_service import generate_valid_itinerary
from logging_config import setup_logging
from services.places_service import (get_places_by_city,clean_places,filter_places,)
import httpx
import logging

from services.ai_service import AIServiceError

from models import Trip,ItineraryDay,Activity,User
from services.auth_service import (hash_password,verify_password,create_access_token,decode_access_token)

from services.ai_schemas import AIItinerary, AIItineraryDay, AIActivity

from services.distance_service import (
    get_attraction_distances,
    get_road_travel_estimates,
)

from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
import logging

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


setup_logging()

app=FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")




def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user_uuid = UUID(user_id)

    except (InvalidTokenError, ValueError):
        raise credentials_exception

    user = session.get(User, user_uuid)

    if user is None:
        raise credentials_exception

    return user

def get_owned_trip(
    trip_id: UUID,
    current_user: User,
    session: Session,
) -> Trip:
    trip = (
        session.query(Trip)
        .filter(
            Trip.id == trip_id,
            Trip.user_id == current_user.id,
        )
        .first()
    )

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    return trip
    
@app.post("/trips")
def create_trip(trip:TripRequest,session:Session = Depends(get_session),current_user:User = Depends(get_current_user),):
    saved_trip= Trip(
        id=uuid4(),
        user_id = current_user.id,
        city=trip.city,
        travellers=trip.travellers,
        days=trip.days,
        budget_of_a_person=trip.budget_of_a_person,
        start_date=trip.start_date,
        end_date=trip.end_date,
        origin=trip.origin,
        preferences=trip.preferences,
        transport_preference=trip.transport_preference,
    )
    session.add(saved_trip)
    session.commit()
    session.refresh(saved_trip)
    trip_id = saved_trip.id
        
    daily_group_budget=trip.travellers*trip.budget_of_a_person/trip.days
    return {
        "id": trip_id,
        "city": trip.city,
        "origin": trip.origin,
        "travellers": trip.travellers,
        "budget_of_a_person": trip.budget_of_a_person,
        "days": trip.days,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "preferences": trip.preferences,
        "transport_preference": trip.transport_preference,
        "total_budget": trip.budget_of_a_person * trip.travellers,
        "daily_group_budget": daily_group_budget,
        }
    
@app.get(
    "/trips",
    response_model=list[TripResponse],
)
def get_trips(
    city: str | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = session.query(Trip).filter(
        Trip.user_id == current_user.id
    )

    if city is not None:
        query = query.filter(
            Trip.city == city
        )

    return query.all()

@app.get(
    "/trips/{trip_id}",
    response_model=TripResponse,
)
def get_trip(
    trip_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    saved_trip = (
        session.query(Trip)
        .filter(
            Trip.id == trip_id,
            Trip.user_id == current_user.id,
        )
        .first()
    )

    if saved_trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    return saved_trip
            
@app.delete("/trips/{trip_id}")
def delete_trip(
    trip_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    saved_trip = (
        session.query(Trip)
        .filter(
            Trip.id == trip_id,
            Trip.user_id == current_user.id,
        )
        .first()
    )

    if saved_trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    session.delete(saved_trip)
    session.commit()

    return {
        "message": "Trip deleted successfully"
    }

    

@app.get("/health")
def health():
    return {"status":"Ok"}

@app.get(
    "/trips/{trip_id}/itinerary-days",
    response_model=list[ItineryDayResponse],
    
)

@app.post(
    "/trips/{trip_id}/itinerary-days",
    response_model=ItineryDayResponse,
)
def create_itinerary_day(
    trip_id: UUID,
    itinery_day: ItineryDayRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    saved_trip = get_owned_trip(
        trip_id,
        current_user,
        session,
    )

    if itinery_day.day_number > saved_trip.days:
        raise HTTPException(
            status_code=400,
            detail=f"Trip only has {saved_trip.days} days",
        )

    existing_day = (
        session.query(ItineraryDay)
        .filter(
            ItineraryDay.trip_id == trip_id,
            ItineraryDay.day_number == itinery_day.day_number,
        )
        .first()
    )

    if existing_day is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Day {itinery_day.day_number} "
                "already exists for this trip"
            ),
        )

    saved_day = ItineraryDay(
        trip_id=saved_trip.id,
        day_number=itinery_day.day_number,
        title=itinery_day.title,
    )

    session.add(saved_day)
    session.commit()
    session.refresh(saved_day)

    return saved_day


def get_itinerary_days(
    trip_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Verify trip exists and belongs to current user
    saved_trip = get_owned_trip(
        trip_id,
        current_user,
        session,
    )

    itinerary_days = (
        session.query(ItineraryDay)
        .filter(
            ItineraryDay.trip_id == saved_trip.id
        )
        .all()
    )

    return itinerary_days


@app.post(
    "/itinerary-days/{itinerary_day_id}/activities",
    response_model=ActivityResponse,
)
def create_activity(
    itinerary_day_id: UUID,
    activity: ActivityRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    saved_day = (
        session.query(ItineraryDay)
        .join(Trip, ItineraryDay.trip_id == Trip.id)
        .filter(
            ItineraryDay.id == itinerary_day_id,
            Trip.user_id == current_user.id,
        )
        .first()
    )

    if saved_day is None:
        raise HTTPException(
            status_code=404,
            detail="Itinerary day not found",
        )

    
    if activity.start_time is not None and activity.end_time is not None:
        overlapping_activity = (
            session.query(Activity)
            .filter(
                Activity.itinerary_day_id == itinerary_day_id,
                Activity.start_time.is_not(None),
                Activity.end_time.is_not(None),
                Activity.start_time < activity.end_time,
                Activity.end_time > activity.start_time,
                )
            .first()
            )
        if overlapping_activity is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Activity overlaps with '{overlapping_activity.title}'",
                )
            
    
    saved_activity = Activity(
        itinerary_day_id=saved_day.id,
        title=activity.title,
        location=activity.location,
        estimated_cost=activity.estimated_cost,
        notes=activity.notes,
        start_time=activity.start_time,
        end_time=activity.end_time,
    )

    session.add(saved_activity)
    session.commit()
    session.refresh(saved_activity)

    return saved_activity



@app.get(
    "/itinerary-days/{itinerary_day_id}/activities",
    response_model=list[ActivityResponse],
)
def get_activities(
    itinerary_day_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    saved_day = session.get(
        ItineraryDay,
        itinerary_day_id,
    )

    if saved_day is None:
        raise HTTPException(
            status_code=404,
            detail="Itinerary day not found",
        )

    # Verify that this itinerary day belongs
    # to the logged-in user's trip
    get_owned_trip(
        saved_day.trip_id,
        current_user,
        session,
    )

    activities = (
        session.query(Activity)
        .filter(
            Activity.itinerary_day_id == itinerary_day_id
        )
        .order_by(Activity.start_time)
        .all()
    )

    return activities


@app.put(
    "/trips/{trip_id}",
    response_model=TripResponse,
)
def update_trip(
    trip_id: UUID,
    trip: TripRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    saved_trip = (
        session.query(Trip)
        .filter(
            Trip.id == trip_id,
            Trip.user_id == current_user.id,
        )
        .first()
    )

    if saved_trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    saved_trip.city = trip.city
    saved_trip.travellers = trip.travellers
    saved_trip.budget_of_a_person = trip.budget_of_a_person
    saved_trip.days = trip.days
    saved_trip.start_date = trip.start_date
    saved_trip.end_date = trip.end_date
    saved_trip.preferences = trip.preferences
    saved_trip.origin = trip.origin
    saved_trip.transport_preference = trip.transport_preference

    session.commit()
    session.refresh(saved_trip)

    return saved_trip


@app.get(
    "/trips/{trip_id}/full-itinerary",
    response_model=TripDetailResponse,
)
def get_full_itinerary(
    trip_id: UUID,
    session: Session = Depends(get_session),current_user:User=Depends(get_current_user),):

    trip = (
        session.query(Trip)
        .options(
            selectinload(Trip.itinerary_days)
            .selectinload(ItineraryDay.activities)
        )
        .filter(Trip.id == trip_id,Trip.user_id == current_user.id)
        .first()
    )

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    return trip


@app.get(
    "/trips/{trip_id}/road-estimates",
    response_model=TripRoadTravelResponse,
)
def get_trip_road_estimates(
    trip_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Retrieve the trip with ownership verification
    trip = get_full_itinerary(
        trip_id=trip_id,
        session=session,
        current_user=current_user,
    )

    places = []
    itinerary_days = []

    for day in sorted(
        trip.itinerary_days,
        key=lambda day: day.day_number,
    ):
        activities = []

        for activity in sorted(
            day.activities,
            key=lambda a: (
                a.start_time is None,
                a.start_time,
            ),
        ):
            activities.append(
                AIActivity.model_validate(
                    activity,
                    from_attributes=True,
                )
            )

            if (
                activity.activity_type == "attraction"
                and activity.place_id
                and activity.latitude is not None
                and activity.longitude is not None
            ):
                places.append({
                    "name": activity.location,
                    "place_id": activity.place_id,
                    "latitude": activity.latitude,
                    "longitude": activity.longitude,
                })

        itinerary_days.append(
            AIItineraryDay(
                day_number=day.day_number,
                title=day.title,
                activities=activities,
            )
        )

    itinerary = AIItinerary(
        city=trip.city,
        days=itinerary_days,
    )

    legs = get_attraction_distances(
        itinerary=itinerary,
        places=places,
    )

    routes = get_road_travel_estimates(
        itinerary=itinerary,
        places=places,
        max_routes=5,
    )

    return {
        "trip_id": trip.id,
        "eligible_legs": sum(
            leg["available_minutes"] is not None
            for leg in legs
        ),
        "checked_legs": len(routes),
        "routes": [
            {
                "day": route["day"],
                "from_activity": route["from"],
                "to_activity": route["to"],
                "from_place_id": route["from_place_id"],
                "to_place_id": route["to_place_id"],
                "straight_line_distance_km": route["distance_km"],
                "road_distance_km": route["road_distance_km"],
                "driving_minutes": route["driving_minutes"],
                "available_minutes": route["available_minutes"],
                "road_travel_warning": route["road_travel_warning"],
            }
            for route in routes
        ],
    }


@app.get(
    "/trips/{trip_id}/budget-summary",
    response_model=BudgetSummaryResponse,
)
def get_budget_summary(
    trip_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    trip = (
        session.query(Trip)
        .options(
            selectinload(Trip.itinerary_days)
            .selectinload(ItineraryDay.activities)
        )
        .filter(
            Trip.id == trip_id,
            Trip.user_id == current_user.id,
        )
        .first()
    )

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )
        
    total_budget = (
        trip.budget_of_a_person * trip.travellers
    )

    category_breakdown = {
        "transport": 0,
        "accommodation": 0,
        "food": 0,
        "attraction": 0,
        "other": 0,
    }

    for day in trip.itinerary_days:
        for activity in day.activities:
            category = activity.activity_type

            if category not in category_breakdown:
                category = "other"

            category_breakdown[category] += (
                activity.estimated_cost
            )

    estimated_spent = sum(category_breakdown.values())

    remaining_budget = total_budget - estimated_spent

    estimated_cost_per_person = round(
        estimated_spent / trip.travellers, 2
    )

    budget_utilization_percentage = round(
        (estimated_spent / total_budget) * 100, 2
    )
    
    
    daily_breakdown = [
        {
            "day_number": day.day_number,
            "title": day.title,
            "estimated_spent": sum(
                activity.estimated_cost
                for activity in day.activities
            ),
        }
        for day in sorted(
            trip.itinerary_days,
            key=lambda day: day.day_number,
        )
    ]


    return BudgetSummaryResponse(
        total_budget=total_budget,
        estimated_spent=estimated_spent,
        remaining_budget=remaining_budget,
        estimated_cost_per_person=estimated_cost_per_person,
        budget_utilization_percentage=budget_utilization_percentage,
        category_breakdown=category_breakdown,
        daily_breakdown=daily_breakdown,
    )

    
@app.delete("/activities/{activity_id}")
def delete_activity(
    activity_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    saved_activity = session.get(
        Activity,
        activity_id,
    )

    if saved_activity is None:
        raise HTTPException(
            status_code=404,
            detail="Activity not found",
        )

    # Find the itinerary day
    saved_day = session.get(
        ItineraryDay,
        saved_activity.itinerary_day_id,
    )

    if saved_day is None:
        raise HTTPException(
            status_code=404,
            detail="Itinerary day not found",
        )

    # Verify ownership of the parent trip
    get_owned_trip(
        saved_day.trip_id,
        current_user,
        session,
    )

    session.delete(saved_activity)
    session.commit()

    return {
        "message": "Activity deleted successfully"
    }
    
@app.put(
    "/activities/{activity_id}",
    response_model=ActivityResponse,
)
def update_activity(
    activity_id: UUID,
    activity: ActivityRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    saved_activity = session.get(
        Activity,
        activity_id,
    )

    if saved_activity is None:
        raise HTTPException(
            status_code=404,
            detail="Activity not found",
        )

    # Find the itinerary day this activity belongs to
    saved_day = session.get(
        ItineraryDay,
        saved_activity.itinerary_day_id,
    )

    if saved_day is None:
        raise HTTPException(
            status_code=404,
            detail="Itinerary day not found",
        )

    # Verify that the trip belongs to the logged-in user
    get_owned_trip(
        saved_day.trip_id,
        current_user,
        session,
    )

    # Check activity time overlap
    if (
        activity.start_time is not None
        and activity.end_time is not None
    ):
        overlapping_activity = (
            session.query(Activity)
            .filter(
                Activity.itinerary_day_id
                == saved_activity.itinerary_day_id,

                # Don't compare activity with itself
                Activity.id != activity_id,

                Activity.start_time.is_not(None),
                Activity.end_time.is_not(None),
                Activity.start_time < activity.end_time,
                Activity.end_time > activity.start_time,
            )
            .first()
        )

        if overlapping_activity is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Activity overlaps with "
                    f"'{overlapping_activity.title}'"
                ),
            )
    

    # Clear geographic data when the place changes
    if (
        saved_activity.location != activity.location
        or saved_activity.title != activity.title
    ):
        saved_activity.place_id = None
        saved_activity.latitude = None
        saved_activity.longitude = None


    saved_activity.title = activity.title
    saved_activity.location = activity.location
    saved_activity.estimated_cost = activity.estimated_cost
    saved_activity.notes = activity.notes
    saved_activity.start_time = activity.start_time
    saved_activity.end_time = activity.end_time

    session.commit()
    session.refresh(saved_activity)

    return saved_activity


# @app.get("/test-itinerary")
# def test_itinerary():
#     itinerary = generate_itinerary(
#         city="Munnar",
#         days=2,
#         travellers=2,
#         budget_per_person=5000
#     )
#     return itinerary
@app.post(
    "/trips/{trip_id}/generate-itinerary",
    response_model=AIItinerary,
)
def generate_trip_itinerary(
    trip_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # 1. Find trip belonging to the logged-in user
    trip = (
        session.query(Trip)
        .filter(
            Trip.id == trip_id,
            Trip.user_id == current_user.id,
        )
        .first()
    )

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )
    # Fetch attractions without blocking itinerary generation
    places_context = []

    try:
        raw_places = get_places_by_city(trip.city)
        cleaned_places = clean_places(raw_places)
        places_context = filter_places(cleaned_places)

    except (httpx.HTTPError, ValueError) as error:
        logger.warning(
            "Geoapify places unavailable for %s: %s",
            trip.city,
            type(error).__name__,
        )

    # 2. Generate and validate itinerary
    try:
        validated_itinerary = generate_valid_itinerary(
            city=trip.city,
            days=trip.days,
            travellers=trip.travellers,
            budget_per_person=trip.budget_of_a_person,
            start_date=trip.start_date,
            end_date=trip.end_date,
            preferences=trip.preferences,
            origin=trip.origin,
            transport_preference=trip.transport_preference,
            places_context=places_context,
        )

    except AIServiceError:
        raise HTTPException(
            status_code=503,
            detail="AI Service is temporarily unavailable",
        )

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        )

    # 3. Save validated itinerary
    try:
        save_ai_itinerary(
            session=session,
            trip=trip,
            itinerary=validated_itinerary,
            places_context=places_context,
)

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to save generated itinerary",
        )

    # 4. Return generated itinerary
    return validated_itinerary
    


@app.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=201,
)
def register_user(
    user: UserRegisterRequest,
    session: Session = Depends(get_session),
):
    existing_user = (
        session.query(User)
        .filter(User.email == user.email)
        .first()
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    saved_user = User(
        email=user.email,
        hashed_password=hash_password(user.password),
    )

    session.add(saved_user)
    session.commit()
    session.refresh(saved_user)

    return saved_user

@app.post(
    "/auth/login",
    response_model=TokenResponse,
)
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    user = (
        session.query(User)
        .filter(User.email == form_data.username)
        .first()
    )

    if user is None or not verify_password(
        form_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    access_token = create_access_token(
        str(user.id)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
    
def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user_uuid = UUID(user_id)

    except (InvalidTokenError, ValueError):
        raise credentials_exception

    user = session.get(User, user_uuid)

    if user is None:
        raise credentials_exception

    return user

@app.get(
    "/auth/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user