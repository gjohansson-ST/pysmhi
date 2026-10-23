"""Tests for SMHI observations."""

import json
import pathlib
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from aiointercept import aiointercept
from syrupy.assertion import SnapshotAssertion

from pysmhi import (
    SmhiObservationException,
    SMHIObservationParameter,
    SMHIObservationQuality,
    SMHIPointObservations,
    SMHIPresentWeather,
)
from pysmhi.smhi_observations import PRESENT_WEATHER, get_observation

from .conftest import request_count

BASE_URL = "https://opendata-download-metobs.smhi.se/api/version/latest/parameter"
STATIONS_URL = f"{BASE_URL}/1/station-set/all/period/latest-hour/data.json"
PARAMETER_URL = BASE_URL + "/{}/station/{}/period/latest-hour/data.json"

MALMO = ("13.0038", "55.605")
MALMO_A = "52350"


@pytest.fixture(name="mock_sleep", autouse=True)
def get_mock_sleep() -> Generator[AsyncMock]:
    """Mock no sleeping."""
    with patch("asyncio.sleep") as mock_sleep:
        yield mock_sleep


@pytest.fixture(name="stations")
def get_stations() -> dict[str, Any]:
    """Return the temperature during the latest hour for all stations."""
    data = pathlib.Path("tests/observations_stations.json").read_text()  # pylint: disable=unspecified-encoding
    json_data: dict[str, Any] = json.loads(data)
    return json_data


@pytest.fixture(name="malmo")
def get_malmo() -> dict[str, Any]:
    """Return the data during the latest hour by parameter for Malmö A.

    Malmö A doesn't observe the snow depth.
    """
    data = pathlib.Path("tests/observations_52350.json").read_text()  # pylint: disable=unspecified-encoding
    json_data: dict[str, Any] = json.loads(data)
    return json_data


def _mock_station(
    mock: aiointercept, station: str, data: dict[str, Any], repeat: bool = False
) -> None:
    """Mock the parameters at a station, missing parameters are not found."""
    for parameter in SMHIObservationParameter:
        url = PARAMETER_URL.format(parameter, station)
        if str(parameter.value) in data:
            mock.get(url, payload=data[str(parameter.value)], repeat=repeat)
        else:
            mock.get(url, status=404, reason="Not Found", repeat=repeat)


async def test_api(
    mock_aiointercept: aiointercept,
    stations: dict[str, Any],
    malmo: dict[str, Any],
    snapshot: SnapshotAssertion,
) -> None:
    """Test all parameters from the nearest station."""
    mock_aiointercept.get(STATIONS_URL, payload=stations)
    _mock_station(mock_aiointercept, MALMO_A, malmo)

    async with aiohttp.ClientSession() as session:
        client = SMHIPointObservations(*MALMO, session)
        result = await client.async_get_observations(list(SMHIObservationParameter))

    assert result["station_id"] == MALMO_A
    assert result["observations"][SMHIObservationParameter.SNOW_DEPTH] is None
    assert result == snapshot


async def test_station_id(
    mock_aiointercept: aiointercept, malmo: dict[str, Any]
) -> None:
    """Test a station by id only requests the parameters."""
    _mock_station(mock_aiointercept, MALMO_A, malmo)

    async with aiohttp.ClientSession() as session:
        client = SMHIPointObservations("18.0686", "59.3293", session)
        result = await client.async_get_observations(
            [SMHIObservationParameter.TEMPERATURE, SMHIObservationParameter.HUMIDITY],
            MALMO_A,
        )

    # The station list isn't mocked, so it would fail if requested
    assert request_count(mock_aiointercept) == 2
    assert result["station_name"] == "Malmö A"
    # The position is the current position of the station from the data
    assert (result["longitude"], result["latitude"], result["height"]) == (
        13.0708,
        55.5715,
        19.757,
    )
    # The distance is from the location of the client in Stockholm
    assert result["distance"] == pytest.approx(513.5, abs=0.1)
    assert list(result["observations"]) == [
        SMHIObservationParameter.TEMPERATURE,
        SMHIObservationParameter.HUMIDITY,
    ]


@pytest.mark.parametrize("name", ["Malmö A", "malmö a", "MALMÖ A"])
async def test_station_name(
    mock_aiointercept: aiointercept,
    stations: dict[str, Any],
    malmo: dict[str, Any],
    name: str,
) -> None:
    """Test a station by name, ignoring case."""
    mock_aiointercept.get(STATIONS_URL, payload=stations)
    _mock_station(mock_aiointercept, MALMO_A, malmo)

    async with aiohttp.ClientSession() as session:
        client = SMHIPointObservations("18.0686", "59.3293", session)
        result = await client.async_get_observations(
            [SMHIObservationParameter.TEMPERATURE], name
        )

    assert result["station_id"] == MALMO_A


async def test_unknown_station_name(
    mock_aiointercept: aiointercept, stations: dict[str, Any]
) -> None:
    """Test an unknown station name."""
    mock_aiointercept.get(STATIONS_URL, payload=stations)

    async with aiohttp.ClientSession() as session:
        client = SMHIPointObservations(*MALMO, session)
        with pytest.raises(
            SmhiObservationException, match="Unknown station Not a station"
        ):
            await client.async_get_observations(
                [SMHIObservationParameter.TEMPERATURE], "Not a station"
            )


async def test_no_observations_at_station(
    mock_aiointercept: aiointercept, mock_sleep: AsyncMock
) -> None:
    """Test a station without any of the parameters, e.g. an unknown id.

    Not found is not retried, as missing data doesn't appear by retrying.
    """
    _mock_station(mock_aiointercept, "1", {})

    async with aiohttp.ClientSession() as session:
        client = SMHIPointObservations(*MALMO, session)
        with pytest.raises(
            SmhiObservationException, match="No observations at station 1"
        ):
            await client.async_get_observations(
                [
                    SMHIObservationParameter.TEMPERATURE,
                    SMHIObservationParameter.HUMIDITY,
                ],
                "1",
            )

    assert request_count(mock_aiointercept) == 2
    mock_sleep.assert_not_called()


async def test_no_station_with_observations(
    mock_aiointercept: aiointercept, stations: dict[str, Any]
) -> None:
    """Test no station with a temperature during the latest hour."""
    for station in stations["station"]:
        station["value"] = None
    mock_aiointercept.get(STATIONS_URL, payload=stations)

    async with aiohttp.ClientSession() as session:
        client = SMHIPointObservations(*MALMO, session)
        with pytest.raises(
            SmhiObservationException, match="No station with observations"
        ):
            await client.async_get_observations([SMHIObservationParameter.TEMPERATURE])


async def test_stations(
    mock_aiointercept: aiointercept, stations: dict[str, Any]
) -> None:
    """Test the stations, nearest the location first."""
    mock_aiointercept.get(STATIONS_URL, payload=stations)

    async with aiohttp.ClientSession() as session:
        client = SMHIPointObservations(*MALMO, session)
        result = await client.async_get_stations()

    assert len(result) == len(stations["station"]) == 232
    assert result[0] == {
        "station_id": MALMO_A,
        "station_name": "Malmö A",
        "longitude": 13.0708,
        "latitude": 55.5715,
        "height": 19.757,
        "distance": 5.62,
    }
    distances = [station["distance"] for station in result]
    assert distances == sorted(distances)


async def test_duplicate_parameters(
    mock_aiointercept: aiointercept, malmo: dict[str, Any]
) -> None:
    """Test a parameter given twice is requested once."""
    _mock_station(mock_aiointercept, MALMO_A, malmo)

    async with aiohttp.ClientSession() as session:
        client = SMHIPointObservations(*MALMO, session)
        result = await client.async_get_observations(
            [SMHIObservationParameter.TEMPERATURE] * 2, MALMO_A
        )

    assert request_count(mock_aiointercept) == 1
    assert list(result["observations"]) == [SMHIObservationParameter.TEMPERATURE]


async def test_api_failure(mock_aiointercept: aiointercept) -> None:
    """Test api failure for the stations and for a parameter."""
    mock_aiointercept.get(
        STATIONS_URL, status=500, reason="Internal Server Error", repeat=True
    )
    mock_aiointercept.get(
        PARAMETER_URL.format(SMHIObservationParameter.TEMPERATURE, MALMO_A),
        status=500,
        reason="Internal Server Error",
        repeat=True,
    )

    async with aiohttp.ClientSession() as session:
        client = SMHIPointObservations(*MALMO, session)
        with pytest.raises(SmhiObservationException, match="500"):
            await client.async_get_stations()
        with pytest.raises(SmhiObservationException, match="500"):
            await client.async_get_observations([SMHIObservationParameter.TEMPERATURE])
        with pytest.raises(SmhiObservationException, match="500"):
            await client.async_get_observations(
                [SMHIObservationParameter.TEMPERATURE], MALMO_A
            )


def test_latest_observation(malmo: dict[str, Any]) -> None:
    """Test the latest of the observations every minute is used."""
    values = malmo["45"]["value"]
    latest = max(values, key=lambda item: item["date"])

    result = get_observation(SMHIObservationParameter.TEMPERATURE, values[::-1])

    assert result == {
        "value": float(latest["value"]),
        "time": datetime.fromtimestamp(latest["date"] / 1000, UTC),
        "quality": SMHIObservationQuality.GREEN,
    }


@pytest.mark.parametrize(
    "values",
    [None, []],
    ids=["no_values", "empty_values"],
)
def test_no_observation(values: list[dict[str, Any]] | None) -> None:
    """Test a parameter without an observation during the latest hour."""
    assert get_observation(SMHIObservationParameter.SNOW_DEPTH, values) is None


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("123", SMHIPresentWeather.RAIN),
        ("161", SMHIPresentWeather.LIGHT_RAIN),
        ("61", SMHIPresentWeather.LIGHT_RAIN),
        ("100", SMHIPresentWeather.NO_SIGNIFICANT_WEATHER),
        ("156", SMHIPresentWeather.FREEZING_DRIZZLE),
    ],
)
def test_present_weather(code: str, expected: SMHIPresentWeather) -> None:
    """Test present weather codes are translated."""
    result = get_observation(
        SMHIObservationParameter.PRESENT_WEATHER,
        [{"date": 1792612800000, "value": code, "quality": "G"}],
    )

    assert result is not None
    assert result["value"] == float(code)
    assert result.get("weather") is expected


@pytest.mark.parametrize("code", ["509", "510", "511"])
def test_present_weather_missing(code: str) -> None:
    """Test present weather codes for no observation or a missing value."""
    assert (
        get_observation(
            SMHIObservationParameter.PRESENT_WEATHER,
            [{"date": 1792612800000, "value": code, "quality": "G"}],
        )
        is None
    )


def test_present_weather_codes() -> None:
    """Test all codes from SMHI are translated, except the missing values."""
    data = pathlib.Path("tests/observations_codes.json").read_text()  # pylint: disable=unspecified-encoding
    codes = {entry["key"] for entry in json.loads(data)["entry"]}

    assert codes - set(PRESENT_WEATHER) == {509, 510, 511}
    assert set(PRESENT_WEATHER) <= codes
    assert set(PRESENT_WEATHER.values()) == set(SMHIPresentWeather)


def test_unknown_codes(caplog: pytest.LogCaptureFixture) -> None:
    """Test unknown present weather and quality codes give None."""
    result = get_observation(
        SMHIObservationParameter.PRESENT_WEATHER,
        [{"date": 1792612800000, "value": "106", "quality": "X"}],
    )

    assert result is not None
    assert result.get("weather") is None
    assert result["quality"] is None
    assert "Unknown SMHIPresentWeather code 106" in caplog.text
    assert "Unknown SMHIObservationQuality code X" in caplog.text
