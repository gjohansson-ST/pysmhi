"""Tests for SMHI forecast."""

import json
import math
import pathlib
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import patch

import aiohttp
import pytest
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion

from pysmhi import SmhiForecastException, SMHIPointForecast


@pytest.fixture(autouse=True)
async def mock_sleep() -> AsyncGenerator[None]:
    """Mock no sleeping."""
    with patch("asyncio.sleep"):
        yield


@pytest.fixture
async def mock_data() -> dict[str, Any]:
    """Mock web response."""
    data = pathlib.Path("tests/data.json").read_text()  # pylint: disable=unspecified-encoding
    json_data: dict[str, Any] = json.loads(data)
    return json_data


async def test_api(
    aresponses: ResponsesMockServer,
    mock_data: dict[str, Any],
    snapshot: SnapshotAssertion,
) -> None:
    """Test api."""
    aresponses.add(
        "opendata-download-metfcst.smhi.se",
        "/api/category/pmp3g/version/2/geotype/point/lon/16.15035/lat/58.570784/data.json",
        "GET",
        response=mock_data,
        repeat=3,
    )

    async with aiohttp.ClientSession() as session:
        forecast = SMHIPointForecast("16.15035", "58.570784", session)
        daily_forecast = await forecast.async_get_daily_forecast()
        assert len(daily_forecast) == 10
        twice_daily_forecast = await forecast.async_get_twice_daily_forecast()
        assert len(twice_daily_forecast) == 20
        hourly_forecast = await forecast.async_get_hourly_forecast()
        assert len(hourly_forecast) == 48

        assert daily_forecast == snapshot(name="daily_forecast")
        assert twice_daily_forecast == snapshot(name="twice_daily_forecast")
        assert hourly_forecast == snapshot(name="hourly_forecast")


@pytest.mark.parametrize(
    ("status", "reason", "match"),
    [
        (
            500,
            "Internal Server Error",
            "500, message='Internal Server Error', "
            "url='https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/16.15035/lat/58.570784/data.json'",
        ),
        (
            404,
            "Not found",
            "404, message='Not found', "
            "url='https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/16.15035/lat/58.570784/data.json'",
        ),
        (
            429,
            "Too Many Requests",
            "429, message='Too Many Requests', "
            "url='https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/16.15035/lat/58.570784/data.json'",
        ),
    ],
)
async def test_api_failure(
    aresponses: ResponsesMockServer, status: int, reason: str, match: str
) -> None:
    """Test api."""
    response = aresponses.Response(status=status, reason=reason)
    aresponses.add(
        "opendata-download-metfcst.smhi.se",
        "/api/category/pmp3g/version/2/geotype/point/lon/16.15035/lat/58.570784/data.json",
        "GET",
        response=response,
        repeat=math.inf,
    )

    async with aiohttp.ClientSession() as session:
        forecast = SMHIPointForecast("16.15035", "58.570784", session)
        with pytest.raises(
            SmhiForecastException,
            match=match,
        ):
            await forecast.async_get_daily_forecast()
        with pytest.raises(
            SmhiForecastException,
            match=match,
        ):
            await forecast.async_get_twice_daily_forecast()
        with pytest.raises(
            SmhiForecastException,
            match=match,
        ):
            await forecast.async_get_hourly_forecast()


async def test_malformed_data(
    aresponses: ResponsesMockServer,
    mock_data: dict[str, Any],
) -> None:
    """Test api."""
    mock_data["referenceTime"] = ""
    aresponses.add(
        "opendata-download-metfcst.smhi.se",
        "/api/category/pmp3g/version/2/geotype/point/lon/16.15035/lat/58.570784/data.json",
        "GET",
        response=mock_data,
        repeat=1,
    )

    async with aiohttp.ClientSession() as session:
        forecast = SMHIPointForecast("16.15035", "58.570784", session)
        with pytest.raises(
            SmhiForecastException,
            match="No time series, approved time or reference time in data",
        ):
            await forecast.async_get_daily_forecast()
