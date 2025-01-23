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

python module for communicating with [Nord Pool](https://data.nordpoolgroup.com/auction/day-ahead/prices)

**Supports**

- Daily forecast
- Hourly forecast
- Bi-daily forecast

## Code example

### Get daily forecast

Hourly rates from provided date

```python
from pysmhi import SMHIForecast, SMHIPointForecast

async with aiohttp.ClientSession(loop=loop) as session:
    client = SMHIPointForecast("16.15035", "58.570784", session)
    daily_forecast: list[SMHIForecast] = await forecast.async_get_daily_forecast()
    print(daily_forecast)
```
