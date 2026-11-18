from services.ai_service import generate_itinerary
from services.ai_validator import validate_itinerary, validate_place_locations
from services.ai_schemas import AIItinerary

from services.weather_service import get_weather_context
from services.ai_validator import validate_place_ids
from services.distance_service import get_attraction_distances
from services.distance_service import get_road_travel_estimates

import logging

logger = logging.getLogger(__name__)



def enrich_activity_coordinates(
    itinerary: AIItinerary,
    places: list[dict] | None,
) -> AIItinerary:

    places_by_id = {
        place["place_id"]: place
        for place in (places or [])
        if place.get("place_id")
    }

    for day in itinerary.days:
        for activity in day.activities:

            # Remove any AI-generated coordinates
            activity.latitude = None
            activity.longitude = None

            if activity.activity_type != "attraction":
                activity.place_id = None
                continue

            matched_place = places_by_id.get(
                activity.place_id
            )

            if matched_place is None:
                activity.place_id = None
                continue

            # Use coordinates from Geoapify
            activity.latitude = matched_place.get("latitude")
            activity.longitude = matched_place.get("longitude")

    return itinerary


def generate_valid_itinerary(
    city: str,
    days: int,
    travellers: int,
    budget_per_person: int,
    start_date=None,
    end_date=None,
    preferences=None,
    origin=None,
    transport_preference=None,
    max_attempts: int = 2,
    places_context=None,
) -> AIItinerary:

    total_budget = budget_per_person * travellers
    feedback = None

    # Get weather information
    weather_context = get_weather_context(
        city=city,
        start_date=start_date,
        end_date=end_date,
    )

    if weather_context:
        logger.info("Weather context available for %s", city)
    else:
        logger.info("Weather context unavailable for %s", city)

    # Log places availability
    if places_context:
        logger.info(
            "Geoapify provided %s places for %s",
            len(places_context),
            city,
        )
    else:
        logger.info(
            "Geoapify places unavailable for %s",
            city,
        )
        
        
    for attempt in range(max_attempts):
        logger.info(
            "Generating itinerary for %s - attempt %s/%s",
            city,
            attempt + 1,
            max_attempts,
        )

        try:
            itinerary = generate_itinerary(
                city=city,
                days=days,
                travellers=travellers,
                budget_per_person=budget_per_person,
                start_date=start_date,
                end_date=end_date,
                preferences=preferences,
                origin=origin,
                transport_preference=transport_preference,
                weather_context=weather_context,
                places_context=places_context,
                feedback=feedback,
            )

            validated_itinerary = validate_itinerary(
                itinerary=itinerary,
                expected_days=days,
                total_budget=total_budget,
            )
            
            # Check attractions against Geoapify data
            if places_context:

                # Validate Geoapify place IDs
                validate_place_ids(
                    itinerary=validated_itinerary,
                    places=places_context,
                )

                # Check attraction names
                unmatched_locations = validate_place_locations(
                    itinerary=validated_itinerary,
                    places=places_context,
                )

                if unmatched_locations:
                    logger.warning(
                        "Unmatched attraction locations for %s: %s",
                        city,
                        unmatched_locations,
                    )

                    unmatched_set = set(unmatched_locations)

                    for day in validated_itinerary.days:
                        for activity in day.activities:
                            if (
                                activity.activity_type == "attraction"
                                and activity.location in unmatched_set
                            ):
                                logger.warning(
                                    "Day %s | Unmatched attraction: %s | Activity: %s",
                                    day.day_number,
                                    activity.location,
                                    activity.title,
                                )

                else:
                    logger.info(
                        "All attraction names matched supplied Geoapify places for %s",
                        city,
                    )
            
            # Check potential travel-time problems
            if places_context:
                travel_distances = get_attraction_distances(
                    itinerary=validated_itinerary,
                    places=places_context,
                )

                for leg in travel_distances:
                    
                    logger.info(
                        "Day %s | %s -> %s | "
                        "Distance: %.2f km | "
                        "Available: %s min | "
                        "Minimum: %.1f min",
                        leg["day"],
                        leg["from"],
                        leg["to"],
                        leg["distance_km"],
                        leg["available_minutes"],
                        leg["minimum_minutes"],
                    )

                    if leg["travel_warning"]:
                        
                        logger.warning(
                            "Day %s | Travel warning: %s -> %s | "
                            "Distance: %.2f km | "
                            "Available: %.1f min | "
                            "Minimum estimate: %.1f min",
                            leg["day"],
                            leg["from"],
                            leg["to"],
                            leg["distance_km"],
                            leg["available_minutes"],
                            leg["minimum_minutes"],
                        )

            
            # Check estimated driving times using Geoapify
            if places_context:
                road_estimates = []

                try:
                    road_estimates = get_road_travel_estimates(
                        itinerary=validated_itinerary,
                        places=places_context,
                        max_routes=5,
                    )

                    for route in road_estimates:
                        logger.info(
                            "Day %s | %s -> %s | "
                            "Driving distance: %.2f km | "
                            "Estimated driving time: %.1f min | "
                            "Available: %.1f min",
                            route["day"],
                            route["from"],
                            route["to"],
                            route["road_distance_km"],
                            route["driving_minutes"],
                            route["available_minutes"],
                        )

                        if route["road_travel_warning"]:
                            logger.warning(
                                "Day %s | Insufficient driving time: %s -> %s",
                                route["day"],
                                route["from"],
                                route["to"],
                            )

                except Exception:
                    logger.exception(
                        "Road travel estimates unavailable for %s",
                        city,
                    )
                    
            
            if places_context:
                road_warnings = [
                    route
                    for route in road_estimates
                    if route["road_travel_warning"]
                ]

                if road_warnings and attempt + 1 < max_attempts:
                    feedback = (
                        "Correct the following travel schedule problems:\n"
                    )

                    for route in road_warnings:
                        feedback += (
                            f"Day {route['day']}: "
                            f"{route['from']} to {route['to']} "
                            f"has only {route['available_minutes']} "
                            f"minutes available, but driving takes "
                            f"approximately {route['driving_minutes']} "
                            f"minutes. Allow sufficient travel time "
                            f"if travelling by car.\n"
                        )

                    logger.warning(
                        "Retrying itinerary due to travel-time problems"
                    )

                    continue


            logger.info(
                "Itinerary validation successful for %s",
                city,
            )

            return enrich_activity_coordinates(
                itinerary=validated_itinerary,
                places=places_context,
            )

        except ValueError as error:
            feedback = str(error)

            logger.warning(
                "Itinerary validation failed on attempt %s/%s: %s",
                attempt + 1,
                max_attempts,
                feedback,
            )

    # Outside the retry loop
    raise ValueError(
        f"AI failed to generate a valid itinerary "
        f"after {max_attempts} attempts. "
        f"Last error: {feedback}"
    )

    
    