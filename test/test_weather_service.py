
from datetime import date, timedelta

import pytest

from services import weather_service


def test_weather_skipped_without_dates():
    result = weather_service.get_weather_context(
        city="Ooty",
        start_date=None,
        end_date=None,
    )

    assert result is None


def test_weather_skipped_outside_forecast_range():
    future_date = date.today() + timedelta(days=30)

    result = weather_service.get_weather_context(
        city="Ooty",
        start_date=future_date,
        end_date=future_date + timedelta(days=2),
    )

    assert result is None


def test_weather_service_failure(monkeypatch):

    def fake_forecast(**kwargs):
        raise weather_service.WeatherServiceError(
            "Weather API unavailable"
        )

    monkeypatch.setattr(
        weather_service,
        "get_weather_forecast",
        fake_forecast,
    )

    result = weather_service.get_weather_context(
        city="Ooty",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=2),
    )

    assert result is None


def test_invalid_geocoding_response(monkeypatch):
    monkeypatch.setattr(
        weather_service,
        "get_json",
        lambda *args, **kwargs: {"results": []},
    )

    with pytest.raises(
        weather_service.WeatherServiceError
    ):
        weather_service.get_coordinates("Unknown City")
