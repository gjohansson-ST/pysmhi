"""Python API for SMHI."""

from __future__ import annotations

from .exceptions import (
    SMHIError,
    SmhiFireDetectionException,
    SmhiFireForecastException,
    SmhiForecastException,
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

__all__ = [
    "SMHIError",
    "SMHIFireDetection",
    "SMHIFireDetectionAnomaly",
    "SMHIFireDetectionConfidence",
    "SMHIFireDetections",
    "SMHIFireForecast",
    "SMHIFirePointForecast",
    "SMHIForecast",
    "SMHIPointForecast",
    "SmhiAPI",
    "SmhiFireDetectionException",
    "SmhiFireForecastException",
    "SmhiForecastException",
]
