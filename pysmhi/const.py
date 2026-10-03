"""Constants for SMHI."""

from __future__ import annotations

import logging

API_POINT_FORECAST = (
    "https://opendata-download-metfcst.smhi.se/api/category"
    "/snow1g/version/1/geotype/point/lon/{}/lat/{}/data.json"
)
API_FIRE_FORECAST = (
    "https://opendata-download-metfcst.smhi.se/api/category"
    "/fwif1g/version/1/{}/geotype/point/lon/{}/lat/{}/data.json"
)
API_PUBLIC_WARNINGS = (
    "https://opendata-download-warnings.smhi.se/ibww/api/version/1/warning.json"
)


LOGGER = logging.getLogger(__package__)

DEFAULT_TIMEOUT = 8
