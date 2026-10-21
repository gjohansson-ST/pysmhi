"""Tests for SMHI forecast."""

import json
import math
import pathlib
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

import aiohttp
import pytest
from aresponses import ResponsesMockServer
from freezegun import freeze_time
from syrupy.assertion import SnapshotAssertion

from pysmhi import SmhiForecastException, SMHIPointForecast


@pytest.fixture(autouse=True)
async def mock_sleep() -> AsyncGenerator[None]:
    """Mock no sleeping."""
    with patch("asyncio.sleep"):
        yield


@pytest.fixture(name="mock_data")
async def get_mock_data() -> dict[str, Any]:
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
        "/api/category/snow1g/version/1/geotype/point/lon/16.15035/lat/58.570784/data.json",
        "GET",
        response=mock_data,
        repeat=3,
    )

    async with aiohttp.ClientSession() as session:
        forecast = SMHIPointForecast("16.15035", "58.570784", session)
        daily_forecast = await forecast.async_get_daily_forecast()
        assert len(daily_forecast) == 12
        twice_daily_forecast = await forecast.async_get_twice_daily_forecast()
        assert len(twice_daily_forecast) == 22
        hourly_forecast = await forecast.async_get_hourly_forecast()
        assert len(hourly_forecast) == 60

        assert daily_forecast == snapshot(name="daily_forecast")
        assert twice_daily_forecast == snapshot(name="twice_daily_forecast")
        assert hourly_forecast == snapshot(name="hourly_forecast")


async def test_ratelimiting(
    aresponses: ResponsesMockServer,
    mock_data: dict[str, Any],
) -> None:
    """Test api."""
    aresponses.add(
        "opendata-download-metfcst.smhi.se",
        "/api/category/snow1g/version/1/geotype/point/lon/16.15035/lat/58.570784/data.json",
        "GET",
        response=mock_data,
        repeat=math.inf,
    )
    aresponses.add(
        "opendata-download-metfcst.smhi.se",
        "/api/category/snow1g/version/1/geotype/point/lon/17.15035/lat/58.570784/data.json",
        "GET",
        response=mock_data,
        repeat=math.inf,
    )
    initial_datetime = datetime(2025, 1, 20, 18, 29, 54, tzinfo=UTC)
    with freeze_time(initial_datetime) as frozen_datetime:
        async with aiohttp.ClientSession() as session:
            forecast = SMHIPointForecast("16.15035", "58.570784", session)
            await forecast.async_get_daily_forecast()
            assert len(aresponses.history) == 1

            forecast2 = SMHIPointForecast("17.15035", "58.570784", session)
            await forecast2.async_get_daily_forecast()
            assert len(aresponses.history) == 2

            initial_rate_limit = forecast._api.rate_limit.copy()  # noqa: SLF001

            # New call within 60 seconds should not make a new request
            frozen_datetime.tick(timedelta(seconds=5))
            await forecast.async_get_daily_forecast()
            await forecast2.async_get_daily_forecast()
            assert len(aresponses.history) == 2

            assert forecast._api.rate_limit == initial_rate_limit  # noqa:SLF001

            # New call after 60 seconds should make a new request
            frozen_datetime.tick(timedelta(seconds=60))
            await forecast.async_get_daily_forecast()
            assert len(aresponses.history) == 3


@pytest.mark.parametrize(
    ("status", "reason", "match"),
    [
        (
            500,
            "Internal Server Error",
            (
                "500, message='Internal Server Error', "
                "url='https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/point/lon/16.15035/lat/58.570784/data.json'"
            ),
        ),
        (
            404,
            "Not found",
            (
                "404, message='Not found', "
                "url='https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/point/lon/16.15035/lat/58.570784/data.json'"
            ),
        ),
        (
            429,
            "Too Many Requests",
            (
                "429, message='Too Many Requests', "
                "url='https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/point/lon/16.15035/lat/58.570784/data.json'"
            ),
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
        "/api/category/snow1g/version/1/geotype/point/lon/16.15035/lat/58.570784/data.json",
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
        "/api/category/snow1g/version/1/geotype/point/lon/16.15035/lat/58.570784/data.json",
        "GET",
        response=mock_data,
        repeat=1,
    )

    async with aiohttp.ClientSession() as session:
        forecast = SMHIPointForecast("16.15035", "58.570784", session)
        with pytest.raises(
            SmhiForecastException,
            match="No time series, created time or reference time in data",
        ):
            await forecast.async_get_daily_forecast()


async def test_six_digits_rounding(
    aresponses: ResponsesMockServer,
    mock_data: dict[str, Any],
) -> None:
    """Test api."""
    aresponses.add(
        "opendata-download-metfcst.smhi.se",
        "/api/category/snow1g/version/1/geotype/point/lon/16.123457/lat/58.123457/data.json",
        "GET",
        response=mock_data,
        repeat=math.inf,
    )

    async with aiohttp.ClientSession() as session:
        forecast = SMHIPointForecast("16.1234567", "58.1234567", session)
        assert forecast._latitude == "58.123457"  # noqa: SLF001
        assert forecast._longitude == "16.123457"  # noqa: SLF001
        await forecast.async_get_daily_forecast()
        assert len(aresponses.history) == 1


def _expected_precipitation(
    mock_data: dict[str, Any], hours_per_period: int
) -> dict[datetime, float]:
    """Sum precipitation amounts per period by the start of their interval."""
    expected: dict[datetime, float] = {}
    for forecast in mock_data["timeSeries"]:
        start = datetime.strptime(
            forecast["intervalParametersStartTime"], "%Y-%m-%dT%H:%M:%S%z"
        )
        period = start.replace(
            hour=start.hour - start.hour % hours_per_period, minute=0, second=0
        )
        expected[period] = (
            expected.get(period, 0) + forecast["data"]["precipitation_amount_mean"]
        )
    return expected


async def test_total_precipitation_daily(
    aresponses: ResponsesMockServer,
    mock_data: dict[str, Any],
) -> None:
    """Test daily total precipitation sums the amounts for each day."""
    aresponses.add(
        "opendata-download-metfcst.smhi.se",
        "/api/category/snow1g/version/1/geotype/point/lon/16.123457/lat/58.123457/data.json",
        "GET",
        response=mock_data,
        repeat=math.inf,
    )
    expected = _expected_precipitation(mock_data, 24)

    async with aiohttp.ClientSession() as session:
        forecast = SMHIPointForecast("16.123457", "58.123457", session)
        result = await forecast.async_get_daily_forecast()

    # First forecast is the current one
    assert result[0]["total_precipitation"] == 0.0
    for result_forecast in result[1:]:
        period = result_forecast["valid_time"].replace(hour=0)
        assert result_forecast["total_precipitation"] == round(expected[period], 2)

    totals = {
        f["valid_time"].date().isoformat(): f["total_precipitation"] for f in result[1:]
    }
    assert totals == {
        "2026-04-02": 1.1,
        "2026-04-03": 3.5,
        "2026-04-04": 3.0,
        "2026-04-05": 3.1,
        "2026-04-06": 0.6,
        "2026-04-07": 0.0,
        "2026-04-08": 0.0,
        "2026-04-09": 0.7,
        "2026-04-10": 0.6,
        "2026-04-11": 1.5,
        "2026-04-12": 0.6,
    }


async def test_total_precipitation_with_different_date(
    aresponses: ResponsesMockServer,
    mock_data: dict[str, Any],
) -> None:
    """Test api."""
    aresponses.add(
        "opendata-download-metfcst.smhi.se",
        "/api/category/snow1g/version/1/geotype/point/lon/16.123457/lat/58.123457/data.json",
        "GET",
        response=mock_data,
        repeat=math.inf,
    )

    forecasts = mock_data["timeSeries"]
    all_precipitation = {}
    for forecast in forecasts:
        start = datetime.strptime(
            forecast["intervalParametersStartTime"], "%Y-%m-%dT%H:%M:%S%z"
        )
        _prec = forecast["data"]["precipitation_amount_mean"]
        all_precipitation[start] = _prec

    get_dates = {_date.date(): 0 for _date in all_precipitation}

    for _date in get_dates:
        for forecast_date, precipitation in all_precipitation.items():
            if forecast_date.date() == _date:
                get_dates[_date] += precipitation

    async with aiohttp.ClientSession() as session:
        forecast = SMHIPointForecast("16.123457", "58.123457", session)
        result = await forecast.async_get_daily_forecast()
        for result_forecast in result[1:]:
            calculated = get_dates.get(result_forecast["valid_time"].date(), 0)

            assert round(result_forecast["total_precipitation"], 2) == round(
                calculated, 2
            )


async def test_total_precipitation_twice_daily(
    aresponses: ResponsesMockServer,
    mock_data: dict[str, Any],
) -> None:
    """Test twice daily total precipitation sums the amounts for each half day."""
    aresponses.add(
        "opendata-download-metfcst.smhi.se",
        "/api/category/snow1g/version/1/geotype/point/lon/16.123457/lat/58.123457/data.json",
        "GET",
        response=mock_data,
        repeat=math.inf,
    )
    expected = _expected_precipitation(mock_data, 12)

    async with aiohttp.ClientSession() as session:
        forecast = SMHIPointForecast("16.123457", "58.123457", session)
        result = await forecast.async_get_twice_daily_forecast()

    for result_forecast in result[1:]:
        valid_time = result_forecast["valid_time"]
        period = valid_time.replace(hour=valid_time.hour - valid_time.hour % 12)
        assert result_forecast["total_precipitation"] == round(expected[period], 2)

    # The last forecast at 12:00 has no data for the afternoon after it
    assert result[-1]["valid_time"] == datetime(2026, 4, 12, 0, tzinfo=UTC)


async def test_hourly_precipitation(
    aresponses: ResponsesMockServer,
    mock_data: dict[str, Any],
) -> None:
    """Test hourly precipitation is the amount for each hour."""
    aresponses.add(
        "opendata-download-metfcst.smhi.se",
        "/api/category/snow1g/version/1/geotype/point/lon/16.123457/lat/58.123457/data.json",
        "GET",
        response=mock_data,
        repeat=math.inf,
    )

    async with aiohttp.ClientSession() as session:
        forecast = SMHIPointForecast("16.123457", "58.123457", session)
        result = await forecast.async_get_hourly_forecast()

    for result_forecast, data in zip(result, mock_data["timeSeries"], strict=False):
        amount = data["data"]["precipitation_amount_mean"]
        assert result_forecast["mean_precipitation"] == amount
        assert result_forecast["total_precipitation"] == amount


async def test_twice_daily_starts_at_half_day(
    aresponses: ResponsesMockServer,
    mock_data: dict[str, Any],
) -> None:
    """Test twice daily forecasts start at 00:00 and 12:00.

    The forecast starts at 13:00 so the first afternoon is only partly covered.
    """
    mock_data["timeSeries"] = [
        forecast
        for forecast in mock_data["timeSeries"]
        if forecast["time"] >= "2026-04-02T13:00:00Z"
    ]
    aresponses.add(
        "opendata-download-metfcst.smhi.se",
        "/api/category/snow1g/version/1/geotype/point/lon/16.123457/lat/58.123457/data.json",
        "GET",
        response=mock_data,
        repeat=math.inf,
    )

    async with aiohttp.ClientSession() as session:
        forecast = SMHIPointForecast("16.123457", "58.123457", session)
        result = await forecast.async_get_twice_daily_forecast()

    assert result[0]["valid_time"] == datetime(2026, 4, 2, 13, tzinfo=UTC)
    assert result[1]["valid_time"] == datetime(2026, 4, 2, 12, tzinfo=UTC)
    assert result[2]["valid_time"] == datetime(2026, 4, 3, 0, tzinfo=UTC)
    for result_forecast in result[1:]:
        assert result_forecast["valid_time"].hour in (0, 12)
        assert result_forecast["valid_time"].minute == 0
