"""SMHI forecast."""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict

from aiohttp import ClientSession

from .const import API_POINT_FORECAST
from .exceptions import SMHIError, SmhiForecastException
from .smhi import SmhiAPI


class SMHIForecast(TypedDict, total=False):
    """SMHI weather forecast.

    https://opendata.smhi.se/apidocs/metfcst/parameters.html
    """

    temperature: float  # Celsius
    temperature_max: float  # Celsius
    temperature_min: float  # Celsius
    humidity: int  # Percent
    pressure: float  # hPa
    thunder: int  # Percent
    total_cloud: int  # Percent
    low_cloud: int  # Percent
    medium_cloud: int  # Percent
    high_cloud: int  # Percent
    precipitation_category: int
    """Precipitation
        0	No precipitation
        1	Snow
        2	Snow and rain
        3	Rain
        4	Drizzle
        5	Freezing rain
        6	Freezing drizzle
    """
    wind_direction: int  # Degrees
    wind_speed: float  # m/s
    visibility: float  # km
    wind_gust: float  # m/s
    min_precipitation: float  # mm/h
    mean_precipitation: float  # mm/h
    median_precipitation: float  # mm/h
    max_precipitation: float  # mm/h
    total_precipitation: float  # mm
    frozen_precipitation: int  # Percent (-9 = no precipitation)
    symbol: int
    """Symbol (Percent)
        1	Clear sky
        2	Nearly clear sky
        3	Variable cloudiness
        4	Halfclear sky
        5	Cloudy sky
        6	Overcast
        7	Fog
        8	Light rain showers
        9	Moderate rain showers
        10	Heavy rain showers
        11	Thunderstorm
        12	Light sleet showers
        13	Moderate sleet showers
        14	Heavy sleet showers
        15	Light snow showers
        16	Moderate snow showers
        17	Heavy snow showers
        18	Light rain
        19	Moderate rain
        20	Heavy rain
        21	Thunder
        22	Light sleet
        23	Moderate sleet
        24	Heavy sleet
        25	Light snowfall
        26	Moderate snowfall
        27	Heavy snowfall
    """
    valid_time: datetime


class SMHIPointForecast:
    """SMHI Open Data API - Meteorological Forecasts."""

    def __init__(
        self,
        longitude: str,
        latitude: str,
        session: ClientSession | None = None,
    ) -> None:
        """Init the SMHI forecast."""
        self._longitude = str(round(float(longitude), 6))
        self._latitude = str(round(float(latitude), 6))
        self._api = SmhiAPI(session)

    async def async_get_daily_forecast(self) -> list[SMHIForecast]:
        """Return a list of forecasts by day."""
        try:
            json_data = await self._api.async_get_data(
                API_POINT_FORECAST.format(self._longitude, self._latitude),
            )
        except SMHIError as error:
            raise SmhiForecastException from error
        return get_daily_forecast(json_data)

    async def async_get_hourly_forecast(self) -> list[SMHIForecast]:
        """Return a list of forecasts by hour."""
        try:
            json_data = await self._api.async_get_data(
                API_POINT_FORECAST.format(self._longitude, self._latitude),
            )
        except SMHIError as error:
            raise SmhiForecastException from error
        return get_hourly_forecast(json_data)


def get_daily_forecast(data: dict[str, Any]) -> list[SMHIForecast]:
    """Get daily forecast."""
    forecasts = _create_forecast(data)
    sorted_forecasts = sorted(forecasts, key=lambda x: x["valid_time"])

    daily_forecasts = [sorted_forecasts[0]]
    pmean: list[float] = []
    for forecast in sorted_forecasts[1:]:
        if forecast["valid_time"].hour == 12:
            new_forecast = SMHIForecast(**forecast)
            new_forecast["total_precipitation"] = sum(pmean)
            daily_forecasts.append(new_forecast)
            pmean = []
        else:
            pmean.append(forecast["mean_precipitation"])

    return daily_forecasts


def get_bidaily_forecast(data: dict[str, Any]) -> list[SMHIForecast]:
    """Get bi-daily forecast."""
    forecasts = _create_forecast(data)
    sorted_forecasts = sorted(forecasts, key=lambda x: x["valid_time"])

    daily_forecasts = [sorted_forecasts[0]]
    pmean: list[float] = []
    for forecast in sorted_forecasts[1:]:
        if forecast["valid_time"].hour in {12, 0}:
            new_forecast = SMHIForecast(**forecast)
            new_forecast["total_precipitation"] = sum(pmean)
            daily_forecasts.append(new_forecast)
            pmean = []
        else:
            pmean.append(forecast["mean_precipitation"])

    return daily_forecasts


def get_hourly_forecast(data: dict[str, Any]) -> list[SMHIForecast]:
    """Get hourly forecast."""
    forecasts = _create_forecast(data)
    sorted_forecasts = sorted(forecasts, key=lambda x: x["valid_time"])

    hourly_forecasts = [sorted_forecasts[0]]
    previous_valid_time = sorted_forecasts[0]["valid_time"]
    for forecast in sorted_forecasts[1:]:
        if (forecast["valid_time"] - previous_valid_time).total_seconds() == 3600:
            hourly_forecasts.append(forecast)
            previous_valid_time = forecast["valid_time"]
            continue
        break
    return hourly_forecasts


def _create_forecast(data: dict[str, Any]) -> list[SMHIForecast]:
    """Convert json data to a list of forecasts."""

    forecasts: list[SMHIForecast] = []

    previous_valid_time = None

    for forecast in data["timeSeries"]:
        valid_time = datetime.strptime(forecast["validTime"], "%Y-%m-%dT%H:%M:%S%z")
        temp_forecast = {
            parameter["name"]: parameter["values"][0]
            for parameter in forecast["parameters"]
        }
        if previous_valid_time:
            hours_between_forecast: int = round(
                (valid_time - previous_valid_time).total_seconds() / 3600
            )
        else:
            hours_between_forecast = 1

        forecast = SMHIForecast(
            temperature=float(temp_forecast["t"]),
            temperature_max=float(temp_forecast["t"]),
            temperature_min=float(temp_forecast["t"]),
            humidity=int(temp_forecast["r"]),
            pressure=float(temp_forecast["msl"]),
            thunder=int(temp_forecast["tstm"]),
            total_cloud=round(100 * temp_forecast["tcc_mean"] / 8),
            low_cloud=round(100 * temp_forecast["lcc_mean"] / 8),
            medium_cloud=round(100 * temp_forecast["mcc_mean"] / 8),
            high_cloud=round(100 * temp_forecast["hcc_mean"] / 8),
            precipitation_category=int(temp_forecast["pcat"]),
            wind_direction=int(temp_forecast["wd"]),
            wind_speed=float(temp_forecast["ws"]),
            visibility=float(temp_forecast["vis"]),
            wind_gust=float(temp_forecast["gust"]),
            min_precipitation=float(temp_forecast["pmin"]) / hours_between_forecast,
            mean_precipitation=float(temp_forecast["pmean"]) / hours_between_forecast,
            median_precipitation=float(temp_forecast["pmedian"])
            / hours_between_forecast,
            max_precipitation=float(temp_forecast["pmax"]) / hours_between_forecast,
            frozen_precipitation=temp_forecast["spp"]
            if temp_forecast["spp"] != -9
            else 0,
            symbol=int(temp_forecast["Wsymb2"]),
            valid_time=valid_time,
        )
        forecasts.append(forecast)
        previous_valid_time = valid_time
    return forecasts
