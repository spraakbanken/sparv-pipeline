"""Miscellaneous classes and methods."""

import logging


class SparvErrorMessage(Exception):
    """Exception used to notify users of errors in a friendly way without displaying traceback."""

    start_marker = "<<<START>>>"
    end_marker = "<<<END>>>"

    def __init__(self, message, module="", function=""):
        """Raise an error and notify user of the problem in a friendly way.

        Args:
            message: Error message.
            module: Name of module where error occurred (optional, not used in Sparv modules)
            function: Name of function where error occurred (optional, not used in Sparv modules)
        """
        self.message = message
        # Alter message before calling base class
        super().__init__("{}{}\n{}\n{}{}".format(SparvErrorMessage.start_marker, module, function, message,
                                                 SparvErrorMessage.end_marker))


def get_logger(name):
    """Get a logger that is a child of 'sparv.modules'."""
    if not name.startswith("sparv.modules"):
        name = "sparv.modules." + name
    return logging.getLogger(name)

