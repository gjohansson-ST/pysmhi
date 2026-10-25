"""SMHI observations."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import UTC, datetime
from enum import IntEnum, StrEnum
from math import asin, cos, radians, sin, sqrt
from typing import Any, NotRequired, TypedDict

from aiohttp import ClientSession

from .const import API_OBSERVATIONS, API_OBSERVATIONS_ALL_STATIONS, LOGGER
from .exceptions import SMHIError, SmhiNotFoundException, SmhiObservationException
from .smhi import SmhiAPI

EARTH_RADIUS = 6371.0  # km
# The hourly temperature, which is available for all stations at once, is used
# to find the stations
STATION_PARAMETER = 1
# Present weather codes for no observation or a missing value
PRESENT_WEATHER_MISSING = (509, 510, 511)


class SMHIObservationParameter(IntEnum):
    """SMHI observation parameters.

    https://opendata.smhi.se/metobs/resources/parameter
    """

    HUMIDITY = 6  # Percent, every hour
    PRESENT_WEATHER = 13  # Code, every hour
    TEMPERATURE = 45  # Celsius, every minute
    PRECIPITATION = 46  # mm during the minute
    WIND_SPEED = 47  # m/s, mean over 1 minute
    WIND_DIRECTION = 48  # Degrees, mean over 1 minute, 360 is north and 0 is calm
    VISIBILITY = 51  # Metres, every minute
    SNOW_DEPTH = 52  # Metres, every minute


class SMHIObservationQuality(StrEnum):
    """SMHI observation quality."""

    GREEN = "G"  # Checked and approved
    YELLOW = "Y"  # Suspect, aggregated or not checked


class SMHIPresentWeather(StrEnum):
    """SMHI present weather.

    Codes 0-99 are from manual stations and codes 100-199 from automatic
    stations, following WMO code tables 4677 and 4680.
    https://opendata-download-metobs.smhi.se/api/version/1.0/parameter/13/codes.json
    """

    NO_SIGNIFICANT_WEATHER = "no_significant_weather"
    CLOUDS_DECREASING = "clouds_decreasing"
    CLOUDS_UNCHANGED = "clouds_unchanged"
    CLOUDS_INCREASING = "clouds_increasing"
    HAZE = "haze"
    MIST = "mist"
    DUST_OR_SAND = "dust_or_sand"
    VOLCANIC_ASH = "volcanic_ash"
    FOG = "fog"
    FREEZING_FOG = "freezing_fog"
    LIGHTNING = "lightning"
    SQUALLS = "squalls"
    TORNADO = "tornado"
    PRECIPITATION_NEARBY = "precipitation_nearby"
    PRECIPITATION = "precipitation"
    HEAVY_PRECIPITATION = "heavy_precipitation"
    LIGHT_DRIZZLE = "light_drizzle"
    DRIZZLE = "drizzle"
    HEAVY_DRIZZLE = "heavy_drizzle"
    FREEZING_DRIZZLE = "freezing_drizzle"
    LIGHT_RAIN = "light_rain"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    FREEZING_RAIN = "freezing_rain"
    LIGHT_SLEET = "light_sleet"
    SLEET = "sleet"
    LIGHT_SNOW = "light_snow"
    SNOW = "snow"
    HEAVY_SNOW = "heavy_snow"
    BLOWING_SNOW = "blowing_snow"
    SNOW_GRAINS = "snow_grains"
    ICE_CRYSTALS = "ice_crystals"
    ICE_PELLETS = "ice_pellets"
    HAIL = "hail"
    LIGHT_RAIN_SHOWERS = "light_rain_showers"
    RAIN_SHOWERS = "rain_showers"
    HEAVY_RAIN_SHOWERS = "heavy_rain_showers"
    SLEET_SHOWERS = "sleet_showers"
    LIGHT_SNOW_SHOWERS = "light_snow_showers"
    SNOW_SHOWERS = "snow_showers"
    HEAVY_SNOW_SHOWERS = "heavy_snow_showers"
    THUNDERSTORM = "thunderstorm"
    HEAVY_THUNDERSTORM = "heavy_thunderstorm"
    DEW = "dew"
    FROST = "frost"


# Codes describing weather during the past hour but not at the observation, e.g.
# 21 and 123 (rain), are given as that weather
_PRESENT_WEATHER_CODES: dict[SMHIPresentWeather, tuple[int, ...]] = {
    SMHIPresentWeather.NO_SIGNIFICANT_WEATHER: (0, 100, 508),
    SMHIPresentWeather.CLOUDS_DECREASING: (1, 101),
    SMHIPresentWeather.CLOUDS_UNCHANGED: (2, 102),
    SMHIPresentWeather.CLOUDS_INCREASING: (3, 103),
    SMHIPresentWeather.HAZE: (4, 5, 104, 105, 210),
    SMHIPresentWeather.MIST: (10, 110),
    SMHIPresentWeather.DUST_OR_SAND: (
        *(6, 7, 8, 9, 30, 31, 32, 33, 34, 35),
        *(206, 208, 209, 221, 230),
    ),
    SMHIPresentWeather.VOLCANIC_ASH: (204, 220),
    SMHIPresentWeather.FOG: (
        *(11, 12, 28, 40, 41, 42, 43, 44, 45, 46, 47),
        *(120, 130, 131, 132, 133, 134),
        *(241, 242, 243, 244, 245, 246, 247, 248, 249),
    ),
    SMHIPresentWeather.FREEZING_FOG: (48, 49, 135),
    SMHIPresentWeather.LIGHTNING: (13, 112, 213),
    SMHIPresentWeather.SQUALLS: (18, 118, 207),
    SMHIPresentWeather.TORNADO: (19, 199, 219),
    SMHIPresentWeather.PRECIPITATION_NEARBY: (14, 15, 16, 292, 293),
    SMHIPresentWeather.PRECIPITATION: (121, 140, 141),
    SMHIPresentWeather.HEAVY_PRECIPITATION: (142,),
    SMHIPresentWeather.LIGHT_DRIZZLE: (50, 51, 151, 250, 251, 252),
    SMHIPresentWeather.DRIZZLE: (20, 52, 53, 122, 150, 152, 253, 254),
    SMHIPresentWeather.HEAVY_DRIZZLE: (54, 55, 153, 255, 256, 257),
    # 156 is heavy freezing drizzle in WMO code table 4680
    SMHIPresentWeather.FREEZING_DRIZZLE: (56, 57, 154, 155, 156),
    SMHIPresentWeather.LIGHT_RAIN: (58, 60, 61, 157, 161, 260, 261),
    SMHIPresentWeather.RAIN: (
        *(21, 59, 62, 63, 123, 143, 158, 160, 162),
        *(262, 263, 280),
    ),
    SMHIPresentWeather.HEAVY_RAIN: (64, 65, 144, 163, 264, 265, 266, 267),
    SMHIPresentWeather.FREEZING_RAIN: (
        *(24, 66, 67, 125, 147, 148, 164, 165, 166),
        *(227, 281),
    ),
    SMHIPresentWeather.LIGHT_SLEET: (68, 167),
    SMHIPresentWeather.SLEET: (23, 69, 168, 259, 279, 282),
    SMHIPresentWeather.LIGHT_SNOW: (70, 71, 171, 270, 271),
    SMHIPresentWeather.SNOW: (
        *(22, 72, 73, 124, 145, 170, 172),
        *(223, 272, 273, 283),
    ),
    SMHIPresentWeather.HEAVY_SNOW: (74, 75, 146, 173, 274, 275, 276, 277),
    SMHIPresentWeather.BLOWING_SNOW: (36, 37, 38, 39, 127, 128, 129, 211, 239),
    SMHIPresentWeather.SNOW_GRAINS: (77, 177),
    SMHIPresentWeather.ICE_CRYSTALS: (76, 78, 111, 178, 278),
    SMHIPresentWeather.ICE_PELLETS: (79, 174, 175, 176),
    SMHIPresentWeather.HAIL: (
        *(27, 87, 88, 89, 90, 189),
        *(284, 285, 286, 287, 288, 289, 290, 291),
    ),
    SMHIPresentWeather.LIGHT_RAIN_SHOWERS: (80, 181),
    SMHIPresentWeather.RAIN_SHOWERS: (25, 81, 180, 182),
    SMHIPresentWeather.HEAVY_RAIN_SHOWERS: (82, 183, 184),
    SMHIPresentWeather.SLEET_SHOWERS: (83, 84),
    SMHIPresentWeather.LIGHT_SNOW_SHOWERS: (85, 185),
    SMHIPresentWeather.SNOW_SHOWERS: (26, 86, 186),
    SMHIPresentWeather.HEAVY_SNOW_SHOWERS: (187,),
    SMHIPresentWeather.THUNDERSTORM: (
        *(17, 29, 91, 92, 93, 94, 95, 96),
        *(126, 190, 191, 192, 193, 217),
    ),
    SMHIPresentWeather.HEAVY_THUNDERSTORM: (97, 98, 99, 194, 195, 196),
    SMHIPresentWeather.DEW: (222,),
    SMHIPresentWeather.FROST: (224, 225, 226, 228),
}
PRESENT_WEATHER = {
    code: weather for weather, codes in _PRESENT_WEATHER_CODES.items() for code in codes
}


class SMHIObservation(TypedDict):
    """SMHI observation of a parameter."""

    value: float
    time: datetime  # UTC
    quality: SMHIObservationQuality | None  # None if unknown
    # Only for present weather, None if the code is unknown
    weather: NotRequired[SMHIPresentWeather | None]


class SMHIStation(TypedDict):
    """SMHI weather station."""

    station_id: str
    station_name: str
    longitude: float
    latitude: float
    height: float  # Metres above sea level
    distance: float  # km from the location


class SMHIStationObservations(SMHIStation):
    """SMHI observations at a station.

    https://opendata.smhi.se/metobs/introduction
    """

    # None if the station doesn't observe the parameter or there is no value
    observations: dict[SMHIObservationParameter, SMHIObservation | None]


class SMHIPointObservations:
    """SMHI Open Data API - Meteorological observations."""

    def __init__(
        self,
        longitude: str,
        latitude: str,
        session: ClientSession | None = None,
    ) -> None:
        """Init the SMHI observations."""
        self._longitude = str(round(float(longitude), 6))
        self._latitude = str(round(float(latitude), 6))
        self._api = SmhiAPI(session)

    async def async_get_stations(self) -> list[SMHIStation]:
        """Return the stations observing temperature, nearest the location first.

        The id or name of a station can be used to get its observations.
        """
        LOGGER.debug("Getting stations")
        json_data = await self._async_get_all_stations()
        return get_stations(json_data, float(self._longitude), float(self._latitude))

    async def async_get_observations(
        self,
        parameters: Iterable[SMHIObservationParameter],
        station: str | None = None,
    ) -> SMHIStationObservations:
        """Return the observations of parameters during the latest hour at a station.

        The station is given by id or name, see async_get_stations. Without a
        station, the station with a temperature during the latest hour nearest
        the location is used. Parameters without an observation, e.g. as the
        station doesn't observe them, are None.
        """
        LOGGER.debug("Getting observations")
        if station is None or not station.isdigit():
            json_data = await self._async_get_all_stations()
            station = get_station(
                json_data, float(self._longitude), float(self._latitude), station
            )["station_id"]

        # One request per parameter, as the API only serves one parameter at a time
        requested = list(dict.fromkeys(parameters))
        responses = await asyncio.gather(
            *(self._async_get_parameter(parameter, station) for parameter in requested)
        )
        data = dict(zip(requested, responses, strict=True))
        # The name and position of the station are only in the data of a parameter
        if not (station_data := next((item for item in responses if item), None)):
            raise SmhiObservationException(f"No observations at station {station}")

        result = SMHIStationObservations(
            **_station_from_data(
                station_data, float(self._longitude), float(self._latitude)
            ),
            observations={
                parameter: get_observation(parameter, response["value"])
                if response
                else None
                for parameter, response in data.items()
            },
        )
        LOGGER.debug(
            "Got %d of %d observations from %s",
            sum(1 for item in result["observations"].values() if item),
            len(result["observations"]),
            result["station_name"],
        )
        return result

    async def _async_get_all_stations(self) -> dict[str, Any]:
        """Return the temperature during the latest hour for all stations."""
        try:
            return await self._api.async_get_data(
                API_OBSERVATIONS_ALL_STATIONS.format(STATION_PARAMETER)
            )
        except SMHIError as error:
            LOGGER.debug("Error getting observations: %s", str(error))
            raise SmhiObservationException from error

    async def _async_get_parameter(
        self, parameter: SMHIObservationParameter, station_id: str
    ) -> dict[str, Any] | None:
        """Return a parameter during the latest hour at a station.

        Returns None if the station doesn't observe the parameter.
        """
        try:
            return await self._api.async_get_data(
                API_OBSERVATIONS.format(parameter, station_id)
            )
        except SmhiNotFoundException:
            LOGGER.debug("No %s at station %s", parameter.name, station_id)
            return None
        except SMHIError as error:
            LOGGER.debug("Error getting observations: %s", str(error))
            raise SmhiObservationException from error


def get_stations(
    data: dict[str, Any], longitude: float, latitude: float
) -> list[SMHIStation]:
    """Get the stations from the data for all stations, nearest the location first."""
    stations = [_station(station, longitude, latitude) for station in data["station"]]
    stations.sort(key=lambda station: station["distance"])
    return stations


def get_station(
    data: dict[str, Any],
    longitude: float,
    latitude: float,
    station: str | None = None,
) -> SMHIStation:
    """Get a station from the data for all stations.

    The station is given by id or name. Without a station, the station with an
    observation nearest the location is used.
    """
    if station is None:
        if not (stations := [item for item in data["station"] if item.get("value")]):
            raise SmhiObservationException("No station with observations")
        selected = min(
            stations,
            key=lambda item: _distance(
                longitude, latitude, item["longitude"], item["latitude"]
            ),
        )
    else:
        selected = next(
            (
                item
                for item in data["station"]
                if station == item["key"]
                or station.casefold() == item["name"].casefold()
            ),
            None,
        )
        if selected is None:
            raise SmhiObservationException(f"Unknown station {station}")
    return _station(selected, longitude, latitude)


def _station_from_data(
    data: dict[str, Any], longitude: float, latitude: float
) -> SMHIStation:
    """Convert the station from the data of a parameter at a station.

    The current position is the latest of the positions of the station, and its
    height above sea level replaces the height of the station.
    """
    position = max(data["position"], key=lambda item: item["to"])
    return _station({**data["station"], **position}, longitude, latitude)


def _station(station: dict[str, Any], longitude: float, latitude: float) -> SMHIStation:
    """Convert a station from json data."""
    return SMHIStation(
        station_id=station["key"],
        station_name=station["name"],
        longitude=station["longitude"],
        latitude=station["latitude"],
        height=station["height"],
        distance=round(
            _distance(longitude, latitude, station["longitude"], station["latitude"]),
            2,
        ),
    )


def get_observation(
    parameter: SMHIObservationParameter, values: list[dict[str, Any]] | None
) -> SMHIObservation | None:
    """Get the latest observation from the values of a period."""
    if not values:
        return None
    latest = max(values, key=lambda item: item["date"])
    value = float(latest["value"])
    if (
        parameter == SMHIObservationParameter.PRESENT_WEATHER
        and value in PRESENT_WEATHER_MISSING
    ):
        LOGGER.debug("Present weather is missing")
        return None
    observation = SMHIObservation(
        value=value,
        time=datetime.fromtimestamp(latest["date"] / 1000, UTC),
        quality=_quality(latest["quality"]),
    )
    if parameter == SMHIObservationParameter.PRESENT_WEATHER:
        observation["weather"] = _present_weather(int(value))
    return observation


def _present_weather(code: int) -> SMHIPresentWeather | None:
    """Return the present weather for a code, or None if the code is unknown."""
    if (weather := PRESENT_WEATHER.get(code)) is None:
        LOGGER.warning("Unknown SMHIPresentWeather code %s", code)
    return weather


def _quality(code: str) -> SMHIObservationQuality | None:
    """Return the quality for a code, or None if the code is unknown."""
    try:
        return SMHIObservationQuality(code)
    except ValueError:
        LOGGER.warning("Unknown SMHIObservationQuality code %s", code)
        return None


def _distance(
    longitude: float, latitude: float, other_longitude: float, other_latitude: float
) -> float:
    """Return the great-circle distance in km between two locations."""
    delta_latitude = radians(other_latitude - latitude)
    delta_longitude = radians(other_longitude - longitude)
    haversine = (
        sin(delta_latitude / 2) ** 2
        + cos(radians(latitude))
        * cos(radians(other_latitude))
        * sin(delta_longitude / 2) ** 2
    )
    return 2 * EARTH_RADIUS * asin(sqrt(haversine))
