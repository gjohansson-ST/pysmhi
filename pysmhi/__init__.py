"""Python API for SMHI."""

from __future__ import annotations

from .exceptions import (
    SMHIError,
    SmhiFireForecastException,
    SmhiForecastException,
    SmhiWarningException,
)
from .smhi import SmhiAPI
from .smhi_fire_forecast import SMHIFireForecast, SMHIFirePointForecast
from .smhi_forecast import SMHIForecast, SMHIPointForecast
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
    "SMHIFireForecast",
    "SMHIFirePointForecast",
    "SMHIForecast",
    "SMHIPointForecast",
    "SMHIPublicWarnings",
    "SMHIWarningAreas",
    "SMHIWarningClassifications",
    "SMHIWarningDescription",
    "SMHIWarningEventDescription",
    "SMHIWarningEvents",
    "SMHIWarnings",
    "SmhiAPI",
    "SmhiFireForecastException",
    "SmhiForecastException",
    "SmhiWarningException",
]
