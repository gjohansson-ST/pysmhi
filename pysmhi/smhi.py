"""SMHI API."""

from __future__ import annotations

import asyncio
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

    async def async_get_data(
        self,
        url: str,
        retry: int = 3,
    ) -> dict[str, Any]:
        """Get data from API asyncronious."""
        LOGGER.debug("Attempting get with url %s", url)
        try:
            async with self._session.get(url, timeout=self._timeout) as resp:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()

        except Exception as error:
            LOGGER.debug("Error, status: %s, error: %s", resp.status, str(error))
            if retry > 0:
                LOGGER.debug(
                    "Retry %d on path %s from error %s", 4 - retry, url, str(error)
                )
                await asyncio.sleep(7)
                return await self.async_get_data(url, retry - 1)

            raise SMHIError from error

        return data
