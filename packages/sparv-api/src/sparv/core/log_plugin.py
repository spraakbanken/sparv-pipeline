"""Logging plugin for Snakemake, to forward internal Snakemake logs to Sparv's log handler."""


import logging
from collections import defaultdict

from rich.console import Console
from snakemake_interface_logger_plugins.base import LogHandlerBase

from sparv.core.log_handler import SparvLogHandler

# Global registry for the SparvLogHandler instance
sparv_log_handler_instance: SparvLogHandler | None = None


def set_sparv_log_handler(instance: SparvLogHandler) -> None:
    """Set the global SparvLogHandler instance."""
    global sparv_log_handler_instance  # noqa: PLW0603
    sparv_log_handler_instance = instance


class LogHandler(LogHandlerBase):
    """Custom log handler for Snakemake to handle internal logs."""

    def __post_init__(self) -> None:
        """Initialize the log handler."""
        logging.Handler.__init__(self)  # Needed because Snakemake's LogHandlerBase doesn't do this
        super().__post_init__()
        self.console = Console()
        self.messages = defaultdict(list)

    @staticmethod
    def emit(record: logging.LogRecord) -> None:
        """Handle log records from Snakemake.

        This method simply forwards the log record to Sparv's main log handler.

        Args:
            record: The log record to handle.
        """
        sparv_log_handler_instance.snakemake_log_handler(record)

    @property
    def writes_to_stream(self) -> bool:
        """Indicate that we are logging to a stream, which automatically disables the default Snakemake log handler."""
        return True

    @property
    def writes_to_file(self) -> bool:
        """Indicate that we are not writing to a file."""
        return False

    @property
    def has_filter(self) -> bool:
        """Indicate that we are doing our own filtering."""
        return True

    @property
    def has_formatter(self) -> bool:
        """Indicate that we are doing our own formatting."""
        return True

    @property
    def needs_rulegraph(self) -> bool:
        """Indicate that we do not need the rulegraph."""
        return False
