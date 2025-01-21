"""Constants for SMHI."""

from __future__ import annotations

import logging

API_POINT_FORECAST = (
    "https://opendata-download-metfcst.smhi.se/api/category"
    "/pmp3g/version/2/geotype/point/lon/{}/lat/{}/data.json"
)

LOGGER = logging.getLogger(__package__)

DEFAULT_TIMEOUT = 8
