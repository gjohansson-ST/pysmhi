"""Exceptions for SMHI."""


class SMHIError(Exception):
    """Error from SMHI api."""


class SmhiForecastException(SMHIError):
    """Exception getting forecast."""
