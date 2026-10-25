"""Python API for SMHI."""

from __future__ import annotations

from .exceptions import (
    SMHIError,
    SmhiFireDetectionException,
    SmhiFireForecastException,
    SmhiForecastException,
    SmhiNotFoundException,
    SmhiObservationException,
    SmhiRadarException,
    SmhiWarningException,
)
from .smhi import SmhiAPI
from .smhi_fire_detections import (
    SMHIFireDetection,
    SMHIFireDetectionAnomaly,
    SMHIFireDetectionConfidence,
    SMHIFireDetections,
)
from .smhi_fire_forecast import SMHIFireForecast, SMHIFirePointForecast
from .smhi_forecast import SMHIForecast, SMHIPointForecast
from .smhi_observations import (
    SMHIObservation,
    SMHIObservationParameter,
    SMHIObservationQuality,
    SMHIPointObservations,
    SMHIPresentWeather,
    SMHIStation,
    SMHIStationObservations,
)
from .smhi_radar import SMHIRadar, SMHIRadarImage
from .smhi_warnings import (
    SMHIPublicWarnings,
    SMHIWarningAreas,
    SMHIWarningClassifications,
    SMHIWarningDescription,
    SMHIWarningEventDescription,
    SMHIWarningEvents,
    SMHIWarnings,
)

__all__ = [
    "SMHIError",
    "SMHIFireDetection",
    "SMHIFireDetectionAnomaly",
    "SMHIFireDetectionConfidence",
    "SMHIFireDetections",
    "SMHIFireForecast",
    "SMHIFirePointForecast",
    "SMHIForecast",
    "SMHIObservation",
    "SMHIObservationParameter",
    "SMHIObservationQuality",
    "SMHIPointForecast",
    "SMHIPointObservations",
    "SMHIPresentWeather",
    "SMHIPublicWarnings",
    "SMHIRadar",
    "SMHIRadarImage",
    "SMHIStation",
    "SMHIStationObservations",
    "SMHIWarningAreas",
    "SMHIWarningClassifications",
    "SMHIWarningDescription",
    "SMHIWarningEventDescription",
    "SMHIWarningEvents",
    "SMHIWarnings",
    "SmhiAPI",
    "SmhiFireDetectionException",
    "SmhiFireForecastException",
    "SmhiForecastException",
    "SmhiNotFoundException",
    "SmhiObservationException",
    "SmhiRadarException",
    "SmhiWarningException",
]
