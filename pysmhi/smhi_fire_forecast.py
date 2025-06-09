"""SMHI forecast."""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict

from aiohttp import ClientSession

from .const import API_FIRE_FORECAST, LOGGER
from .exceptions import SMHIError, SmhiFireForecastException
from .smhi import SmhiAPI


class SMHIFireForecast(TypedDict, total=False):
    """SMHI fire forecast.

    https://opendata.smhi.se/apidocs/metfcst/parameters.html
    """

    fwiindex: int
    """Index of fire risk, FWI.

    6 Extremely high risk (FWI ≥ 28)
    5 Very high risk (FWI ≥ 22 & FWI < 28)
    4 High risk (FWI ≥ 17 & FWI < 22)
    3 Moderate risk (FWI ≥ 11 & FWI < 17)
    2 Low risk (FWI ≥ 5 & FWI < 11)
    1 Very low risk (FWI < 5)
    -1 Data missing
    """
    fwi: float
    isi: float
    bui: float  # codespell:ignore bui
    ffmc: float
    dmc: float
    dc: float
    grassfire: int
    """Index of grass fire risk.

    6 Very high Rn>25
    5 High Rn>15 & Rn≤25
    4 Moderate Rn>5 & Rn≤15
    3 Low Rn≤5
    2 Grass fire season over
    1 Snow cover
    -1 Data missing/outside season
    """
    rn: float
    forestdry: int | None
    """Index of grass fire risk.

    6 Extremely dry
    5 Very dry
    4 Dry
    3 Moderate wet
    2 Wet
    1 Very wet
    -1 Data missing
    """
    temperature: float
    wind_direction: int
    wind_speed: float
    humidity: int
    glirr: float | None
    precipitation_acc: float
    """Accumulated precipitation in mm.

    Daily: 24 hours accumulated precipitation for the period 18-18 UTC.
    Hourly: 1 hours accumulated precipitation for each hour.
    """
    valid_time: datetime


class SMHIFirePointForecast:
    """SMHI Open Data API - Fire Forecasts."""

    def __init__(
        self,
        longitude: str,
        latitude: str,
        session: ClientSession | None = None,
    ) -> None:
        """Init the SMHI fire forecast."""
        self._longitude = str(round(float(longitude), 6))
        self._latitude = str(round(float(latitude), 6))
        self._api = SmhiAPI(session)

    async def async_get_daily_forecast(self) -> list[SMHIFireForecast]:
        """Return a list of fire forecasts by day."""
        LOGGER.debug("Getting daily fire forecast")
        try:
            json_data = await self._api.async_get_data(
                API_FIRE_FORECAST.format("daily", self._longitude, self._latitude),
            )
        except SMHIError as error:
            LOGGER.debug("Error getting daily fire forecast: %s", str(error))
            raise SmhiFireForecastException from error
        LOGGER.debug(
            "Got daily fire forecast with approved time %s and reference time %s",
            json_data.get("approvedTime"),
            json_data.get("referenceTime"),
        )
        return get_fire_forecast(json_data)

    async def async_get_hourly_forecast(self) -> list[SMHIFireForecast]:
        """Return a list of fire forecasts by hour."""
        LOGGER.debug("Getting hourly fire forecast")
        try:
            json_data = await self._api.async_get_data(
                API_FIRE_FORECAST.format("hourly", self._longitude, self._latitude),
            )
        except SMHIError as error:
            LOGGER.debug("Error getting hourly fire forecast: %s", str(error))
            raise SmhiFireForecastException from error

        LOGGER.debug(
            "Got hourly fire forecast with approved time %s and reference time %s",
            json_data.get("approvedTime"),
            json_data.get("referenceTime"),
        )
        return get_fire_forecast(json_data)


def get_fire_forecast(data: dict[str, Any]) -> list[SMHIFireForecast]:
    """Get hourly forecast."""
    forecasts = _create_forecast(data)
    return sorted(forecasts, key=lambda x: x["valid_time"])


def _create_forecast(data: dict[str, Any]) -> list[SMHIFireForecast]:
    """Convert json data to a list of fire forecasts."""

    forecasts: list[SMHIFireForecast] = []

    if (
        not data.get("timeSeries")
        or not data.get("approvedTime")
        or not data.get("referenceTime")
    ):
        LOGGER.debug("No time series, approved time or reference time in data")
        raise SmhiFireForecastException(
            "No time series, approved time or reference time in data"
        )

    for forecast in data["timeSeries"]:
        valid_time = datetime.strptime(forecast["validTime"], "%Y-%m-%dT%H:%M:%S%z")
        if valid_time.date() < datetime.now().date():
            # Skip previous days
            continue

        _forecast = {
            parameter["name"]: parameter["values"][0]
            for parameter in forecast["parameters"]
        }

        forecast = SMHIFireForecast(
            fwiindex=_forecast["fwiindex"],
            fwi=_forecast["fwi"],
            isi=_forecast["isi"],
            bui=_forecast["bui"],  # codespell:ignore bui
            ffmc=_forecast["ffmc"],
            dmc=_forecast["dmc"],
            dc=_forecast["dc"],
            grassfire=_forecast["grassfire"],
            rn=_forecast["rn"],
            forestdry=_forecast.get("forestdry"),
            temperature=_forecast["t"],
            wind_direction=_forecast["wd"],
            wind_speed=_forecast["ws"],
            humidity=_forecast["r"],
            glirr=_forecast.get("GLirr"),
            precipitation_acc=_forecast.get("prec24h")
            or _forecast.get("prec1h")
            or 0.0,
            valid_time=valid_time,
        )
        forecasts.append(forecast)

    LOGGER.debug("Returning fire forecasts with length: %s", len(forecasts))
    return forecasts
