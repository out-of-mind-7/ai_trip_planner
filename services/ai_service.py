import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

import logging
import time
from services.ai_validator  import validate_place_locations
from services.ai_schemas import AIItinerary
from datetime import date
from pydantic import ValidationError

load_dotenv()


client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(
        timeout=45000,
        retry_options=types.HttpRetryOptions(
            attempts=1,
        ),
    ),
)


logger = logging.getLogger(__name__)

class AIServiceError(Exception):
    pass


def generate_itinerary(
    city: str,
    days: int,
    travellers: int,
    budget_per_person: int,
    start_date: date | None = None,
    end_date: date | None = None,
    preferences: str | None = None,
    feedback: str | None = None,
    origin: str | None = None,
    transport_preference: str | None = None,
    weather_context=None,
    places_context=None,
) -> AIItinerary:

    total_budget = budget_per_person * travellers
    planning_budget = total_budget * 90 // 100

    prompt = f"""
    Create a realistic travel itinerary.

    Origin: {origin or "Not provided"}
    Destination: {city}
    Number of days: {days}
    Travellers: {travellers}
    Budget per person: ₹{budget_per_person}
    Total group budget: ₹{total_budget}
    Target itinerary budget: ₹{planning_budget}
    Start date: {start_date or "Not provided"}
    End date: {end_date or "Not provided"}
    Traveller preferences: {preferences or "No specific preferences"}
    Preferred transport: {transport_preference or "No preference"}

    Weather information:
    {weather_context if weather_context else "Live weather forecast is not available for these travel dates."}

    Requirements:
    - Generate exactly {days} days.
    - Day numbers must start at 1 and be sequential.
    - Keep the total estimated activity cost within ₹{total_budget}.
    - Prioritize the traveller's preferences.
    - Give realistic activity locations.
    - Give an estimated cost for each activity.
    - Give sensible start and end times.
    - Do not create overlapping activities.
    - Keep travel time between locations realistic.
    - Consider the preferred transport when planning.
    - Use transport preference only for planning.
    - Do not invent train numbers, flight numbers, live fares, schedules, or availability.
    - If real-time transport information is required, mark it as requiring external verification.
    - Consider the provided weather information when choosing activities.
    - If rain is expected, prefer suitable indoor activities during that period.
    - Do not invent weather information when forecast data is unavailable.
    Activity classification requirements:
    - Every activity must include an activity_type.
    - Use only these values:
    attraction, transport, accommodation, food, other.
    - Use "attraction" for sightseeing, museums, gardens,
    viewpoints, and tourist destinations.
    - Use "transport" for driving, train journeys,
    transfers, and other travel between locations.
    - Use "accommodation" for hotel check-in, checkout,
    and lodging-related activities.
    - Use "food" for meals and restaurant visits.
    - Use "other" only when none of the above applies.
    - Classify activities based on their actual purpose.
    - Do not classify transport as an attraction.
    - Activity start_time and end_time must represent
    destination-local clock times in HH:MM:SS format.
    - Do not append Z or timezone offsets to activity times.
    - Every activity must have a start_time and end_time.
    - Never use null for activity times.
    - Include realistic travel durations for transport activities.
    - Schedule meals and hotel check-in/check-out explicitly.
    - All activity times must be in destination-local time.
    - For attractions selected from Geoapify, include the exact place_id from the provided dataset.
    - Never invent or modify a place_id.
    - For activities without a matching Geoapify place,set place_id to null.
    - When using a Geoapify place_id, copy the exact
    corresponding Geoapify name into activity.location.
    - Preserve the original language, including Tamil.
    - Do not translate or modify that location name.
    - The activity title can remain in English.
    - The place_id and location must come from the same Geoapify record.
    
    - The total estimated cost of all activities must not exceed
    the target itinerary budget of ₹{planning_budget}.
    - Reserve the remaining 10% for unexpected expenses.
    - Before finalizing, add up every activity's estimated_cost.
    - Include realistic transport, accommodation, food,
    and attraction expenses.
    - Do not artificially reduce prices or mark paid
    activities as free just to meet the budget.
    - If the plan is too expensive, choose more affordable
    activities or accommodation.
    
    """

    if places_context:
        prompt += f"""

        VERIFIED PLACE DATA FROM GEOAPIFY:
        {places_context}

        Place selection requirements:
        - Prefer attractions from the provided dataset.
        - Use the actual place names from the dataset.
        - Consider their coordinates when planning travel.
        - Group nearby attractions together where practical.
        - Avoid scheduling distant attractions too close together.
        - Do not invent addresses or coordinates.
        - Do not claim that a place is verified unless it appears in the dataset.
        - Do not assume that listed places are currently open.
        - Treat opening hours, ticket prices, and availability as unverified unless supplied.
        """

    if feedback:
        prompt += f"""

        Your previous itinerary was rejected.

        Validation error:
        {feedback}

        Generate a corrected itinerary that fixes this problem.
        """

    start_time = time.perf_counter()

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIItinerary,
            ),
        )

    except Exception as error:
        duration = time.perf_counter() - start_time

        logger.error(
            "Gemini request failed after %.2f seconds: %s",
            duration,
            type(error).__name__,
        )

        raise AIServiceError(
            "AI service is temporarily unavailable"
        ) from error

        

    duration = time.perf_counter() - start_time

    logger.info(
        "Gemini itinerary generation completed in %.2f seconds",
        duration,
    )
    
    
    if isinstance(response.parsed, AIItinerary):
        return response.parsed

    try:
        return AIItinerary.model_validate_json(
            response.text or ""
        )

    except ValidationError:
        logger.warning(
            "Gemini response failed schema validation"
        )

        raise ValueError(
            "Generate a valid itinerary matching "
            "the required response schema."
        ) from None


    