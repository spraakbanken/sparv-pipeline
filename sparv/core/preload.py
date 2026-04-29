"""Sparv preloader."""

from __future__ import annotations

import logging
import multiprocessing
import multiprocessing.synchronize
import os
import pickle
import socket
import struct
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from rich.logging import RichHandler

from sparv.core import config, io, log_handler
from sparv.core.console import console
from sparv.core.misc import SparvErrorMessage
from sparv.core.pipeline import PipelineData, RuleInfo

INFO = "INFO"
STATUS = "STATUS"
STOP = "STOP"
PING = "PING"
PONG = "PONG"
PARAMS = "params"
SOCKET = "socket"
PROCESSES = "processes"

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
    if not data:
        return None

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

    # At this point, we should have annotator info in 'data', sent by the preloader client (run_snake.py)
    assert isinstance(data, tuple)

    log.info("Running %s...", data[0])

    annotator = annotators[data[0]]

    # Set target parameter to preloaded data or process
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


def handle_control(
    client_sock: socket.socket,
    annotator_info: dict[str, dict[str, Any]],
    stop_event: multiprocessing.synchronize.Event,
) -> None:
    """Handle a control socket request.

    Args:
        client_sock: Client socket.
        annotator_info: Information about preloaded annotators.
        stop_event: Event to signal when stopping.
    """
    data = receive_data(client_sock)
    if data is None:
        return

    if data == STOP:
        stop_event.set()
    elif data in {INFO, STATUS}:
        send_data(client_sock, annotator_info)
    elif data == PING:
        send_data(client_sock, PONG)


def control_worker(
    server_socket: socket.socket,
    annotator_info: dict[str, dict[str, Any]],
    stop_event: multiprocessing.synchronize.Event,
) -> None:
    """Listen to the control socket and handle info and stop requests.

    Args:
        server_socket: Server socket.
        annotator_info: Information about preloaded annotators.
        stop_event: Event to signal when stopping.
    """
    while not stop_event.is_set():
        try:
            client_sock, _address = server_socket.accept()
        except OSError:
            return

        try:
            handle_control(client_sock, annotator_info, stop_event)
        except:  # noqa: E722
            log.exception("Error during control handling")
        client_sock.close()


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


def get_process_count(annotator: str, processes: int) -> int:
    """Get the number of preloader processes to start for an annotator.

    Args:
        annotator: Annotator name.
        processes: Maximum number of preloader processes.

    Returns:
        Number of preloader processes for the annotator.
    """
    process_limit = (config.get(config.MAX_THREADS, {}) or {}).get(annotator)
    if process_limit:
        return max(1, min(processes, process_limit))
    return processes


def serve(
    socket_path: str, processes: int, pipeline_data: PipelineData, stop_signal: multiprocessing.synchronize.Event
) -> None:
    """Start the Sparv preloader socket server.

    Args:
        socket_path: Path to the socket file.
        processes: Number of processes to start.
        pipeline_data: PipelineData object.
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

    preload_config = config.get("preload")
    if not preload_config:
        raise SparvErrorMessage(
            "Preloader config is missing. Use the 'preload' section in your config file to list annotators to preload."
        )
    rules: dict[str, RuleInfo] = {}
    for rule in pipeline_data.all_rules:
        if rule.has_preloader:
            rules[rule.name] = rule

    log.info("Loading annotators: %s", ", ".join(preload_config))

    annotator_processes = {}  # Annotator name to process count mapping
    for annotator in preload_config:
        if annotator not in rules:
            raise SparvErrorMessage(
                f"Unknown annotator '{annotator}' in preloader config. Either it doesn't exist "
                "or it doesn't support preloading."
            )
        annotator_processes[annotator] = get_process_count(annotator, processes)

    socket_paths = {
        process_count: f"{socket_path}.{process_count}" for process_count in set(annotator_processes.values())
    }
    for worker_socket_path in socket_paths.values():
        if Path(worker_socket_path).exists():
            raise SparvErrorMessage(f"Socket {worker_socket_path} already exists.")

    # Dictionaries of preloaded resources, grouped by their number of worker processes
    annotator_groups = {process_count: {} for process_count in socket_paths}
    annotator_info = {}
    annotator_obj = None

    for annotator in preload_config:
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
        process_count = annotator_processes[annotator]
        annotator_groups[process_count][annotator] = annotator_obj
        annotator_info[annotator] = {
            PARAMS: annotator_obj.params,
            SOCKET: socket_paths[process_count],
            PROCESSES: process_count,
        }

    # Start the sockets (AF_UNIX is also supported on Windows 10 and later)
    worker_sockets = []
    for process_count in annotator_groups:
        server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_socket.bind(socket_paths[process_count])
        server_socket.listen(process_count)
        worker_sockets.append((process_count, server_socket))

    control_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    control_socket.bind(socket_path)
    control_socket.listen(processes)

    stop_event = multiprocessing.Event()

    workers = []

    for process_count, server_socket in worker_sockets:
        annotators = annotator_groups[process_count]
        for i in range(process_count):
            p = multiprocessing.Process(target=worker, args=(i + 1, server_socket, annotators, stop_event))
            p.start()
            workers.append((p, socket_paths[process_count]))

    control_thread = threading.Thread(
        target=control_worker, args=(control_socket, annotator_info, stop_event), daemon=True
    )
    control_thread.start()

    # Free up memory
    del annotator_groups
    del annotator_info
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
            for p, worker_socket_path in workers:
                if p.is_alive():
                    # Send stop signal to worker
                    stop(worker_socket_path)
            break
        time.sleep(2)

    # Remove socket files
    for path in [socket_file, *(Path(worker_socket_path) for worker_socket_path in socket_paths.values())]:
        if path.exists():
            path.unlink()
