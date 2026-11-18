import pytest
import httpx

from services import places_service



@pytest.mark.parametrize("status_code, content", [
    (429, b'{"error": "Rate limit exceeded"}'),
    (500, b'{"error": "Server error"}'),
    (200, b'invalid json'),
    (200, b'{"features": null}'),
])
def test_invalid_places_response(
    monkeypatch, status_code, content
):
    monkeypatch.setattr(
        places_service,
        "GEOAPIFY_API_KEY",
        "test-key",
    )

    monkeypatch.setattr(
        places_service.httpx,
        "get",
        lambda *args, **kwargs: httpx.Response(
            status_code,
            content=content,
        ),
    )

    with pytest.raises(places_service.PlacesServiceError):
        places_service.get_places_by_coordinates(
            11.4, 76.7
        )


def test_clean_places_skips_invalid_records():
    places = [
        None,
        {},
        {
            "properties": {"name": "Invalid Place"},
            "geometry": {"coordinates": [76.7, 100]},
        },
        {
            "properties": {
                "name": "Botanical Garden",
                "place_id": "garden-id",
            },
            "geometry": {
                "coordinates": [76.7105, 11.4175],
            },
        },
    ]

    result = places_service.clean_places(places)

    assert len(result) == 1
    assert result[0]["name"] == "Botanical Garden"
    assert result[0]["latitude"] == 11.4175
    assert result[0]["longitude"] == 76.7105
