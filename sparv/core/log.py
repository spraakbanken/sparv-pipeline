"""Logging configuration."""

import copy
import logging

from sparv import util

FORMAT = "%(asctime)s - %(name)s (%(process)d) - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_COLORS = {
    logging.ERROR: util.Color.RED,
    logging.WARNING: util.Color.YELLOW
}


class ColorFormatter(logging.Formatter):
    """Custom log formatter for adding colors.

    http://uran198.github.io/en/python/2016/07/12/colorful-python-logging.html
    https://stackoverflow.com/questions/15870380/python-custom-logging-across-all-modules
    """

    def format(self, record, *args, **kwargs):
        """Colorise levelname and message in the log output."""
        # If the corresponding logger has children, they may receive modified record, so we want to keep it intact
        new_record = copy.copy(record)
        if new_record.levelno in LOG_COLORS:
            new_record.levelname = f"{LOG_COLORS[new_record.levelno]}{new_record.levelname}{util.Color.RESET}"
            new_record.msg = f"{LOG_COLORS[new_record.levelno]}{new_record.getMessage()}{util.Color.RESET}"
        # Let standart formatting take care of the rest
        return super(ColorFormatter, self).format(new_record, *args, **kwargs)


def setup_logging(verbose=False):
    """Set up logging with custom formatter."""
    log_level = logging.INFO if verbose else logging.CRITICAL

    # "Simple" logging without custom formatting
    # logging.basicConfig(format=FORMAT, datefmt=DATE_FORMAT, level=log_level)

    log = logging.getLogger("sparv")
    log.setLevel(log_level)
    handler = logging.StreamHandler()
    formatter = ColorFormatter(FORMAT)
    handler.setFormatter(formatter)
    log.addHandler(handler)
