"""SMHI forecast."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
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
            "Got daily forecast with created time %s and reference time %s",
            json_data.get("createdTime"),
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
            "Got twice daily forecast with created time %s and reference time %s",
            json_data.get("createdTime"),
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
            "Got hourly forecast with created time %s and reference time %s",
            json_data.get("createdTime"),
            json_data.get("referenceTime"),
        )
        return get_hourly_forecast(json_data)


def get_daily_forecast(data: dict[str, Any]) -> list[SMHIForecast]:
    """Get daily forecast."""
    intervals = _create_forecast(data)
    sorted_forecasts = [forecast for _, forecast in intervals]

    daily_forecasts: dict[str, SMHIForecast] = {}

    dates = {forecast["valid_time"].date() for forecast in sorted_forecasts}

    # First in forecast list is current day and time
    daily_forecasts["current"] = sorted_forecasts[0]

    for date in dates:
        date_list = [
            forecast
            for forecast in sorted_forecasts
            if forecast["valid_time"].date() == date
        ]

        new_forecast = None
        forecast_temp_min = 100.0
        forecast_temp_max = -100.0

        for forecast in date_list:
            if forecast["valid_time"].hour >= 12 and new_forecast is None:
                new_forecast = forecast.copy()

            forecast_temp_min = min(forecast_temp_min, forecast["temperature"])
            forecast_temp_max = max(forecast_temp_max, forecast["temperature"])

        if new_forecast:
            start = datetime.combine(date, datetime.min.time(), tzinfo=UTC)
            new_forecast["temperature_max"] = forecast_temp_max
            new_forecast["temperature_min"] = forecast_temp_min
            _set_precipitation(
                new_forecast, intervals, start, start + timedelta(days=1)
            )
            daily_forecasts[date.isoformat()] = new_forecast

    returned_forecasts = list(daily_forecasts.values())
    returned_forecasts.sort(key=lambda x: x["valid_time"])

    return returned_forecasts


def get_twice_daily_forecast(data: dict[str, Any]) -> list[SMHIForecast]:
    """Get bi-daily forecast."""
    intervals = _create_forecast(data)
    sorted_forecasts = [forecast for _, forecast in intervals]

    twice_daily_forecasts: dict[str, SMHIForecast] = {}

    dates = {forecast["valid_time"].date() for forecast in sorted_forecasts}

    forecast_temp_max = sorted_forecasts[0]["temperature"]
    forecast_temp_min = sorted_forecasts[0]["temperature"]

    # First in forecast list is current day and time
    twice_daily_forecasts["current"] = sorted_forecasts[0]

    for date in dates:
        date_list = [
            forecast
            for forecast in sorted_forecasts
            if forecast["valid_time"].date() == date
        ]
        date_list.sort(key=lambda x: x["valid_time"])

        start = datetime.combine(date, datetime.min.time(), tzinfo=UTC)
        midday = start + timedelta(hours=12)

        first_new_forecast = None
        first_forecast_temp_min = 100.0
        first_forecast_temp_max = -100.0
        second_new_forecast = None
        second_forecast_temp_min = 100.0
        second_forecast_temp_max = -100.0

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

        # Skip half days the forecast does not cover, e.g. the last forecast
        # at 12:00 has no data for the afternoon after it. Half days start at
        # 00:00 and 12:00 also when the forecast starts within the half day,
        # so night and day can be told apart by the hour
        if first_new_forecast and _set_precipitation(
            first_new_forecast, intervals, start, midday
        ):
            first_new_forecast["valid_time"] = start
            first_new_forecast["temperature_max"] = first_forecast_temp_max
            first_new_forecast["temperature_min"] = first_forecast_temp_min
            twice_daily_forecasts[date.isoformat() + "0"] = first_new_forecast
        if second_new_forecast and _set_precipitation(
            second_new_forecast, intervals, midday, start + timedelta(days=1)
        ):
            second_new_forecast["valid_time"] = midday
            second_new_forecast["temperature_max"] = second_forecast_temp_max
            second_new_forecast["temperature_min"] = second_forecast_temp_min
            twice_daily_forecasts[date.isoformat() + "12"] = second_new_forecast

    # Current is kept first as a half day may now start before it
    current = twice_daily_forecasts.pop("current")
    returned_forecasts = list(twice_daily_forecasts.values())
    returned_forecasts.sort(key=lambda x: x["valid_time"])

    return [current, *returned_forecasts]


def get_hourly_forecast(data: dict[str, Any]) -> list[SMHIForecast]:
    """Get hourly forecast."""
    sorted_forecasts = [forecast for _, forecast in _create_forecast(data)]

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


def _set_precipitation(
    forecast: SMHIForecast,
    intervals: list[tuple[datetime, SMHIForecast]],
    start: datetime,
    end: datetime,
) -> float:
    """Set total and mean precipitation for a period on a forecast.

    Each precipitation amount from SMHI covers the interval from its start time up
    to its valid time, so an amount belongs to the period its interval starts in.
    Returns the number of hours in the period covered by the forecast.
    """
    total_precipitation = 0.0
    hours = 0.0
    for interval_start, interval in intervals:
        if start <= interval_start < end:
            total_precipitation += interval["total_precipitation"]
            hours += (interval["valid_time"] - interval_start).total_seconds() / 3600

    forecast["total_precipitation"] = round(total_precipitation, 2)
    forecast["mean_precipitation"] = (
        round(total_precipitation / hours, 2) if hours else 0.0
    )
    return hours


def _create_forecast(data: dict[str, Any]) -> list[tuple[datetime, SMHIForecast]]:
    """Convert json data to a sorted list of (interval start, forecast).

    SMHI precipitation values are amounts (mm) accumulated over the interval from
    intervalParametersStartTime to time, which is 1 hour in the near term and
    up to 12 hours further ahead. Per forecast, total_precipitation is the amount
    for the interval and min/mean/median/max are converted to mm/h.
    """

    forecasts: list[tuple[datetime, SMHIForecast]] = []

    if (
        not data.get("timeSeries")
        or not data.get("createdTime")
        or not data.get("referenceTime")
    ):
        LOGGER.debug("No time series, created time or reference time in data")
        raise SmhiForecastException(
            "No time series, created time or reference time in data"
        )

    for forecast in data["timeSeries"]:
        valid_time = datetime.strptime(forecast["time"], "%Y-%m-%dT%H:%M:%S%z")
        temp_forecast = forecast["data"]

        if interval_start_time := forecast.get("intervalParametersStartTime"):
            interval_start = datetime.strptime(
                interval_start_time, "%Y-%m-%dT%H:%M:%S%z"
            )
        else:
            interval_start = valid_time - timedelta(hours=1)
        interval_hours = max((valid_time - interval_start).total_seconds() / 3600, 1.0)

        forecast = SMHIForecast(
            temperature=float(temp_forecast["air_temperature"]),
            temperature_max=float(temp_forecast["air_temperature"]),
            temperature_min=float(temp_forecast["air_temperature"]),
            humidity=int(temp_forecast["relative_humidity"]),
            pressure=float(temp_forecast["air_pressure_at_mean_sea_level"]),
            thunder=int(temp_forecast["thunderstorm_probability"]),
            total_cloud=round(100 * temp_forecast["cloud_area_fraction"] / 8),
            low_cloud=round(100 * temp_forecast["low_type_cloud_area_fraction"] / 8),
            medium_cloud=round(
                100 * temp_forecast["medium_type_cloud_area_fraction"] / 8
            ),
            high_cloud=round(100 * temp_forecast["high_type_cloud_area_fraction"] / 8),
            precipitation_category=int(
                temp_forecast["predominant_precipitation_type_at_surface"]
            ),
            wind_direction=int(temp_forecast["wind_from_direction"]),
            wind_speed=float(temp_forecast["wind_speed"]),
            visibility=float(temp_forecast["visibility_in_air"]),
            wind_gust=float(temp_forecast["wind_speed_of_gust"]),
            min_precipitation=round(
                float(temp_forecast["precipitation_amount_min"]) / interval_hours,
                2,
            ),
            mean_precipitation=round(
                float(temp_forecast["precipitation_amount_mean"]) / interval_hours,
                2,
            ),
            median_precipitation=round(
                float(temp_forecast["precipitation_amount_median"]) / interval_hours,
                2,
            ),
            max_precipitation=round(
                float(temp_forecast["precipitation_amount_max"]) / interval_hours,
                2,
            ),
            total_precipitation=float(temp_forecast["precipitation_amount_mean"]),
            frozen_precipitation=temp_forecast["precipitation_frozen_part"]
            if temp_forecast["precipitation_frozen_part"] != -9
            else 0,
            symbol=int(temp_forecast["symbol_code"]),
            valid_time=valid_time,
        )
        forecasts.append((interval_start, forecast))

    forecasts.sort(key=lambda x: x[1]["valid_time"])
    LOGGER.debug("Returning forecasts with length: %s", len(forecasts))
    return forecasts
