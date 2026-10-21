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
- Latest observations from the nearest weather station

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

### Get observations

Retrieves the [observations](https://opendata.smhi.se/metobs/introduction) during the
latest hour of the given parameters from a weather station. By default the station
nearest the specified location, which had a temperature observation during the latest
hour, is used.

The API serves one parameter per request, so the parameters are requested in parallel.
Parameters without an observation, e.g. as the station doesn't observe them, are `None`.

```python
import asyncio

import aiohttp

from pysmhi import SMHIObservationParameter, SMHIPointObservations


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        client = SMHIPointObservations("13.0038", "55.605", session)
        observations = await client.async_get_observations(
            [
                SMHIObservationParameter.TEMPERATURE,
                SMHIObservationParameter.WIND_SPEED,
                SMHIObservationParameter.PRESENT_WEATHER,
            ]
        )
        print(observations)


asyncio.run(main())
```

Result:

```python
{
    "station_id": "52350",
    "station_name": "Malmö A",
    "longitude": 13.0708,
    "latitude": 55.5715,
    "height": 19.757,
    "distance": 5.62,
    "observations": {
        SMHIObservationParameter.TEMPERATURE: {
            "value": 12.574771,
            "time": datetime(2026, 10, 21, 20, 37, tzinfo=UTC),
            "quality": SMHIObservationQuality.GREEN,
        },
        SMHIObservationParameter.WIND_SPEED: {
            "value": 2.713146,
            "time": datetime(2026, 10, 21, 20, 37, tzinfo=UTC),
            "quality": SMHIObservationQuality.GREEN,
        },
        SMHIObservationParameter.PRESENT_WEATHER: {
            "value": 100.0,
            "time": datetime(2026, 10, 21, 20, 0, tzinfo=UTC),
            "quality": SMHIObservationQuality.GREEN,
            "weather": SMHIPresentWeather.NO_SIGNIFICANT_WEATHER,
        },
    },
}
```

To use another station, e.g. one observing more parameters, list the stations nearest
the location and give the id or name of a station. With an id, only the parameters are
requested.

```python
stations = await client.async_get_stations()
# [{"station_id": "52350", "station_name": "Malmö A", ..., "distance": 5.62}, ...]
parameters = [SMHIObservationParameter.TEMPERATURE]
observations = await client.async_get_observations(parameters, "52350")
observations = await client.async_get_observations(parameters, "Malmö A")
```

The parameters are humidity and present weather, observed every hour, and temperature,
precipitation, wind speed, wind direction, visibility and snow depth, observed every
minute. The latest observation is given for each parameter.

The quality is green if the observation is checked and approved, and yellow if it's
suspect, aggregated or not checked.

The present weather is a code, which is also given as `weather`, e.g.
`SMHIPresentWeather.RAIN` for code 123 and `SMHIPresentWeather.LIGHT_RAIN` for code 161.

Credits to [@helto4real](https://github.com/helto4real) for making the original smhi api package used for Home Assistant to connect to SMHI weather services which this is based upon.
