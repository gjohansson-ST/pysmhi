"""Python API for SMHI."""

from __future__ import annotations

from .exceptions import SMHIError, SmhiFireForecastException, SmhiForecastException
from .smhi import SmhiAPI
from .smhi_fire_forecast import SMHIFireForecast, SMHIFirePointForecast
from .smhi_forecast import SMHIForecast, SMHIPointForecast

__all__ = [
    "SMHIError",
    "SMHIFireForecast",
    "SMHIFirePointForecast",
    "SMHIForecast",
    "SMHIPointForecast",
    "SmhiAPI",
    "SmhiFireForecastException",
    "SmhiForecastException",
]
