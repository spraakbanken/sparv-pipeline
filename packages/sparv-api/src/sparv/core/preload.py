"""Sparv preloader."""

from __future__ import annotations

import logging
import multiprocessing
import multiprocessing.synchronize
import os
import pickle
import socket
import struct
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from rich.logging import RichHandler

from sparv.core import config, io, log_handler
from sparv.core.console import console
from sparv.core.misc import SparvErrorMessage
from sparv.core.snake_utils import SnakeStorage

INFO = "INFO"
STATUS = "STATUS"
STOP = "STOP"
PING = "PING"
PONG = "PONG"

# Set up logging
log = logging.getLogger("sparv_preloader")
log.setLevel(logging.INFO)
handler = RichHandler(show_path=False, rich_tracebacks=True, console=console)
handler.setFormatter(logging.Formatter("%(message)s", datefmt=log_handler.DATE_FORMAT))
log.addHandler(handler)

# Set compression
compression = config.get("sparv.compression")
if compression:
    io.compression = compression


class Preloader:
    """Class representing a preloader."""

    def __init__(
        self, function: Callable, target: str, preloader: Callable, params: dict, cleanup: Callable, shared: bool
    ) -> None:
        """Initialize a preloader."""
        self.function = function
        self.target = target
        self.preloader = preloader
        self.params = params
        self.cleanup = cleanup
        self.shared = shared
        self.preloaded = None


def connect_to_socket(socket_path: str, timeout: bool = False) -> socket.socket:
    """Connect to a socket and return it.

    Args:
        socket_path: Path to the socket file.
        timeout: Whether to use a 1-second timeout when connecting.

    Returns:
        A connected socket.
    """
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    if timeout:
        s.settimeout(1)
    s.connect(socket_path)
    s.settimeout(None)
    return s


@contextmanager
def socketcontext(socket_path: str) -> Iterator[socket.socket]:
    """Context manager for socket.

    Args:
        socket_path: Path to the socket file.

    Yields:
        A connected socket.
    """
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(socket_path)
    try:
        yield s
    finally:
        s.close()


def receive_data(sock: socket.socket) -> Any:
    """Receive pickled data from a socket and unpickle it.

    Args:
        sock: Socket object.

    Returns:
        Unpickled data.
    """
    # Get data length
    data_length_bytes = 4
    buf_length = recvall(sock, data_length_bytes)
    if not buf_length or len(buf_length) < data_length_bytes:
        return None
    (length,) = struct.unpack(">I", buf_length)

    # Get data
    data = recvall(sock, length)

    # Unpickle data and return
    return pickle.loads(data)


def send_data(sock: socket.socket, data: Any) -> None:
    """Send pickled data over a socket.

    Args:
        sock: Socket object.
        data: Data to send.
    """
    datap = pickle.dumps(data)
    sock.sendall(struct.pack(">I", len(datap)))
    sock.sendall(datap)


def get_preloader_info(socket_path: str) -> dict:
    """Get information about preloaded modules.

    Args:
        socket_path: Path to the socket file.

    Returns:
        Information about preloaded modules.
    """
    with socketcontext(socket_path) as sock:
        send_data(sock, INFO)
        return receive_data(sock)


def get_preloader_status(socket_path: str) -> Any:
    """Get preloader status.

    Args:
        socket_path: Path to the socket file.

    Returns:
        Preloader status.
    """
    with socketcontext(socket_path) as sock:
        send_data(sock, STATUS)
        return receive_data(sock)


def stop(socket_path: str) -> bool:
    """Send stop signal to Sparv preloader.

    Args:
        socket_path: Path to the socket file.

    Returns:
        True if the preloader was successfully stopped, False if the connection was refused.
    """
    try:
        with socketcontext(socket_path) as sock:
            send_data(sock, STOP)
            return True
    except ConnectionRefusedError:
        return False


def recvall(sock: socket.socket, size: int) -> bytes | None:
    """Receive data of a specific size from a socket.

    If 'size' number of bytes are not received, None is returned.

    Args:
        sock: Socket object.
        size: Number of bytes to receive.

    Returns:
        Received data.
    """
    buf = b""
    while size:
        newbuf = sock.recv(size)
        if not newbuf:
            return None
        buf += newbuf
        size -= len(newbuf)
    return buf


def handle(client_sock: socket.socket, annotators: dict[str, Preloader]) -> bool | None:
    """Handle request and execute preloaded function.

    Args:
        client_sock: Client socket.
        annotators: Dictionary of preloaded annotators.

    Returns:
        False if stop signal is received, otherwise None.
    """
    # Get data
    data = receive_data(client_sock)
    if data is None:
        return None

    # Check if we got a command instead of annotator info
    if isinstance(data, str):
        if data == STOP:
            return False
        if data == INFO:
            send_data(client_sock, {k: v.params for k, v in annotators.items()})
            return None
        if data == PING:
            try:
                send_data(client_sock, PONG)
            except BrokenPipeError:
                return None
            data = receive_data(client_sock)

    log.info("Running %s...", data[0])

    annotator = annotators[data[0]]

    # Set target parameter to preloaded data
    data[1][annotator.target] = annotator.preloaded

    # Set up logging over socket
    log_handler.setup_logging(
        data[2]["log_server"],
        log_level=data[2]["log_level"],
        log_file_level=data[2]["log_file_level"],
        file=data[3],
        job=data[0],
    )

    # Call annotator function
    try:
        annotator.function(**data[1])
    except SparvErrorMessage as e:
        send_data(client_sock, e)
        return None
    except Exception as e:
        console.print_exception()
        send_data(client_sock, e)
        return None
    finally:
        # Clear log handlers
        logger = logging.getLogger("sparv")
        logger.handlers.clear()

    log.info("Done")

    send_data(client_sock, True)

    # Run cleanup if available
    if annotator.cleanup:
        annotator.preloaded = annotator.cleanup(**{**annotator.params, annotator.target: annotator.preloaded})

    return None


def worker(
    worker_no: int,
    server_socket: socket.socket,
    annotators: dict[str, Preloader],
    stop_event: multiprocessing.synchronize.Event,
) -> None:
    """Listen to the socket server and handle incoming requests.

    Args:
        worker_no: Worker number.
        server_socket: Server socket.
        annotators: Dictionary of preloaded annotators.
        stop_event: Event to signal when stopping.
    """
    log.info("Worker %d started", worker_no)

    # Load any non-shared preloaders
    for annotator in annotators.values():
        if not annotator.shared:
            annotator.preloaded = annotator.preloader(**annotator.params)

    while True:
        try:
            client_sock, _address = server_socket.accept()  # Accept a connection
        except KeyboardInterrupt:
            stop_event.set()
            return

        try:
            log.debug("Handling request")
            result = handle(client_sock, annotators)
            if result is False:
                stop_event.set()
                return
        except:  # noqa: E722
            log.exception("Error during handling")
        client_sock.close()


def serve(
    socket_path: str, processes: int, storage: SnakeStorage, stop_signal: multiprocessing.synchronize.Event
) -> None:
    """Start the Sparv preloader socket server.

    Args:
        socket_path: Path to the socket file.
        processes: Number of processes to start.
        storage: SnakeStorage object.
        stop_signal: Event to signal when stopping.

    Raises:
        SparvErrorMessage: If the socket already exists, or if an annotator in the preloader config is unknown, or if
            the annotator doesn't support preloading.
    """
    socket_file = Path(socket_path)
    if socket_file.exists():
        raise SparvErrorMessage(f"Socket {socket_path} already exists.")

    # If processes is not set, set it to the number of processors
    if not processes:
        processes = multiprocessing.cpu_count()

    # Dictionary of preloaded models, indexed by module and annotator name
    annotators = {}

    preload_config = config.get("preload")
    if not preload_config:
        raise SparvErrorMessage(
            "Preloader config is missing. Use the 'preload' section in your config file to list annotators to preload."
        )
    rules = {}
    for rule in storage.all_rules:
        if rule.has_preloader:
            rules[rule.target_name] = rule

    log.info("Loading annotators: %s", ", ".join(preload_config))

    for annotator in preload_config:
        if annotator not in rules:
            raise SparvErrorMessage(
                f"Unknown annotator '{annotator}' in preloader config. Either it doesn't exist "
                "or it doesn't support preloading."
            )
        rule = rules[annotator]
        preloader_params = {}
        for param in rule.annotator_info["preloader_params"]:
            preloader_params[param] = rule.parameters[param]

        annotator_obj = Preloader(
            rule.annotator_info["function"],
            rule.annotator_info["preloader_target"],
            rule.annotator_info["preloader"],
            preloader_params,
            rule.annotator_info["preloader_cleanup"],
            rule.annotator_info["preloader_shared"],
        )
        if annotator_obj.shared:
            annotator_obj.preloaded = annotator_obj.preloader(**annotator_obj.params)
        annotators[annotator] = annotator_obj

    # Start the socket (AF_UNIX should be supported in Windows 10 since 2018)
    server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_socket.bind(socket_path)
    server_socket.listen(processes)

    stop_event = multiprocessing.Event()

    workers = []

    for i in range(processes):
        p = multiprocessing.Process(target=worker, args=(i + 1, server_socket, annotators, stop_event))
        p.start()
        workers.append(p)

    # Free up memory
    del annotators
    del annotator_obj

    log.info(
        "The Sparv preloader is ready and waiting for connections using the socket at %s. "
        "Run Sparv with the command 'sparv run --socket /path/to/socket' to use the preloader. "
        "Press Ctrl-C to exit, or run 'sparv preload stop --socket /path/to/socket'. You can also stop the "
        "preloader by sending an interrupt signal to the process with id %d.",
        socket_file.absolute(),
        os.getpid(),
    )

    # Periodically check whether stop_event is set or not and stop all processes when set
    while True:
        if stop_event.is_set() or stop_signal.is_set():
            log.info("Stopping all workers...")
            for p in workers:
                if p.is_alive():
                    # Send stop signal to worker
                    stop(socket_path)
            break
        time.sleep(2)

    # Remove socket file
    if socket_file.exists():
        socket_file.unlink()
