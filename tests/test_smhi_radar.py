"""Tests for SMHI radar."""

import json
import pathlib
from collections.abc import AsyncGenerator
from io import BytesIO
from typing import Any, cast
from unittest.mock import patch

import aiohttp
import pytest
from aiointercept import aiointercept
from PIL import Image
from syrupy.assertion import SnapshotAssertion

from pysmhi import SmhiRadarException, SMHIRadarImage
from pysmhi.smhi_radar import (
    get_map_image,
    get_radar_values,
    to_pixel,
    to_sweref99tm,
)

URL = "https://opendata-download-radar.smhi.se/api/version/latest/area/sweden/product/comp"
TIF_URL = f"{URL}/latest.tif"
PNG_URL = f"{URL}/latest.png"

HEAVY_RAIN = (18.1, 64.1)
OSTERSUND = (14.6357, 63.1792)
STOCKHOLM = (18.0686, 59.3293)


@pytest.fixture(autouse=True)
async def mock_sleep() -> AsyncGenerator[None]:
    """Mock no sleeping."""
    with patch("asyncio.sleep"):
        yield


@pytest.fixture(name="mock_data")
def get_mock_data() -> dict[str, Any]:
    """Return the radar composite for Sweden."""
    data = pathlib.Path("tests/radar_comp.json").read_text()  # pylint: disable=unspecified-encoding
    json_data: dict[str, Any] = json.loads(data)
    return json_data


@pytest.fixture(name="image")
def get_image() -> bytes:
    """Return the radar GeoTIFF valid 2026-10-21 19:10 UTC."""
    return pathlib.Path("tests/radar_latest.tif").read_bytes()


async def test_api(
    mock_aiointercept: aiointercept,
    mock_data: dict[str, Any],
    image: bytes,
    snapshot: SnapshotAssertion,
) -> None:
    """Test api."""
    mock_aiointercept.get(URL, payload=mock_data)
    mock_aiointercept.get(TIF_URL, body=image)

    async with aiohttp.ClientSession() as session:
        client = SMHIRadarImage("18.1", "64.1", session)
        result = await client.async_get_radar()

    assert result == snapshot


async def test_image(
    mock_aiointercept: aiointercept, mock_data: dict[str, Any]
) -> None:
    """Test the radar image on the background map with the location marked."""
    mock_aiointercept.get(URL, payload=mock_data)
    mock_aiointercept.get(
        PNG_URL, body=pathlib.Path("tests/radar_latest.png").read_bytes()
    )

    async with aiohttp.ClientSession() as session:
        client = SMHIRadarImage("14.6357", "63.1792", session)
        result = await client.async_get_image()

    with Image.open(BytesIO(result)) as image:
        assert image.format == "PNG"
        assert image.size == (942, 1774)
        pixels = image.convert("RGB")

    def pixel(location: tuple[float, float]) -> tuple[int, ...]:
        x, y = to_pixel(*location, scale=2)
        return cast("tuple[int, ...]", pixels.getpixel((round(x), round(y))))

    # Marker at Östersund
    assert pixel(OSTERSUND) == (220, 0, 0)
    # Map without echo in the Gulf of Bothnia and on land in the north
    assert pixel((20.0, 62.5)) == (170, 211, 223)
    assert pixel((16.0, 66.5)) == (242, 239, 233)
    # Radar on top, the colour for 49 dBZ
    assert pixel(HEAVY_RAIN) == (211, 0, 211)


def test_image_wrong_size(caplog: pytest.LogCaptureFixture) -> None:
    """Test a radar image not matching the map is returned as is."""
    image = BytesIO()
    Image.new("RGBA", (10, 10)).save(image, format="PNG")

    assert get_map_image(image.getvalue(), *OSTERSUND) == image.getvalue()
    assert "Radar image size (10, 10) doesn't match the map" in caplog.text


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        (HEAVY_RAIN, (49.2, 55.72)),
        (OSTERSUND, (8.8, 0.11)),
        ((15.6, 62.0), (4.4, 0.0)),
        (STOCKHOLM, (None, 0.0)),
        ((24.94, 60.17), (None, None)),
        ((5.32, 60.39), (None, None)),
    ],
    ids=[
        "heavy_rain",
        "light_rain",
        "below_5_dbz",
        "no_echo",
        "no_data",
        "outside_image",
    ],
)
def test_radar_values(
    image: bytes,
    location: tuple[float, float],
    expected: tuple[float | None, float | None],
) -> None:
    """Test dBZ and precipitation at a location.

    Helsinki is in the image without radar data and Bergen is outside the image.
    """
    assert get_radar_values(image, *location) == expected


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ((18.0686, 59.3293), (674571.866, 6580743.008)),
        ((13.3593, 55.3369), (395933.071, 6133508.047)),
        ((20.5486, 69.0603), (721046.260, 7671092.045)),
        ((24.1365, 65.8355), (916164.317, 7331934.206)),
        ((11.1667, 58.9361), (279437.125, 6539260.515)),
    ],
    ids=["stockholm", "smygehuk", "treriksroset", "haparanda", "stromstad"],
)
def test_to_sweref99tm(
    location: tuple[float, float], expected: tuple[float, float]
) -> None:
    """Test conversion to SWEREF99 TM against pyproj (EPSG:4326 to EPSG:3006)."""
    easting, northing = to_sweref99tm(*location)

    assert easting == pytest.approx(expected[0], abs=0.001)
    assert northing == pytest.approx(expected[1], abs=0.001)


def test_unexpected_image_mode() -> None:
    """Test an image which is not 8-bit greyscale."""
    image = BytesIO()
    Image.new("RGB", (2, 2)).save(image, format="TIFF")

    with pytest.raises(SmhiRadarException, match="Unexpected radar image mode RGB"):
        get_radar_values(image.getvalue(), *STOCKHOLM)


async def test_no_latest_image(
    mock_aiointercept: aiointercept, mock_data: dict[str, Any]
) -> None:
    """Test data without a latest PNG and GeoTIFF image."""
    mock_data["lastFiles"] = [
        file
        for file in mock_data["lastFiles"]
        if [file_format["key"] for file_format in file["formats"]] == ["h5"]
    ]
    mock_aiointercept.get(URL, payload=mock_data)

    async with aiohttp.ClientSession() as session:
        client = SMHIRadarImage("18.1", "64.1", session)
        with pytest.raises(SmhiRadarException, match="No latest radar image in data"):
            await client.async_get_radar()


async def test_api_failure(mock_aiointercept: aiointercept) -> None:
    """Test api failure."""
    mock_aiointercept.get(URL, status=500, reason="Internal Server Error", repeat=True)
    match = f"500, message='Internal Server Error', url='{URL}'"

    async with aiohttp.ClientSession() as session:
        client = SMHIRadarImage("18.1", "64.1", session)
        with pytest.raises(SmhiRadarException, match=match):
            await client.async_get_radar()
        with pytest.raises(SmhiRadarException, match=match):
            await client.async_get_image()
