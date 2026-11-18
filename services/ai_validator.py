from services.ai_schemas import AIItinerary
import re


def validate_itinerary(
    itinerary: AIItinerary,
    expected_days: int,
    total_budget: int,
) -> AIItinerary:
    # Check number of days
    if len(itinerary.days) != expected_days:
        raise ValueError(
            f"Expected {expected_days} days, "
            f"but AI generated {len(itinerary.days)}"
        )

    # Check day numbers
    expected_day_numbers = set(range(1, expected_days + 1))
    actual_day_numbers = {
        day.day_number for day in itinerary.days
    }

    if actual_day_numbers != expected_day_numbers:
        raise ValueError("Invalid or duplicate day numbers")

    # Calculate estimated spending
    estimated_spent = sum(
        activity.estimated_cost
        for day in itinerary.days
        for activity in day.activities
    )

    # Check budget
    if estimated_spent > total_budget:
        raise ValueError(
            f"Itinerary exceeds budget: "
            f"₹{estimated_spent} > ₹{total_budget}"
        )

    # Check activity time overlaps
    # Check activity times and overlaps
    for day in itinerary.days:
        for activity in day.activities:

            # Every activity must have start and end times
            if activity.start_time is None or activity.end_time is None:
                raise ValueError(
                    f"Day {day.day_number}: "
                    f"Activity '{activity.title}' must have "
                    "both start_time and end_time"
                )

            # End time must be after start time
            if activity.end_time <= activity.start_time:
                raise ValueError(
                    f"Invalid activity time on Day {day.day_number}: "
                    f"'{activity.title}' ends before or at its start time"
                )
            
        timed_activities = [
            activity
            for activity in day.activities
            if activity.start_time is not None
            and activity.end_time is not None
        ]

        timed_activities.sort(
            key=lambda activity: activity.start_time
        )

        for i in range(len(timed_activities) - 1):
            current_activity = timed_activities[i]
            next_activity = timed_activities[i + 1]

            if current_activity.end_time > next_activity.start_time:
                raise ValueError(
                    f"Overlapping activities on Day {day.day_number}: "
                    f"'{current_activity.title}' and "
                    f"'{next_activity.title}'"
                )

    return itinerary




def validate_place_locations(
    itinerary: AIItinerary,
    places: list[dict],
) -> list[str]:
    """Return attraction locations that do not match supplied places."""

    if not places:
        return []

    def normalize(name: str) -> str:
        return " ".join(name.casefold().split())

    known_names = {
        normalize(place["name"])
        for place in places
        if place.get("name")
    }

    unmatched = []

    for day in itinerary.days:
        for activity in day.activities:

            # Only check tourist attractions
            if activity.activity_type != "attraction":
                continue

            location = normalize(activity.location)

            # 1. Exact name match
            if location in known_names:
                continue

            # 2. Remove address suffix
            base_location = normalize(
                activity.location.split(",", 1)[0]
            )

            if base_location in known_names:
                continue

            # 3. Match sufficiently specific partial names
            partial_match = any(
                (
                    base_location in known_name
                    or known_name in base_location
                )
                for known_name in known_names
                if len(base_location) >= 10
                and len(known_name) >= 10
            )

            if partial_match:
                continue

            # 4. No matching place found
            unmatched.append(activity.location)

    return unmatched



def validate_place_ids(
    itinerary: AIItinerary,
    places: list[dict],
) -> None:
    """Reject attraction place IDs not found in Geoapify data."""

    if not places:
        return

    valid_ids = {
        place["place_id"]
        for place in places
        if place.get("place_id")
    }

    for day in itinerary.days:
        for activity in day.activities:
            if activity.activity_type != "attraction":
                continue

            if activity.place_id is None:
                continue

            if activity.place_id not in valid_ids:
                raise ValueError(
                    f"Day {day.day_number}: "
                    f"Invalid Geoapify place_id "
                    f"'{activity.place_id}' for "
                    f"'{activity.title}'"
                )



def validate_place_ids(
    itinerary: AIItinerary,
    places: list[dict],
) -> None:
    """Check Geoapify IDs and their attraction names."""

    if not places:
        return

    places_by_id = {
        place["place_id"]: place
        for place in places
        if place.get("place_id")
    }

    def get_words(value: str) -> set[str]:
        return set(re.findall(r"\w+", value.casefold()))

    for day in itinerary.days:
        for activity in day.activities:
            if activity.activity_type != "attraction":
                continue

            if activity.place_id is None:
                continue

            matched_place = places_by_id.get(activity.place_id)

            if matched_place is None:
                raise ValueError(
                    f"Invalid Geoapify place_id "
                    f"'{activity.place_id}' for '{activity.title}'"
                )

            
            place_name = matched_place.get("name", "")

            # Accept an exact Geoapify name, including
            # names written in Tamil or other languages.
            def normalize_name(value: str) -> str:
                return " ".join(value.casefold().split())

            if (
                place_name
                and normalize_name(activity.location)
                == normalize_name(place_name)
            ):
                continue

            place_words = get_words(place_name)


            title_words = get_words(activity.title)
            location_words = get_words(activity.location)

            title_matches = len(place_words & title_words)
            location_matches = len(place_words & location_words)

            required_matches = 1 if len(place_words) == 1 else 2

            if (
                not place_words
                or max(title_matches, location_matches) < required_matches
            ):
                raise ValueError(
                    f"Geoapify place_id does not match attraction "
                    f"'{activity.title}'. "
                    f"Expected place: '{place_name}'"
                )
