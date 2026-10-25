"""SMHI API."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

from aiohttp import ClientSession, ClientTimeout

from .const import DEFAULT_TIMEOUT, LOGGER
from .exceptions import SMHIError, SmhiNotFoundException


class SmhiAPI:
    """SMHI api."""

    def __init__(
        self,
        session: ClientSession | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Init the API with or without session."""
        self._session = session or ClientSession()
        self._timeout = ClientTimeout(total=timeout)

        self.rate_limit: dict[str, tuple[datetime, Any]] = {}

    async def async_get_data(
        self,
        url: str,
        retry: int = 3,
    ) -> dict[str, Any]:
        """Get data from API asyncronious."""
        data: dict[str, Any] = await self._async_get(url, retry, as_json=True)
        return data

    async def async_get_bytes(
        self,
        url: str,
        retry: int = 3,
    ) -> bytes:
        """Get binary data, e.g. an image, from API asyncronious."""
        data: bytes = await self._async_get(url, retry, as_json=False)
        return data

    async def _async_get(
        self,
        url: str,
        retry: int,
        as_json: bool,
    ) -> Any:
        """Get JSON or binary data from API asyncronious."""
        LOGGER.debug("Attempting get with url %s", url)

        if url in self.rate_limit:
            last_update, last_data = self.rate_limit[url]
            if (datetime.now(UTC) - last_update).total_seconds() < 60:
                # Return last data if it is less than 60 seconds old
                return last_data

        status = None
        try:
            async with self._session.get(url, timeout=self._timeout) as resp:
                status = resp.status
                resp.raise_for_status()
                data = await resp.json() if as_json else await resp.read()

        except Exception as error:
            LOGGER.debug("Error, status: %s, error: %s", status, str(error))
            # Missing data doesn't appear by retrying
            if status == HTTPStatus.NOT_FOUND:
                raise SmhiNotFoundException from error
            if retry > 0:
                LOGGER.debug(
                    "Retry %d on path %s from error %s", 4 - retry, url, str(error)
                )
                await asyncio.sleep(7)
                return await self._async_get(url, retry - 1, as_json)

            raise SMHIError from error

        self.rate_limit[url] = (datetime.now(UTC), data)
        return data
