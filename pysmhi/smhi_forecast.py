"""SMHI forecast."""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict

from aiohttp import ClientSession

from .const import API_POINT_FORECAST, LOGGER
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
        LOGGER.debug("Getting daily forecast")
        try:
            json_data = await self._api.async_get_data(
                API_POINT_FORECAST.format(self._longitude, self._latitude),
            )
        except SMHIError as error:
            LOGGER.debug("Error getting daily forecast: %s", str(error))
            raise SmhiForecastException from error
        LOGGER.debug(
            "Got daily forecast with approved time %s and reference time %s",
            json_data.get("approvedTime"),
            json_data.get("referenceTime"),
        )
        return get_daily_forecast(json_data)

    async def async_get_twice_daily_forecast(self) -> list[SMHIForecast]:
        """Return a list of forecasts by day."""
        LOGGER.debug("Getting twice daily forecast")
        try:
            json_data = await self._api.async_get_data(
                API_POINT_FORECAST.format(self._longitude, self._latitude),
            )
        except SMHIError as error:
            LOGGER.debug("Error getting twice daily forecast: %s", str(error))
            raise SmhiForecastException from error

        LOGGER.debug(
            "Got twice daily forecast with approved time %s and reference time %s",
            json_data.get("approvedTime"),
            json_data.get("referenceTime"),
        )
        return get_twice_daily_forecast(json_data)

    async def async_get_hourly_forecast(self) -> list[SMHIForecast]:
        """Return a list of forecasts by hour."""
        LOGGER.debug("Getting hourly forecast")
        try:
            json_data = await self._api.async_get_data(
                API_POINT_FORECAST.format(self._longitude, self._latitude),
            )
        except SMHIError as error:
            LOGGER.debug("Error getting hourly forecast: %s", str(error))
            raise SmhiForecastException from error

        LOGGER.debug(
            "Got hourly forecast with approved time %s and reference time %s",
            json_data.get("approvedTime"),
            json_data.get("referenceTime"),
        )
        return get_hourly_forecast(json_data)


def get_daily_forecast(data: dict[str, Any]) -> list[SMHIForecast]:
    """Get daily forecast."""
    forecasts = _create_forecast(data)
    sorted_forecasts = sorted(forecasts, key=lambda x: x["valid_time"])

    daily_forecasts: dict[str, SMHIForecast] = {}

    dates = {forecast["valid_time"].date() for forecast in sorted_forecasts}

    total_precipitation = sorted_forecasts[0]["mean_precipitation"]
    forecast_temp_max = sorted_forecasts[0]["temperature"]
    forecast_temp_min = sorted_forecasts[0]["temperature"]

    # First in forecast list is current day and time
    daily_forecasts["current"] = sorted_forecasts[0]
    daily_forecasts["current"]["total_precipitation"] = total_precipitation

    for date in dates:
        date_list = [
            forecast
            for forecast in sorted_forecasts
            if forecast["valid_time"].date() == date
        ]
        date_list.sort(key=lambda x: x["valid_time"])

        new_forecast = None
        forecast_temp_min = 100.0
        forecast_temp_max = -100.0
        total_precipitation = 0.0

        for forecast in date_list:
            if (
                forecast["valid_time"].hour == 12 or forecast["valid_time"].hour > 12
            ) and new_forecast is None:
                new_forecast = forecast.copy()

            forecast_temp_min = min(forecast_temp_min, forecast["temperature"])
            forecast_temp_max = max(forecast_temp_max, forecast["temperature"])
            total_precipitation += forecast["mean_precipitation"]

        if new_forecast:
            new_forecast["temperature_max"] = forecast_temp_max
            new_forecast["temperature_min"] = forecast_temp_min
            new_forecast["total_precipitation"] = total_precipitation
            new_forecast["mean_precipitation"] = round(total_precipitation / 24, 2)
            daily_forecasts[date.isoformat()] = new_forecast

    returned_forecasts = list(daily_forecasts.values())
    returned_forecasts.sort(key=lambda x: x["valid_time"])

    return returned_forecasts


def get_twice_daily_forecast(data: dict[str, Any]) -> list[SMHIForecast]:
    """Get bi-daily forecast."""
    forecasts = _create_forecast(data)
    sorted_forecasts = sorted(forecasts, key=lambda x: x["valid_time"])

    twice_daily_forecasts: dict[str, SMHIForecast] = {}

    dates = {forecast["valid_time"].date() for forecast in sorted_forecasts}

    total_precipitation = sorted_forecasts[0]["mean_precipitation"]
    forecast_temp_max = sorted_forecasts[0]["temperature"]
    forecast_temp_min = sorted_forecasts[0]["temperature"]

    # First in forecast list is current day and time
    twice_daily_forecasts["current"] = sorted_forecasts[0]
    twice_daily_forecasts["current"]["total_precipitation"] = total_precipitation

    for date in dates:
        date_list = [
            forecast
            for forecast in sorted_forecasts
            if forecast["valid_time"].date() == date
        ]
        date_list.sort(key=lambda x: x["valid_time"])

        first_new_forecast = None
        first_forecast_temp_min = 100.0
        first_forecast_temp_max = -100.0
        first_total_precipitation = 0.0
        second_new_forecast = None
        second_forecast_temp_min = 100.0
        second_forecast_temp_max = -100.0
        second_total_precipitation = 0.0

        for forecast in date_list:
            if (
                forecast["valid_time"].hour == 0 or forecast["valid_time"].hour < 12
            ) and first_new_forecast is None:
                first_new_forecast = forecast.copy()
                first_forecast_temp_min = min(
                    forecast_temp_min, forecast["temperature"]
                )
                first_forecast_temp_max = max(
                    forecast_temp_max, forecast["temperature"]
                )
                first_total_precipitation += forecast["mean_precipitation"]

            if (
                forecast["valid_time"].hour == 12 or forecast["valid_time"].hour > 12
            ) and second_new_forecast is None:
                second_new_forecast = forecast.copy()
                second_forecast_temp_min = min(
                    forecast_temp_min, forecast["temperature"]
                )
                second_forecast_temp_max = max(
                    forecast_temp_max, forecast["temperature"]
                )
                second_total_precipitation += forecast["mean_precipitation"]

        if first_new_forecast:
            first_new_forecast["temperature_max"] = first_forecast_temp_max
            first_new_forecast["temperature_min"] = first_forecast_temp_min
            first_new_forecast["total_precipitation"] = first_total_precipitation
            first_new_forecast["mean_precipitation"] = round(
                first_total_precipitation / 12, 2
            )
            twice_daily_forecasts[date.isoformat() + "0"] = first_new_forecast
        if second_new_forecast:
            second_new_forecast["temperature_max"] = second_forecast_temp_max
            second_new_forecast["temperature_min"] = second_forecast_temp_min
            second_new_forecast["total_precipitation"] = second_total_precipitation
            second_new_forecast["mean_precipitation"] = round(
                second_total_precipitation / 12, 2
            )
            twice_daily_forecasts[date.isoformat() + "12"] = second_new_forecast

    returned_forecasts = list(twice_daily_forecasts.values())
    returned_forecasts.sort(key=lambda x: x["valid_time"])

    return returned_forecasts


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
        LOGGER.debug(
            "Breaking as time difference is not 1 hour between %s and %s",
            forecast["valid_time"],
            previous_valid_time,
        )
        break
    return hourly_forecasts


def _create_forecast(data: dict[str, Any]) -> list[SMHIForecast]:
    """Convert json data to a list of forecasts."""

    forecasts: list[SMHIForecast] = []

    previous_valid_time = None

    if (
        not data.get("timeSeries")
        or not data.get("approvedTime")
        or not data.get("referenceTime")
    ):
        LOGGER.debug("No time series, approved time or reference time in data")
        raise SmhiForecastException(
            "No time series, approved time or reference time in data"
        )

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
            min_precipitation=round(
                float(temp_forecast["pmin"]) * hours_between_forecast, 2
            ),
            mean_precipitation=round(
                float(temp_forecast["pmean"]) * hours_between_forecast, 2
            ),
            median_precipitation=round(
                float(temp_forecast["pmedian"]) / hours_between_forecast, 2
            ),
            max_precipitation=round(
                float(temp_forecast["pmax"]) * hours_between_forecast, 2
            ),
            frozen_precipitation=temp_forecast["spp"]
            if temp_forecast["spp"] != -9
            else 0,
            symbol=int(temp_forecast["Wsymb2"]),
            valid_time=valid_time,
        )
        forecasts.append(forecast)
        previous_valid_time = valid_time

    LOGGER.debug("Returning forecasts with length: %s", len(forecasts))
    return forecasts
