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
API_FIRE_DETECTIONS = (
    "https://opendata-download-satellite.smhi.se/api/category"
    "/firedetections/version/1/year/{}/month/{:02d}/data.json"
)
API_OBSERVATIONS = (
    "https://opendata-download-metobs.smhi.se/api/version/latest"
    "/parameter/{}/station/{}/period/latest-hour/data.json"
)
API_OBSERVATIONS_ALL_STATIONS = (
    "https://opendata-download-metobs.smhi.se/api/version/latest"
    "/parameter/{}/station-set/all/period/latest-hour/data.json"
)
API_PUBLIC_WARNINGS = (
    "https://opendata-download-warnings.smhi.se/ibww/api/version/1/warning.json"
)
API_RADAR = "https://opendata-download-radar.smhi.se/api/version/latest/area/sweden/product/comp"

LOGGER = logging.getLogger(__package__)

DEFAULT_TIMEOUT = 8
