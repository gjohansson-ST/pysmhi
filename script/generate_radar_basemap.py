"""Generate the background map for the SMHI radar images.

Draws the countries and lakes from Natural Earth (public domain) in the grid of
the radar images in SWEREF99 TM, at BASEMAP_SCALE times the radar resolution.

Run from the repository root: python script/generate_radar_basemap.py
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from pysmhi.smhi_radar import BASEMAP, BASEMAP_SCALE, RADAR_SIZE, to_pixel

NATURAL_EARTH = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/"
)
LAYERS = ("ne_50m_admin_0_countries.geojson", "ne_50m_lakes.geojson")
# Only draw polygons with a point in this area, which covers the radar images
LONGITUDE_RANGE = (-5.0, 45.0)
LATITUDE_RANGE = (50.0, 75.0)

SEA = (170, 211, 223)
LAND = (242, 239, 233)
BORDER = (150, 150, 150)
COLORS = 16


def _polygons(url: str) -> list[list[list[float]]]:
    """Return the outer rings of the polygons in the area from a GeoJSON file."""
    # The url is the https Natural Earth url above
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
        data: dict[str, Any] = json.load(response)
    rings: list[list[list[float]]] = []
    for feature in data["features"]:
        geometry = feature["geometry"]
        polygons = (
            geometry["coordinates"]
            if geometry["type"] == "MultiPolygon"
            else [geometry["coordinates"]]
        )
        rings.extend(
            polygon[0]
            for polygon in polygons
            if any(
                LONGITUDE_RANGE[0] <= longitude <= LONGITUDE_RANGE[1]
                and LATITUDE_RANGE[0] <= latitude <= LATITUDE_RANGE[1]
                for longitude, latitude in polygon[0]
            )
        )
    return rings


def main() -> None:
    """Draw the background map and save it in the package."""
    size = (RADAR_SIZE[0] * BASEMAP_SCALE, RADAR_SIZE[1] * BASEMAP_SCALE)
    image = Image.new("RGB", size, SEA)
    draw = ImageDraw.Draw(image)
    countries, lakes = (_polygons(NATURAL_EARTH + layer) for layer in LAYERS)
    for ring in countries:
        draw.polygon(
            [to_pixel(lon, lat, BASEMAP_SCALE) for lon, lat in ring],
            fill=LAND,
            outline=BORDER,
        )
    for ring in lakes:
        draw.polygon(
            [to_pixel(lon, lat, BASEMAP_SCALE) for lon, lat in ring],
            fill=SEA,
            outline=BORDER,
        )

    path = Path(__file__).parent.parent / "pysmhi" / BASEMAP
    image.quantize(colors=COLORS).save(path, format="PNG", optimize=True)
    print(f"Saved {path} {size}")  # noqa: T201


if __name__ == "__main__":
    main()
