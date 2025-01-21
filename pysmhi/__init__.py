"""Python API for SMHI."""

from __future__ import annotations

from .exceptions import SMHIError, SmhiForecastException
from .smhi import SmhiAPI
from .smhi_forecast import SMHIForecast, SMHIPointForecast

__all__ = [
    "SMHIError",
    "SMHIForecast",
    "SMHIPointForecast",
    "SmhiAPI",
    "SmhiForecastException",
]
