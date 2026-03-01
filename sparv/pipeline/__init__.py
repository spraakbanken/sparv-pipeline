"""Main Sparv package."""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from collections.abc import Generator
from typing import Self

__version__ = importlib.metadata.version("sparv")


class SparvCall:
    """Context manager for calling the Sparv pipeline using a subprocess."""

    def __init__(self, args: list[str] | None = None) -> None:
        """Initialize the context manager and start the Sparv pipeline in a subprocess.

        Args:
            args: List of arguments to pass to the Sparv pipeline.
        """
        self.args = args or []
        self._process = None
        self._stdout_iter = None
        self._return_code: int | None = None
        self._started = False

    def _start(self) -> None:
        """Start the Sparv subprocess and prepare to stream output."""
        if self._started:
            return
        cmd = [sys.executable, "-m", "sparv", *self.args]
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._stdout_iter = iter(self._process.stdout)
        self._started = True

    def __enter__(self) -> Self:
        """Enter the context and return the SparvCall instance.

        Returns:
            The SparvCall instance itself.
        """
        self._start()
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: object
    ) -> None:
        """Exit the context and ensure the subprocess finishes."""
        if self._process:
            self._process.wait()
            self._return_code = self._process.returncode
            self._process.stdout.close()

    def _create_log_generator(self) -> Generator[str, None, None]:
        """Create a generator that yields log messages and stdout from the subprocess.

        Yields:
            Log messages and stdout lines from the subprocess.
        """
        self._start()
        for line in self._stdout_iter:
            yield line.rstrip("\n")
        if self._process:
            self._process.wait()
            self._return_code = self._process.returncode

    def __iter__(self) -> SparvCall:
        """Return the SparvCall instance as an iterator."""
        self._log_generator = self._create_log_generator()
        return self

    def __next__(self) -> str:
        """Return the next log message or stdout line from the generator."""
        return next(self._log_generator)

    def get_return_value(self) -> bool:
        """Retrieve the return value of the pipeline call.

        Returns:
            True if the pipeline call was successful, False otherwise.

        Raises:
            RuntimeError: If the subprocess is still running or no return value is available.
        """
        if self._return_code is not None:
            return self._return_code == 0
        raise RuntimeError("The subprocess is still running or no return value is available.")

    def wait(self) -> bool:
        """Wait for the subprocess to finish and return the return value.

        Returns:
            True if the pipeline call was successful, False otherwise.
        """
        if self._process:
            self._process.wait()
            self._return_code = self._process.returncode
        return self.get_return_value()


def call(args: list[str] | None = None, /) -> SparvCall:
    """Call the Sparv pipeline.

    This function returns a context manager that can be used to either iterate over log messages
    or simply wait for the pipeline to finish.

    The list of arguments are the same as the arguments you would pass to the command-line interface,
    e.g. `["run", "xml_export:pretty", "--log"]`.

    Args:
        args: List of arguments to pass to the Sparv pipeline.

    Returns:
        A context manager for managing the Sparv pipeline call.
    """
    return SparvCall(args)
