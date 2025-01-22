"""Exceptions for SMHI."""

from __future__ import annotations


class SMHIError(Exception):
    """Error from SMHI api."""

    def __init__(self, *args: object) -> None:
        """Initialize the exception."""
        super().__init__(*args)

    def __str__(self) -> str:
        """Return exception message."""

        return super().__str__() or str(self.__cause__)


class SmhiForecastException(SMHIError):
    """Exception getting forecast."""
