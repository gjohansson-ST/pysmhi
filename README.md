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
- Satellite fire detections near a location

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

### Get fire detections

Retrieves the [satellite fire detections](https://opendata.smhi.se/satellite/firedetections/introduction)
near the specified location, newest first.

Only detections within `radius` km from the location during the last `days` days are
included. The defaults are 50 km and 7 days.

```python
import asyncio

import aiohttp

from pysmhi import SMHIFireDetections


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        client = SMHIFireDetections("17.1413", "60.6749", session)
        detections = await client.async_get_fire_detections(radius=150, days=30)
        print(detections)


asyncio.run(main())
```

Result, showing the first detection:

```python
[
    {
        "id": "20261007-1",
        "observation_time": datetime(2026, 10, 7, 10, 31, 42, tzinfo=UTC),
        "longitude": 17.202057,
        "latitude": 60.60487,
        "distance": 8.46,
        "power": 2.1,
        "brightness_temperature": 329.2,
        "brightness_temperature_celsius": 56,
        "confidence": SMHIFireDetectionConfidence.NOMINAL,
        "anomaly": SMHIFireDetectionAnomaly.NONE,
        "platform_name": "NOAA-20",
    },
    ...,
]
```

The observation time is converted from Swedish time to UTC. The `anomaly` tells if the
detection is at a known persistent heat source, e.g. a gas flare or a solar panel.

Credits to [@helto4real](https://github.com/helto4real) for making the original smhi api package used for Home Assistant to connect to SMHI weather services which this is based upon.
