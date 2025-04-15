"""SMHI API."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from aiohttp import ClientSession, ClientTimeout

from .const import DEFAULT_TIMEOUT, LOGGER
from .exceptions import SMHIError


class SmhiAPI:
    """SMHI api."""

    def __init__(
        self,
        session: ClientSession | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Init the API with or without session."""
        self._session = session if session else ClientSession()
        self._timeout = ClientTimeout(total=timeout)

        self.rate_limit: dict[str, tuple[datetime, dict[str, Any]]] = {}

    async def async_get_data(
        self,
        url: str,
        retry: int = 3,
    ) -> dict[str, Any]:
        """Get data from API asyncronious."""
        LOGGER.debug("Attempting get with url %s", url)

        if url in self.rate_limit:
            last_update, last_data = self.rate_limit[url]
            if (datetime.now(timezone.utc) - last_update).total_seconds() < 60:
                # Return last data if it is less than 60 seconds old
                return last_data

        status = None
        try:
            async with self._session.get(url, timeout=self._timeout) as resp:
                status = resp.status
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()

        except Exception as error:
            LOGGER.debug("Error, status: %s, error: %s", status, str(error))
            if retry > 0:
                LOGGER.debug(
                    "Retry %d on path %s from error %s", 4 - retry, url, str(error)
                )
                await asyncio.sleep(7)
                return await self.async_get_data(url, retry - 1)

            raise SMHIError from error

        self.rate_limit[url] = (datetime.now(timezone.utc), data)
        return data
