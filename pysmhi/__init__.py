"""Python API for SMHI."""

from __future__ import annotations

from .exceptions import (
    SMHIError,
    SmhiFireForecastException,
    SmhiForecastException,
    SmhiRadarException,
)
from .smhi import SmhiAPI
from .smhi_fire_forecast import SMHIFireForecast, SMHIFirePointForecast
from .smhi_forecast import SMHIForecast, SMHIPointForecast
from .smhi_radar import SMHIRadar, SMHIRadarImage

__all__ = [
    "SMHIError",
    "SMHIFireForecast",
    "SMHIFirePointForecast",
    "SMHIForecast",
    "SMHIPointForecast",
    "SMHIRadar",
    "SMHIRadarImage",
    "SmhiAPI",
    "SmhiFireForecastException",
    "SmhiForecastException",
    "SmhiRadarException",
]
