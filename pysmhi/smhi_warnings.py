"""SMHI warnings."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, TypedDict

from aiohttp import ClientSession

from .const import API_PUBLIC_WARNINGS, LOGGER
from .exceptions import SMHIError, SmhiWarningException
from .smhi import SmhiAPI


class SMHIWarningClassifications(StrEnum):
    """SMHI warning classifications."""

    MESSAGE = "message"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"


class SMHIWarningDescription(StrEnum):
    """SMHI warning descriptions."""

    HAPPENS = "happens"
    INCIDENT = "incident"
    AFFECT = "affect"
    COMMENTS = "comments"
    WHERE = "where"
    WATERCOURSE = "watercourse"
    GROUNDWATER_MINOR = "groundwater_minor"
    GROUNDWATER_MAJOR = "groundwater_major"


class SMHIWarningEvents(StrEnum):
    """SMHI warning events."""

    THUNDER = "thunderstorm"
    WIND = "wind"
    WIND_MOUNTAINS = "wind_mountains"
    WIND_MOUNTAINS_SNOW = "wind_snow_mountains"
    STRONG_COOLING = "strong_cooling"
    SNOW = "snow"
    WIND_SNOW = "wind_snow"
    BLACK_ICE = "black_ice"
    RAIN = "rain"
    FIRE = "fire"
    HIGH_TEMPERATURES = "high_temperatures"
    WIND_SEA = "wind_sea"
    ICE_ACCRETION = "ice_accretion"
    LOW_SEA_LEVEL = "low_sea_level"
    HIGH_SEALEVEL = "high_sealevel"
    WATER_SHORTAGE = "water_shortage"
    HIGH_FLOW = "high_flow"
    FLOODING = "flooding"


class SMHIWarningEventDescription(StrEnum):
    """SMHI warning events descriptions."""

    WIND = "wind"
    WIND_MOUNTAINS = "wind_mountains"
    WIND_MOUNTAINS_SNOW = "wind_snow_mountains"
    STRONG_COOLING = "strong_cooling"
    SNOW = "snow"
    WIND_SNOW = "wind_snow"
    ICE = "ice"
    BLACK_ICE = "black_ice"
    RAIN = "rain"
    CLOUDBURST = "cloudburst"
    GRASS_FIRE = "grass_fire"
    FOREST_FIRE = "forest_fire"
    HIGH_TEMPERATURES = "high_temperatures"
    THUNDER = "thunderstorm"
    GALE_LOW = "gale_low"
    GALE_HIGH = "gale_high"
    STORM = "storm"
    HURRICANE = "hurricane"
    LOW_SEA_LEVEL = "low_sea_level"
    ICE_ACCRETION = "ice_accretion"
    SEVERE_ICE_ACCRETION = "severe_ice_accretion"
    HIGH_WATER_LEVEL = "high_water_level"
    HIGH_SEALEVEL = "high_sealevel"
    HIGH_FLOW = "high_flow"
    FLOODING = "flooding"
    WATER_SHORTAGE = "water_shortage"
    GROUNDWATER_MAJOR = "groundwater_major"
    GROUNDWATER_MINOR = "groundwater_minor"
    GROUNDWATER_MINOR_MAJOR = "groundwater_minor_major"
    WATERCOURSES = "watercourses"
    WATERCOURSES_GROUNDWATER_MAJOR = "watercourses_groundwater_major"
    WATERCOURSES_GROUNDWATER_MINOR = "watercourses_groundwater_minor"
    WATERCOURSES_GROUNDWATER_MINOR_MAJOR = "watercourses_groundwater_minor_major"


class SMHIWarningAreas(TypedDict, total=False):
    """SMHI warning areas.

    https://opendata.smhi.se/warnings/resources/warning
    """

    id: int
    approx_start: datetime
    created: datetime
    published: datetime
    approx_end: datetime | None
    probability_normal: bool  # False if low confidence
    area_name: str | None
    warning_level: list[SMHIWarningClassifications]
    event_description: list[SMHIWarningEventDescription]
    affected_areas: list[str]
    descriptions: dict[SMHIWarningDescription, str] | None
    area_type: Literal["Polygon", "MultiPolygon"]
    area_coordinates: list[list[list[float | list[float]]]]


class SMHIWarnings(TypedDict, total=False):
    """SMHI warnings.

    https://opendata.smhi.se/warnings/resources/warning
    """

    id: int
    event_code: str
    classification: str
    probability_normal: bool  # False if low confidence
    warning_areas: list[SMHIWarningAreas]
    descriptions: dict[SMHIWarningDescription, str] | None


class SMHIPublicWarnings:
    """SMHI Open Data API - Warnings."""

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

    async def async_get_warnings(self) -> list[SMHIWarnings]:
        """Return a list of all warnings."""
        LOGGER.debug("Getting daily forecast")
        try:
            json_data = await self._api.async_get_data(
                API_PUBLIC_WARNINGS,
            )
        except SMHIError as error:
            LOGGER.debug("Error getting warnings: %s", str(error))
            raise SmhiWarningException from error
        LOGGER.debug(
            "Got %d warnings ",
            len(json_data),
        )

        if len(json_data) == 0:
            return []

        warnings = []

        for warning in json_data:
            warning_id = warning.get("id")
            probability_normal = warning.get("normalProbability")
            event_code = warning.get("event", {}).get("code")
            classification = (
                warning.get("event", {}).get("mhoClassification", {}).get("code")
            )
            warnings.append(
                SMHIWarnings(
                    id=warning_id,
                    probability_normal=probability_normal,
                    event_code=event_code,
                    classification=classification,
                )
            )

        return warnings
