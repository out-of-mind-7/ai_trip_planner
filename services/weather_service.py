
import httpx
import logging

from datetime import date, timedelta

logger = logging.getLogger(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherServiceError(ValueError):
    pass


def get_json(url: str, params: dict) -> dict:
    try:
        response = httpx.get(
            url,
            params=params,
            timeout=httpx.Timeout(10.0, connect=3.0),
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            raise ValueError("Invalid response")

        return data

    except (httpx.HTTPError, ValueError) as error:
        raise WeatherServiceError(
            f"Weather API request failed: {type(error).__name__}"
        ) from None


def get_coordinates(city: str):
    params = {
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json",
    }

    data = get_json(GEOCODING_URL, params)

    results = data.get("results")

    if not isinstance(results, list) or not results:
        raise WeatherServiceError(
            f"Could not find location: {city}"
        )

    location = results[0]

    try:
        latitude = location["latitude"]
        longitude = location["longitude"]

        if not (
            -90 <= latitude <= 90
            and -180 <= longitude <= 180
        ):
            raise ValueError("Invalid coordinates")

        return {
            "name": location["name"],
            "latitude": latitude,
            "longitude": longitude,
            "timezone": location.get("timezone"),
            "country": location.get("country"),
        }

    except (KeyError, TypeError, ValueError):
        raise WeatherServiceError(
            "Invalid geocoding response"
        ) from None


def get_weather_forecast(
    city: str,
    start_date: date,
    end_date: date,
):
    location = get_coordinates(city)

    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "daily": (
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_probability_max"
        ),
        "timezone": "auto",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }

    data = get_json(FORECAST_URL, params)

    daily = data.get("daily")

    if not isinstance(daily, dict):
        raise WeatherServiceError(
            "Invalid daily forecast"
        )

    dates = daily.get("time")

    if not isinstance(dates, list) or not dates:
        raise WeatherServiceError(
            "Forecast dates are unavailable"
        )

    required_fields = [
        "temperature_2m_max",
        "temperature_2m_min",
        "precipitation_probability_max",
    ]

    for field in required_fields:
        values = daily.get(field)

        if (
            not isinstance(values, list)
            or len(values) != len(dates)
        ):
            raise WeatherServiceError(
                f"Invalid forecast field: {field}"
            )

    return {
        "location": location["name"],
        "country": location["country"],
        "daily": daily,
    }


def get_weather_context(
    city: str,
    start_date: date | None,
    end_date: date | None,
):
    if start_date is None or end_date is None:
        logger.info(
            "Weather skipped for %s: No travel dates",
            city,
        )
        return None

    today = date.today()
    forecast_limit = today + timedelta(days=15)

    if (
        end_date < start_date
        or start_date < today
        or start_date > forecast_limit
    ):
        logger.info(
            "Weather skipped for %s: Dates outside forecast range",
            city,
        )
        return None

    try:
        weather = get_weather_forecast(
            city=city,
            start_date=start_date,
            end_date=min(end_date, forecast_limit),
        )

        logger.info(
            "Weather forecast successfully fetched for %s",
            city,
        )

        return weather

    except WeatherServiceError as error:
        logger.warning(
            "Weather forecast unavailable for %s: %s",
            city,
            error,
        )

        return None
