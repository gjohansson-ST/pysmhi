"""Python API for SMHI."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from .smhi_forecast import SMHIForecast, SMHIPointForecast
from .exceptions import SMHIError,SmhiForecastException
from .smhi import SmhiAPI


__all__ = [
    "SmhiAPI",
    "SMHIError",
    "SMHIForecast",
    "SmhiForecastException",
    "SMHIPointForecast",
]
