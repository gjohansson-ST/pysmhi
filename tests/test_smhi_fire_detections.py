"""Tests for SMHI fire detections."""

import json
import pathlib
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import aiohttp
import pytest
from aiointercept import aiointercept
from freezegun import freeze_time
from syrupy.assertion import SnapshotAssertion

from pysmhi import (
    SMHIFireDetectionAnomaly,
    SMHIFireDetectionConfidence,
    SmhiFireDetectionException,
    SMHIFireDetections,
)
from pysmhi.smhi_fire_detections import _distance, get_fire_detections

from .conftest import request_count

URL = (
    "https://opendata-download-satellite.smhi.se/api/category"
    "/firedetections/version/1/year/{}/month/{}/data.json"
)
EMPTY = {"type": "FeatureCollection", "features": []}

GAVLE = (17.1413, 60.6749)
LULEA = (22.1567, 65.5848)


@pytest.fixture(autouse=True)
async def mock_sleep() -> AsyncGenerator[None]:
    """Mock no sleeping."""
    with patch("asyncio.sleep"):
        yield


def _load(month: str) -> dict[str, Any]:
    """Load the fire detections for a month in 2026."""
    data = pathlib.Path(f"tests/fire_detections_2026_{month}.json").read_text()  # pylint: disable=unspecified-encoding
    json_data: dict[str, Any] = json.loads(data)
    return json_data


@pytest.fixture(name="october")
def get_october() -> list[dict[str, Any]]:
    """Return the fire detections for October 2026."""
    features: list[dict[str, Any]] = _load("10")["features"]
    return features


@freeze_time("2026-10-21T12:00:00+02:00")
async def test_api(
    mock_aiointercept: aiointercept,
    snapshot: SnapshotAssertion,
) -> None:
    """Test api with a period over two months."""
    mock_aiointercept.get(URL.format(2026, "09"), payload=_load("09"))
    mock_aiointercept.get(URL.format(2026, "10"), payload=_load("10"))

    async with aiohttp.ClientSession() as session:
        client = SMHIFireDetections("17.1413", "60.6749", session)
        result = await client.async_get_fire_detections(radius=450, days=30)

    assert request_count(mock_aiointercept) == 2
    # 20260930-1 is from September and 20260922-1 is outside the radius
    assert [detection["id"] for detection in result] == [
        "20261007-1",
        "20261006-4",
        "20261006-2",
        "20261006-3",
        "20261006-1",
        "20260930-1",
    ]
    assert result == snapshot


@freeze_time("2026-10-19T03:30:00+02:00")
async def test_defaults(mock_aiointercept: aiointercept) -> None:
    """Test default radius of 50 km and period of 7 days, newest first."""
    mock_aiointercept.get(URL.format(2026, "10"), payload=_load("10"))

    async with aiohttp.ClientSession() as session:
        client = SMHIFireDetections("22.1567", "65.5848", session)
        result = await client.async_get_fire_detections()

    # Only October is requested as the period starts 2026-10-12 03:30 Swedish
    # time, which excludes 20261012-1 at 03:27. 20261017-1 and 20261017-2 are
    # about 180 km away.
    assert request_count(mock_aiointercept) == 1
    assert [detection["id"] for detection in result] == [
        "20261012-6",
        "20261012-5",
        "20261012-4",
        "20261012-3",
        "20261012-2",
    ]


@freeze_time("2026-01-03T12:00:00+01:00")
async def test_period_over_new_year(mock_aiointercept: aiointercept) -> None:
    """Test a period over new year requests December and January."""
    mock_aiointercept.get(URL.format(2025, "12"), payload=EMPTY)
    mock_aiointercept.get(URL.format(2026, "01"), payload=EMPTY)

    async with aiohttp.ClientSession() as session:
        client = SMHIFireDetections("17.1413", "60.6749", session)
        assert await client.async_get_fire_detections() == []

    assert request_count(mock_aiointercept) == 2


async def test_api_failure(mock_aiointercept: aiointercept) -> None:
    """Test api failure."""
    url = URL.format(2026, "10")
    mock_aiointercept.get(url, status=500, reason="Internal Server Error", repeat=True)

    async with aiohttp.ClientSession() as session:
        client = SMHIFireDetections("17.1413", "60.6749", session)
        with (
            freeze_time("2026-10-21T12:00:00+02:00"),
            pytest.raises(
                SmhiFireDetectionException,
                match=f"500, message='Internal Server Error', url='{url}'",
            ),
        ):
            await client.async_get_fire_detections(days=1)


@pytest.mark.parametrize(
    ("radius", "expected"),
    [
        (8.4, []),
        (8.5, ["20261007-1"]),
        # 20261006-2 and 20261006-3 have the same time and keep the API order
        (17, ["20261007-1", "20261006-2", "20261006-3", "20261006-1"]),
    ],
)
def test_radius(
    october: list[dict[str, Any]], radius: float, expected: list[str]
) -> None:
    """Test only detections within the radius are included."""
    result = get_fire_detections(october, *GAVLE, radius=radius)

    assert [detection["id"] for detection in result] == expected
    assert all(detection["distance"] <= radius for detection in result)


def test_distance() -> None:
    """Test the distance between Stockholm and Gothenburg."""
    assert round(_distance(18.0686, 59.3293, 11.9746, 57.7089)) == 397


@pytest.mark.parametrize(
    ("observation_time", "expected"),
    [
        ("2026-10-06T02:37:32", datetime(2026, 10, 6, 0, 37, 32, tzinfo=UTC)),
        ("2026-02-04T03:09:39", datetime(2026, 2, 4, 2, 9, 39, tzinfo=UTC)),
    ],
    ids=["summer_time", "winter_time"],
)
def test_observation_time(
    october: list[dict[str, Any]], observation_time: str, expected: datetime
) -> None:
    """Test the observation time is converted from Swedish time to UTC."""
    october[0]["properties"]["observation_time"] = observation_time

    result = get_fire_detections(october[:1], *october[0]["geometry"]["coordinates"])

    assert result[0]["observation_time"] == expected


def test_since(october: list[dict[str, Any]]) -> None:
    """Test detections before since are excluded."""
    since = datetime(2026, 10, 12, 1, 30, tzinfo=UTC)

    result = get_fire_detections(october, *LULEA, since=since)

    assert [detection["id"] for detection in result][-1] == "20261012-2"


def test_enums(october: list[dict[str, Any]]) -> None:
    """Test confidence and anomaly are converted to enums."""
    october[0]["properties"]["confidence"] = 9
    october[0]["properties"]["anomaly"] = 1

    result = get_fire_detections(october[:1], *october[0]["geometry"]["coordinates"])

    assert result[0]["confidence"] is SMHIFireDetectionConfidence.HIGH
    assert result[0]["anomaly"] is SMHIFireDetectionAnomaly.GAS_FLARE


def test_unknown_values(
    october: list[dict[str, Any]], caplog: pytest.LogCaptureFixture
) -> None:
    """Test unknown confidence and anomaly values give None."""
    october[0]["properties"]["confidence"] = 10
    october[0]["properties"]["anomaly"] = 6

    result = get_fire_detections(october[:1], *october[0]["geometry"]["coordinates"])

    assert result[0]["confidence"] is None
    assert result[0]["anomaly"] is None
    assert "Unknown SMHIFireDetectionConfidence value 10" in caplog.text
    assert "Unknown SMHIFireDetectionAnomaly value 6" in caplog.text
