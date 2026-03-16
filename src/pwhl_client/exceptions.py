"""Exception hierarchy for pwhl-client."""


class PWHLBaseError(Exception):
    """Base exception for all pwhl-client errors."""


class PWHLConfigError(PWHLBaseError):
    """Raised when required configuration is missing. Reserved for future use."""


class PWHLAPIError(PWHLBaseError):
    """Raised on HTTP error, network failure, or timeout."""


class PWHLParseError(PWHLAPIError):
    """Raised when the API response cannot be parsed or has unexpected shape."""
