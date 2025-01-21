"""Tests for SMHI forecast."""

import json
import pathlib
from typing import Any

import aiohttp
import pytest
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion

from pysmhi.smhi_forecast import SMHIPointForecast


@pytest.fixture
async def mock_data() -> dict[str, Any]:
    """Mock web response."""
    data = pathlib.Path("tests/data.json").read_text()  # pylint: disable=unspecified-encoding
    json_data: dict[str, Any] = json.loads(data)
    return json_data


@pytest.mark.asyncio
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
