from sqlalchemy.orm import Session
import logging

from models import Trip, ItineraryDay, Activity
from services.ai_schemas import AIItinerary

logger = logging.getLogger(__name__)

def save_ai_itinerary(
    session: Session,
    trip: Trip,
    itinerary: AIItinerary,
    places_context: list[dict] | None = None,
):
    try:
        # Create a lookup using verified Geoapify IDs
        places_by_id = {
            place["place_id"]: place
            for place in (places_context or [])
            if place.get("place_id")
        }

        # Delete existing itinerary
        for existing_day in list(trip.itinerary_days):
            session.delete(existing_day)

        session.flush()

        # Save new itinerary
        for ai_day in itinerary.days:
            saved_day = ItineraryDay(
                trip_id=trip.id,
                day_number=ai_day.day_number,
                title=ai_day.title,
            )

            session.add(saved_day)
            session.flush()

            for ai_activity in ai_day.activities:

                # Find the Geoapify record for attractions
                matched_place = None

                if (
                    ai_activity.activity_type == "attraction"
                    and ai_activity.place_id
                ):
                    matched_place = places_by_id.get(
                        ai_activity.place_id
                    )

                saved_activity = Activity(
                    itinerary_day_id=saved_day.id,
                    title=ai_activity.title,
                    location=ai_activity.location,
                    activity_type=ai_activity.activity_type,
                    place_id=(
                        matched_place["place_id"]
                        if matched_place else None
                    ),
                    latitude=(
                        matched_place.get("latitude")
                        if matched_place else None
                    ),
                    longitude=(
                        matched_place.get("longitude")
                        if matched_place else None
                    ),
                    estimated_cost=ai_activity.estimated_cost,
                    notes=ai_activity.notes,
                    start_time=ai_activity.start_time,
                    end_time=ai_activity.end_time,
                )

                session.add(saved_activity)

        session.commit()

        logger.info(
            "AI itinerary saved successfully for trip %s",
            trip.id,
        )

    except Exception:
        session.rollback()

        logger.exception(
            "Failed to save AI itinerary for trip %s",
            trip.id,
        )

        raise
