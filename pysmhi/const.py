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
API_RADAR = "https://opendata-download-radar.smhi.se/api/version/latest/area/sweden/product/comp"

LOGGER = logging.getLogger(__package__)

DEFAULT_TIMEOUT = 8
