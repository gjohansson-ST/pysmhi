"""SMHI fire detections."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import IntEnum
from math import asin, cos, radians, sin, sqrt
from typing import Any, TypedDict, TypeVar
from zoneinfo import ZoneInfo

from aiohttp import ClientSession

from .const import API_FIRE_DETECTIONS, LOGGER
from .exceptions import SMHIError, SmhiFireDetectionException
from .smhi import SmhiAPI

SWEDISH_TIME = ZoneInfo("Europe/Stockholm")
EARTH_RADIUS = 6371.0  # km

_EnumT = TypeVar("_EnumT", bound=IntEnum)


class SMHIFireDetectionConfidence(IntEnum):
    """SMHI fire detection confidence."""

    LOW = 7
    NOMINAL = 8
    HIGH = 9


class SMHIFireDetectionAnomaly(IntEnum):
    """SMHI fire detection persistent anomaly at the location."""

    NONE = 0
    GAS_FLARE = 1
    VOLCANO = 2
    SOLAR_PANEL = 3
    URBAN = 4
    UNCLASSIFIED = 5


class SMHIFireDetection(TypedDict):
    """SMHI fire detection.

    https://opendata.smhi.se/satellite/firedetections/data
    """

    id: str
    observation_time: datetime
    longitude: float
    latitude: float
    distance: float  # km from the location
    power: float  # Fire Radiative Power
    brightness_temperature: float  # Kelvin
    brightness_temperature_celsius: float  # Celsius
    confidence: SMHIFireDetectionConfidence | None  # None if unknown
    anomaly: SMHIFireDetectionAnomaly | None  # None if unknown
    platform_name: str  # Satellite detecting the fire


class SMHIFireDetections:
    """SMHI Open Data API - Satellite fire detections.

    https://opendata.smhi.se/satellite/firedetections/introduction
    """

    def __init__(
        self,
        longitude: str,
        latitude: str,
        session: ClientSession | None = None,
    ) -> None:
        """Init the SMHI fire detections."""
        self._longitude = str(round(float(longitude), 6))
        self._latitude = str(round(float(latitude), 6))
        self._api = SmhiAPI(session)

    async def async_get_fire_detections(
        self, radius: float = 50.0, days: int = 7
    ) -> list[SMHIFireDetection]:
        """Return the fire detections near the location, newest first.

        Only detections within radius km from the location during the last
        days are included.
        """
        LOGGER.debug("Getting fire detections")
        since = datetime.now(SWEDISH_TIME) - timedelta(days=days)
        features: list[dict[str, Any]] = []
        # Detections are published per month in Swedish time
        for year, month in _months(since, datetime.now(SWEDISH_TIME)):
            try:
                json_data: dict[str, Any] = await self._api.async_get_data(
                    API_FIRE_DETECTIONS.format(year, month),
                )
            except SMHIError as error:
                LOGGER.debug("Error getting fire detections: %s", str(error))
                raise SmhiFireDetectionException from error
            features.extend(json_data["features"])
        LOGGER.debug("Got %d fire detections", len(features))

        return get_fire_detections(
            features,
            float(self._longitude),
            float(self._latitude),
            radius,
            since,
        )


def get_fire_detections(
    features: list[dict[str, Any]],
    longitude: float,
    latitude: float,
    radius: float = 50.0,
    since: datetime | None = None,
) -> list[SMHIFireDetection]:
    """Get the fire detections within radius km from a location, newest first."""
    detections: list[SMHIFireDetection] = []

    for feature in features:
        # GeoJSON coordinates are in longitude, latitude order
        detection_longitude, detection_latitude = feature["geometry"]["coordinates"]
        distance = _distance(
            longitude, latitude, detection_longitude, detection_latitude
        )
        if distance > radius:
            continue

        properties = feature["properties"]
        # The observation time is in Swedish time without an offset
        observation_time = (
            datetime.fromisoformat(properties["observation_time"])
            .replace(tzinfo=SWEDISH_TIME)
            .astimezone(UTC)
        )
        if since and observation_time < since:
            continue

        detections.append(
            SMHIFireDetection(
                id=properties["id"],
                observation_time=observation_time,
                longitude=detection_longitude,
                latitude=detection_latitude,
                distance=round(distance, 2),
                power=properties["power"],
                brightness_temperature=properties["tb"],
                # The API spells it tb_celcius, not tb_celsius as documented
                brightness_temperature_celsius=properties["tb_celcius"],
                confidence=_to_enum(
                    SMHIFireDetectionConfidence, properties["confidence"]
                ),
                anomaly=_to_enum(SMHIFireDetectionAnomaly, properties["anomaly"]),
                platform_name=properties["platform_name"],
            )
        )

    detections.sort(key=lambda x: x["observation_time"], reverse=True)
    LOGGER.debug("Returning %d fire detections for the location", len(detections))
    return detections


def _months(start: datetime, end: datetime) -> list[tuple[int, int]]:
    """Return the (year, month) from start to end."""
    months: list[tuple[int, int]] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


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


def _to_enum(enum: type[_EnumT], value: int) -> _EnumT | None:
    """Return the enum member for a value, or None if the value is unknown."""
    try:
        return enum(value)
    except ValueError:
        LOGGER.warning("Unknown %s value %s", enum.__name__, value)
        return None
