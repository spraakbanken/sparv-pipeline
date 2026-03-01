"""Shared logger definitions used across Sparv."""

from __future__ import annotations

import logging


class CurrentProgress:
    """Class to store current file and job for logging progress."""

    current_file = None
    current_job = None


class SparvLogger(logging.Logger):
    """Custom logger class for Sparv with additional methods."""

    INTERNAL = 100
    PROGRESS = 90
    FINAL = 80

    def progress(
        self: SparvLogger, progress: int | None = None, advance: int | None = None, total: int | None = None
    ) -> None:
        """Log progress of task."""
        if self.isEnabledFor(self.INTERNAL):
            self._log(
                self.INTERNAL,
                "progress",
                (),
                extra={
                    "progress": progress,
                    "advance": advance,
                    "total": total,
                    "job": CurrentProgress.current_job,
                    "file": CurrentProgress.current_file,
                },
            )

    def export_dirs(self: SparvLogger, dirs: list[str]) -> None:
        """Send list of export dirs to log handler."""
        if self.isEnabledFor(self.INTERNAL):
            self._log(self.INTERNAL, "export_dirs", (), extra={"export_dirs": dirs})


def ensure_logger_class() -> None:
    """Ensure SparvLogger and custom log levels are registered."""
    if not issubclass(logging.getLoggerClass(), SparvLogger):
        logging.setLoggerClass(SparvLogger)

    logging.addLevelName(SparvLogger.INTERNAL, "INTERNAL")
    logging.addLevelName(SparvLogger.PROGRESS, "PROGRESS")
    logging.addLevelName(SparvLogger.FINAL, "FINAL")
