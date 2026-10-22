[![size_badge](https://img.shields.io/github/repo-size/gjohansson-ST/pysmhi?style=for-the-badge&cacheSeconds=3600)](https://github.com/gjohansson-ST/pysmhi)
[![version_badge](https://img.shields.io/github/v/release/gjohansson-ST/pysmhi?label=Latest%20release&style=for-the-badge&cacheSeconds=3600)](https://github.com/gjohansson-ST/pysmhi/releases/latest)
[![download_badge](https://img.shields.io/pypi/dm/pysmhi?style=for-the-badge&cacheSeconds=3600)](https://github.com/gjohansson-ST/pysmhi/releases/latest)
![GitHub Repo stars](https://img.shields.io/github/stars/gjohansson-ST/pysmhi?style=for-the-badge&cacheSeconds=3600)
![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/gjohansson-ST/pysmhi?style=for-the-badge&cacheSeconds=3600)
![GitHub License](https://img.shields.io/github/license/gjohansson-ST/pysmhi?style=for-the-badge&cacheSeconds=3600)

[![Made for Home Assistant](https://img.shields.io/badge/Made_for-Home%20Assistant-blue?style=for-the-badge&logo=homeassistant)](https://github.com/home-assistant)

[![Sponsor me](https://img.shields.io/badge/Sponsor-Me-blue?style=for-the-badge&logo=github)](https://github.com/sponsors/gjohansson-ST)
[![Discord](https://img.shields.io/discord/872446427664625664?style=for-the-badge&label=Discord&cacheSeconds=3600)](https://discord.gg/EG7cWFQMGW)

# pysmhi

python module for communicating with [SMHI](https://opendata.smhi.se/)

## Supported applications

- Daily weather forecast
- Hourly weather forecast
- Bi-daily weather forecast
- Daily fire risk
- Hourly fire risk
- Radar image and precipitation at a location

## Code examples

### Get daily forecast

Retrieves the daily forecast for the specified location

```python
from pysmhi import SMHIForecast, SMHIPointForecast

async with aiohttp.ClientSession(loop=loop) as session:
    client = SMHIPointForecast("16.15035", "58.570784", session)
    daily_forecast = await client.async_get_daily_forecast()
    print(daily_forecast)
```

### Get radar

Retrieves the latest [radar](https://opendata.smhi.se/radar/introduction) image of
Sweden, updated every 5 minutes, and the precipitation at the specified location.

The reflectivity (`dbz`) at the location is read from the radar image and converted to
precipitation in mm/h. Reflectivities below 5 dBZ are not counted as precipitation.

```python
import asyncio

import aiohttp

from pysmhi import SMHIRadarImage


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        client = SMHIRadarImage("17.92", "63.81", session)
        radar = await client.async_get_radar()
        print(radar)
        image = await client.async_get_image()  # PNG image on a map as bytes


asyncio.run(main())
```

Result:

```python
{
    "valid_time": datetime(2026, 10, 21, 18, 55, tzinfo=UTC),
    "image_url": "https://opendata-download-radar.smhi.se/api/version/latest/area/sweden/product/comp/latest.png",
    "dbz": 48.8,
    "precipitation": 52.4,
}
```

The `dbz` is `None` if there is no echo, and the precipitation is then 0. Both are
`None` if there is no radar data at the location, e.g. outside Sweden.

The radar image from SMHI only contains the radar echoes, so `async_get_image()` returns
it on a background map of Sweden with the location marked by a red dot. The map is
drawn from [Natural Earth](https://www.naturalearthdata.com/) (public domain) by
`script/generate_radar_basemap.py`. The `image_url` is the radar image without a map.

Credits to [@helto4real](https://github.com/helto4real) for making the original smhi api package used for Home Assistant to connect to SMHI weather services which this is based upon.
