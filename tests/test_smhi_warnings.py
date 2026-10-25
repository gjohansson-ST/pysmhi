"""Tests for SMHI warnings."""

import json
import pathlib
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import patch

import aiohttp
import pytest
from aiointercept import aiointercept
from syrupy.assertion import SnapshotAssertion

from pysmhi import (
    SMHIPublicWarnings,
    SMHIWarningClassifications,
    SMHIWarningDescription,
    SMHIWarningEventDescription,
    SMHIWarningEvents,
    SmhiWarningException,
)
from pysmhi.smhi_warnings import get_warnings

WARNINGS_URL = (
    "https://opendata-download-warnings.smhi.se/ibww/api/version/1/warning.json"
)

MALMO = (13.0038, 55.605)
KALMAR = (16.3616, 56.6634)
OSTERSUND = (14.6357, 63.1792)
SOUTHEASTERN_BALTIC = (18.9564, 55.2859)
# Corner shared by the Southeastern Baltic and Central Baltic warning areas
BALTIC_BORDER = (20.97639, 56.29807)


@pytest.fixture(autouse=True)
async def mock_sleep() -> AsyncGenerator[None]:
    """Mock no sleeping."""
    with patch("asyncio.sleep"):
        yield


@pytest.fixture(name="mock_data")
async def get_mock_data() -> list[dict[str, Any]]:
    """Mock web response."""
    data = pathlib.Path("tests/warning_data.json").read_text()  # pylint: disable=unspecified-encoding
    json_data: list[dict[str, Any]] = json.loads(data)
    return json_data


def _warning(data: list[dict[str, Any]], warning_id: int) -> dict[str, Any]:
    """Return a warning by id from the data."""
    return next(warning for warning in data if warning["id"] == warning_id)


async def test_api(
    mock_aiointercept: aiointercept,
    mock_data: list[dict[str, Any]],
    snapshot: SnapshotAssertion,
) -> None:
    """Test api."""
    mock_aiointercept.get(WARNINGS_URL, payload=mock_data, repeat=True)

    async with aiohttp.ClientSession() as session:
        warnings = SMHIPublicWarnings("20.97639", "56.29807", session)
        result = await warnings.async_get_warnings()
        warnings_en = SMHIPublicWarnings("20.97639", "56.29807", session, language="en")
        result_en = await warnings_en.async_get_warnings()

    assert result == snapshot(name="warnings")
    assert result_en == snapshot(name="warnings_en")


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        (MALMO, {3122: [9873]}),
        (KALMAR, {3180: [10012]}),
        (SOUTHEASTERN_BALTIC, {3372: [10684]}),
        (BALTIC_BORDER, {3372: [10684, 10685]}),
        (OSTERSUND, {}),
    ],
    ids=["polygon", "multipolygon", "one_area", "border", "no_warnings"],
)
def test_warnings_for_location(
    mock_data: list[dict[str, Any]],
    location: tuple[float, float],
    expected: dict[int, list[int]],
) -> None:
    """Test only warnings and warning areas covering the location are returned."""
    result = get_warnings(mock_data, *location)

    assert {
        warning["id"]: [area["id"] for area in warning["warning_areas"]]
        for warning in result
    } == expected


def test_language(mock_data: list[dict[str, Any]]) -> None:
    """Test texts are in Swedish by default and English falls back to Swedish."""
    warning = get_warnings(mock_data, *MALMO)[0]
    area = warning["warning_areas"][0]
    assert warning["event"] == "Risk för vattenbrist"
    assert area["area_name"] == "Skåne län"
    assert area["affected_areas"] == ["Skåne län"]
    assert area["descriptions"][SMHIWarningDescription.INCIDENT].startswith(
        "Låga grundvattennivåer"
    )

    warning = get_warnings(mock_data, *MALMO, language="en")[0]
    area = warning["warning_areas"][0]
    assert warning["event"] == "Risk for water shortage"
    # The area name is only in Swedish
    assert area["area_name"] == "Skåne län"
    assert area["affected_areas"] == ["Skåne County"]
    assert area["descriptions"][SMHIWarningDescription.INCIDENT].startswith(
        "Low groundwater levels"
    )


def test_feature_collection(mock_data: list[dict[str, Any]]) -> None:
    """Test a warning area given as a FeatureCollection."""
    area = _warning(mock_data, 3122)["warningAreas"][0]
    area["area"] = {"type": "FeatureCollection", "features": [area["area"]]}

    result = get_warnings(mock_data, *MALMO)

    assert [warning["id"] for warning in result] == [3122]


def test_lines_are_skipped(mock_data: list[dict[str, Any]]) -> None:
    """Test warning areas drawn as lines are skipped, also when on the line."""
    area = _warning(mock_data, 3122)["warningAreas"][0]
    exterior = area["area"]["geometry"]["coordinates"][0]
    line = {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": exterior},
    }
    area["area"] = {"type": "FeatureCollection", "features": [line]}

    assert not get_warnings(mock_data, *MALMO)
    assert not get_warnings(mock_data, *exterior[0])


def test_optional_fields(mock_data: list[dict[str, Any]]) -> None:
    """Test optional warning fields."""
    warning = _warning(mock_data, 3122)
    warning["areaName"] = {"sv": "Södra Sverige", "en": "Southern Sweden"}
    warning["descriptions"] = [
        {
            "title": {"sv": "Var", "en": "Where", "code": "WHERE"},
            "text": {"sv": "I Skåne", "en": "In Scania"},
        }
    ]
    del warning["warningAreas"][0]["areaName"]

    result = get_warnings(mock_data, *MALMO, language="en")[0]

    assert result["area_name"] == "Southern Sweden"
    assert result["descriptions"] == {SMHIWarningDescription.WHERE: "In Scania"}
    assert result["warning_areas"][0]["area_name"] is None


def test_approximate_end(mock_data: list[dict[str, Any]]) -> None:
    """Test warning areas with and without an end."""
    assert (
        get_warnings(mock_data, *MALMO)[0]["warning_areas"][0]["approximate_end"]
        is None
    )
    end = get_warnings(mock_data, *SOUTHEASTERN_BALTIC)[0]["warning_areas"][0][
        "approximate_end"
    ]
    assert end is not None
    assert end.isoformat() == "2026-10-22T09:00:00+00:00"


def test_unknown_codes(
    mock_data: list[dict[str, Any]], caplog: pytest.LogCaptureFixture
) -> None:
    """Test unknown codes give None and unknown description titles are skipped."""
    warning = _warning(mock_data, 3122)
    warning["event"]["code"] = "NEW_EVENT"
    area = warning["warningAreas"][0]
    area["warningLevel"]["code"] = "PURPLE"
    area["eventDescription"]["code"] = "NEW_EVENT_DESCRIPTION"
    area["descriptions"][0]["title"]["code"] = "NEW_TITLE"

    result = get_warnings(mock_data, *MALMO)[0]

    assert result["event_code"] is None
    assert result["warning_areas"][0]["warning_level"] is None
    assert result["warning_areas"][0]["event_description"] is None
    assert list(result["warning_areas"][0]["descriptions"]) == [
        SMHIWarningDescription.AFFECT
    ]
    assert "Unknown SMHIWarningEvents code NEW_EVENT" in caplog.text
    assert "Unknown SMHIWarningClassifications code PURPLE" in caplog.text
    assert (
        "Unknown SMHIWarningEventDescription code NEW_EVENT_DESCRIPTION" in caplog.text
    )
    assert "Unknown SMHIWarningDescription code NEW_TITLE" in caplog.text


def test_known_codes(mock_data: list[dict[str, Any]]) -> None:
    """Test codes are converted to enums."""
    warning = get_warnings(mock_data, *SOUTHEASTERN_BALTIC)[0]
    area = warning["warning_areas"][0]

    assert warning["event_code"] is SMHIWarningEvents.WIND_SEA
    assert warning["classification"] == "MET"
    assert area["warning_level"] is SMHIWarningClassifications.YELLOW
    assert area["event_description"] is SMHIWarningEventDescription.GALE_LOW


async def test_api_failure(mock_aiointercept: aiointercept) -> None:
    """Test api failure."""
    mock_aiointercept.get(
        WARNINGS_URL,
        status=500,
        reason="Internal Server Error",
        repeat=True,
    )

    async with aiohttp.ClientSession() as session:
        warnings = SMHIPublicWarnings("13.0038", "55.605", session)
        with pytest.raises(
            SmhiWarningException,
            match=f"500, message='Internal Server Error', url='{WARNINGS_URL}'",
        ):
            await warnings.async_get_warnings()
