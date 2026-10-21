"""SMHI warnings."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, TypedDict, TypeVar

from aiohttp import ClientSession
from shapely.geometry import Point, shape

from .const import API_PUBLIC_WARNINGS, LOGGER
from .exceptions import SMHIError, SmhiWarningException
from .smhi import SmhiAPI

_EnumT = TypeVar("_EnumT", bound=StrEnum)


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


class SMHIWarningAreas(TypedDict):
    """SMHI warning area.

    https://opendata.smhi.se/warnings/objects
    """

    id: int
    area_name: str | None
    approximate_start: datetime
    approximate_end: datetime | None  # None if the area has no end
    published: datetime
    probability_normal: bool  # False if low confidence
    warning_level: SMHIWarningClassifications | None  # None if unknown
    event_description: SMHIWarningEventDescription | None  # None if unknown
    affected_areas: list[str]
    descriptions: dict[SMHIWarningDescription, str]


class SMHIWarnings(TypedDict):
    """SMHI warning.

    https://opendata.smhi.se/warnings/objects
    """

    id: int
    event_code: SMHIWarningEvents | None  # None if unknown
    event: str
    classification: str
    probability_normal: bool  # False if low confidence
    area_name: str | None
    warning_areas: list[SMHIWarningAreas]
    descriptions: dict[SMHIWarningDescription, str]


class SMHIPublicWarnings:
    """SMHI Open Data API - Warnings.

    https://opendata.smhi.se/warnings/introduction
    """

    def __init__(
        self,
        longitude: str,
        latitude: str,
        session: ClientSession | None = None,
        language: Literal["sv", "en"] = "sv",
    ) -> None:
        """Init the SMHI warnings."""
        self._longitude = str(round(float(longitude), 6))
        self._latitude = str(round(float(latitude), 6))
        self._language = language
        self._api = SmhiAPI(session)

    async def async_get_warnings(self) -> list[SMHIWarnings]:
        """Return the warnings for the location.

        Only the warning areas covering the location are included.
        """
        LOGGER.debug("Getting warnings")
        try:
            json_data: list[dict[str, Any]] = await self._api.async_get_data(
                API_PUBLIC_WARNINGS,
            )
        except SMHIError as error:
            LOGGER.debug("Error getting warnings: %s", str(error))
            raise SmhiWarningException from error
        LOGGER.debug("Got %d warnings", len(json_data))

        return get_warnings(
            json_data, float(self._longitude), float(self._latitude), self._language
        )


def get_warnings(
    data: list[dict[str, Any]],
    longitude: float,
    latitude: float,
    language: Literal["sv", "en"] = "sv",
) -> list[SMHIWarnings]:
    """Get the warnings with warning areas covering a location."""
    # GeoJSON coordinates are in longitude, latitude order
    location = Point(longitude, latitude)
    warnings: list[SMHIWarnings] = []

    for warning in data:
        warning_areas = [
            _create_warning_area(warning_area, language)
            for warning_area in warning["warningAreas"]
            if _area_covers(warning_area["area"], location)
        ]
        if not warning_areas:
            continue

        event = warning["event"]
        warnings.append(
            SMHIWarnings(
                id=warning["id"],
                event_code=_to_enum(SMHIWarningEvents, event["code"]),
                event=_text(event, language),
                classification=event["mhoClassification"]["code"],
                probability_normal=warning["normalProbability"],
                area_name=_optional_text(warning.get("areaName"), language),
                warning_areas=warning_areas,
                descriptions=_descriptions(warning.get("descriptions"), language),
            )
        )

    LOGGER.debug("Returning %d warnings for the location", len(warnings))
    return warnings


def _area_covers(area: dict[str, Any], location: Point) -> bool:
    """Return True if a GeoJSON Feature or FeatureCollection covers the location.

    Only polygons are considered, as a location can't be within e.g. a line
    along a coast or a watercourse.
    """
    features = area["features"] if area["type"] == "FeatureCollection" else [area]
    return any(
        shape(feature["geometry"]).covers(location)
        for feature in features
        if feature["geometry"]["type"] in ("Polygon", "MultiPolygon")
    )


def _create_warning_area(
    warning_area: dict[str, Any], language: Literal["sv", "en"]
) -> SMHIWarningAreas:
    """Convert a warning area from json data."""
    approximate_end = warning_area.get("approximateEnd")
    return SMHIWarningAreas(
        id=warning_area["id"],
        area_name=_optional_text(warning_area.get("areaName"), language),
        approximate_start=datetime.fromisoformat(warning_area["approximateStart"]),
        approximate_end=datetime.fromisoformat(approximate_end)
        if approximate_end
        else None,
        published=datetime.fromisoformat(warning_area["published"]),
        probability_normal=warning_area["normalProbability"],
        warning_level=_to_enum(
            SMHIWarningClassifications, warning_area["warningLevel"]["code"]
        ),
        event_description=_to_enum(
            SMHIWarningEventDescription, warning_area["eventDescription"]["code"]
        ),
        affected_areas=[
            _text(area, language) for area in warning_area["affectedAreas"]
        ],
        descriptions=_descriptions(warning_area.get("descriptions"), language),
    )


def _to_enum(enum: type[_EnumT], code: str) -> _EnumT | None:
    """Return the enum member for a code, or None if the code is unknown."""
    try:
        return enum[code]
    except KeyError:
        LOGGER.warning("Unknown %s code %s", enum.__name__, code)
        return None


def _text(text: dict[str, Any], language: Literal["sv", "en"]) -> str:
    """Return the text in the language, falling back to Swedish if missing.

    Some texts, e.g. area names for water shortage, are only in Swedish.
    """
    return str(text.get(language) or text["sv"])


def _optional_text(
    text: dict[str, Any] | None, language: Literal["sv", "en"]
) -> str | None:
    """Return an optional text in the language."""
    return _text(text, language) if text else None


def _descriptions(
    descriptions: list[dict[str, Any]] | None, language: Literal["sv", "en"]
) -> dict[SMHIWarningDescription, str]:
    """Return the descriptions by title, skipping unknown titles."""
    result: dict[SMHIWarningDescription, str] = {}
    for description in descriptions or []:
        if title := _to_enum(SMHIWarningDescription, description["title"]["code"]):
            result[title] = _text(description["text"], language)
    return result
