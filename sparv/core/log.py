"""Logging configuration."""
import logging

FORMAT = "%(asctime)s - %(name)s (%(process)d) - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(verbose=False):
    """Set up logging."""
    log_level = logging.INFO if verbose else logging.CRITICAL

    logging.basicConfig(format=FORMAT, datefmt=DATE_FORMAT, level=log_level)
