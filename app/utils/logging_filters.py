"""Logging filters for reducing expected noise in development."""

import logging


class OptionalApiKeyWarningFilter(logging.Filter):
    """Downgrade optional-provider missing API key warnings to DEBUG."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno == logging.WARNING and "API key not configured" in (
            record.getMessage()
        ):
            record.levelno = logging.DEBUG
            record.levelname = "DEBUG"
        return True
