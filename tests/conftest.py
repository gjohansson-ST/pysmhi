"""Fixtures for SMHI tests."""

from collections.abc import AsyncGenerator

import pytest
from aiointercept import aiointercept


@pytest.fixture(name="mock_aiointercept")
async def get_mock_aiointercept() -> AsyncGenerator[aiointercept]:
    """Mock aiohttp requests to SMHI."""
    async with aiointercept(mock_external_urls=True) as mock:
        yield mock


def request_count(mock: aiointercept) -> int:
    """Return the number of requests made to the mock."""
    return sum(len(calls) for calls in mock.requests.values())
