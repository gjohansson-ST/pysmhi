"""Tests for SMHI fire forecast."""

import json
import pathlib
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

import aiohttp
import pytest
from aiointercept import aiointercept
from freezegun import freeze_time
from syrupy.assertion import SnapshotAssertion

from pysmhi import SmhiFireForecastException, SMHIFirePointForecast

from .conftest import request_count


@pytest.fixture(autouse=True)
async def mock_sleep() -> AsyncGenerator[None]:
    """Mock no sleeping."""
    with patch("asyncio.sleep"):
        yield


@pytest.fixture(name="mock_data")
async def get_mock_data() -> tuple[dict[str, Any], dict[str, Any]]:
    """Mock web response."""
    data = pathlib.Path("tests/fire_data_daily.json").read_text()  # pylint: disable=unspecified-encoding
    json_data: dict[str, Any] = json.loads(data)
    data2 = pathlib.Path("tests/fire_data_hourly.json").read_text()  # pylint: disable=unspecified-encoding
    json_data2: dict[str, Any] = json.loads(data2)
    return (json_data, json_data2)


@freeze_time("2025-06-09T12:00:00+02:00")
async def test_api(
    mock_aiointercept: aiointercept,
    mock_data: tuple[dict[str, Any], dict[str, Any]],
    snapshot: SnapshotAssertion,
) -> None:
    """Test api."""
    mock_aiointercept.get(
        "https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/daily/geotype/point/lon/16.15035/lat/58.570784/data.json",
        payload=mock_data[0],
    )
    mock_aiointercept.get(
        "https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/hourly/geotype/point/lon/16.15035/lat/58.570784/data.json",
        payload=mock_data[1],
    )

    async with aiohttp.ClientSession() as session:
        forecast = SMHIFirePointForecast("16.15035", "58.570784", session)
        daily_forecast = await forecast.async_get_daily_forecast()
        assert len(daily_forecast) == 5
        hourly_forecast = await forecast.async_get_hourly_forecast()
        assert len(hourly_forecast) == 41

        assert daily_forecast == snapshot(name="daily_forecast")
        assert hourly_forecast == snapshot(name="hourly_forecast")


async def test_ratelimiting(
    mock_aiointercept: aiointercept,
    mock_data: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    """Test api."""
    mock_aiointercept.get(
        "https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/daily/geotype/point/lon/16.15035/lat/58.570784/data.json",
        payload=mock_data[0],
        repeat=True,
    )
    mock_aiointercept.get(
        "https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/daily/geotype/point/lon/17.15035/lat/58.570784/data.json",
        payload=mock_data[0],
        repeat=True,
    )
    initial_datetime = datetime(2025, 1, 20, 18, 29, 54, tzinfo=UTC)
    with freeze_time(initial_datetime) as frozen_datetime:
        async with aiohttp.ClientSession() as session:
            forecast = SMHIFirePointForecast("16.15035", "58.570784", session)
            await forecast.async_get_daily_forecast()
            assert request_count(mock_aiointercept) == 1

            forecast2 = SMHIFirePointForecast("17.15035", "58.570784", session)
            await forecast2.async_get_daily_forecast()
            assert request_count(mock_aiointercept) == 2

            initial_rate_limit = forecast._api.rate_limit.copy()  # noqa: SLF001

            # New call within 60 seconds should not make a new request
            frozen_datetime.tick(timedelta(seconds=5))
            await forecast.async_get_daily_forecast()
            await forecast2.async_get_daily_forecast()
            assert request_count(mock_aiointercept) == 2

            assert forecast._api.rate_limit == initial_rate_limit  # noqa:SLF001

            # New call after 60 seconds should make a new request
            frozen_datetime.tick(timedelta(seconds=60))
            await forecast.async_get_daily_forecast()
            assert request_count(mock_aiointercept) == 3


@pytest.mark.parametrize(
    ("status", "reason", "match", "match_hourly"),
    [
        (
            500,
            "Internal Server Error",
            (
                "500, message='Internal Server Error', "
                "url='https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/daily/geotype/point/lon/16.15035/lat/58.570784/data.json'"
            ),
            "url='https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/hourly/geotype/point/lon/16.15035/lat/58.570784/data.json'",
        ),
        (
            404,
            "Not found",
            (
                "404, message='Not found', "
                "url='https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/daily/geotype/point/lon/16.15035/lat/58.570784/data.json'"
            ),
            "url='https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/hourly/geotype/point/lon/16.15035/lat/58.570784/data.json'",
        ),
        (
            429,
            "Too Many Requests",
            (
                "429, message='Too Many Requests', "
                "url='https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/daily/geotype/point/lon/16.15035/lat/58.570784/data.json'"
            ),
            "url='https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/hourly/geotype/point/lon/16.15035/lat/58.570784/data.json'",
        ),
    ],
)
async def test_api_failure(
    mock_aiointercept: aiointercept,
    status: int,
    reason: str,
    match: str,
    match_hourly: str,
) -> None:
    """Test api."""
    mock_aiointercept.get(
        "https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/daily/geotype/point/lon/16.15035/lat/58.570784/data.json",
        status=status,
        reason=reason,
        repeat=True,
    )
    mock_aiointercept.get(
        "https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/hourly/geotype/point/lon/16.15035/lat/58.570784/data.json",
        status=status,
        reason=reason,
        repeat=True,
    )

    async with aiohttp.ClientSession() as session:
        forecast = SMHIFirePointForecast("16.15035", "58.570784", session)
        with pytest.raises(
            SmhiFireForecastException,
            match=match,
        ):
            await forecast.async_get_daily_forecast()
        with pytest.raises(
            SmhiFireForecastException,
            match=match_hourly,
        ):
            await forecast.async_get_hourly_forecast()


async def test_malformed_data(
    mock_aiointercept: aiointercept,
    mock_data: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    """Test api."""
    mock_data[0]["referenceTime"] = ""
    mock_aiointercept.get(
        "https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/daily/geotype/point/lon/16.15035/lat/58.570784/data.json",
        payload=mock_data[0],
    )

    async with aiohttp.ClientSession() as session:
        forecast = SMHIFirePointForecast("16.15035", "58.570784", session)
        with pytest.raises(
            SmhiFireForecastException,
            match="No time series, approved time or reference time in data",
        ):
            await forecast.async_get_daily_forecast()


async def test_six_digits_rounding(
    mock_aiointercept: aiointercept,
    mock_data: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    """Test api."""
    mock_aiointercept.get(
        "https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/daily/geotype/point/lon/16.123457/lat/58.123457/data.json",
        payload=mock_data[0],
        repeat=True,
    )

    async with aiohttp.ClientSession() as session:
        forecast = SMHIFirePointForecast("16.1234567", "58.1234567", session)
        assert forecast._latitude == "58.123457"  # noqa: SLF001
        assert forecast._longitude == "16.123457"  # noqa: SLF001
        await forecast.async_get_daily_forecast()
        assert request_count(mock_aiointercept) == 1
