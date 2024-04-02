import logging
import os
import re
import shlex
import signal
import socket
import subprocess
import time
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Callable, Optional, TypedDict


class CustomLogFormat(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        names = record.name.split(".") if record.name else []
        if len(names) > 1:
            _, *names = names
            record.msg = f"[{' '.join(names)}] {record.msg}"
        return super().format(record)


class TunnelDict(TypedDict):
    command: str
    pattern: re.Pattern
    name: str
    note: Optional[str]
    callback: Optional[Callable[[str, str], None]]  # (url, note) -> None


class Tunnel:
    """
    Tunnel class for managing subprocess-based tunnels.

    Args:
        port (int): The local port on which the tunnels will be created.
        check_local_port (bool): Flag to check if the local port is available. Default True.
        debug (bool): Flag to enable debug mode for additional output. Default False.
        timeout (int): Maximum time to wait for the tunnels to start. Default 60.
        propagate (bool): Flag to propagate log messages to the root logger, \
            if False will create custom log format to print log. Default False.
        log_dir (os.PathLike): Directory to store log files. If None it will set to os.get_cwd(). Default None.
        callback (Callable[[list[tuple[str, str | None]]], None]): A callback function to be called when Tunnel URL is printed.\
            `callback([(url1, note1), (url2, note2), ...]) -> None`
    """

    def __init__(
        self,
        port: int,
        *,
        check_local_port: bool = True,
        debug: bool = False,
        timeout: int = 60,
        propagate: bool = False,
        log_dir: str | os.PathLike = None,
        callback: Callable[[list[tuple[str, str | None]]], None] = None,
    ):
        self._is_running = False

        self.urls: list[tuple[str, str | None]] = []
        self.urls_lock = Lock()

        self.jobs: list[Thread] = []
        self.processes: list[subprocess.Popen] = []
        self.tunnel_list: list[TunnelDict] = []

        self.stop_event: Event = Event()
        self.printed = Event()

        self.port = port
        self.check_local_port = check_local_port
        self.debug = debug
        self.timeout = timeout
        self.log_dir = log_dir or os.getcwd()
        self.callback = callback

        self.logger = logging.getLogger("Tunnel")
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        # write our own logger format when propagate is false
        if not propagate:
            self.logger.propagate = False
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                handler.setLevel(self.logger.level)
                handler.setFormatter(
                    CustomLogFormat("[{asctime} {levelname}]: {message}", datefmt="%X", style="{")
                )
                self.logger.addHandler(handler)

        self.WINDOWS = True if os.name == "nt" else False

    @classmethod
    def with_tunnel_list(
        cls,
        port: int,
        tunnel_list: list[TunnelDict],
        *,
        check_local_port: bool = True,
        debug: bool = False,
        timeout: int = 60,
        propagate: bool = False,
        log_dir: str | os.PathLike = None,
        callback: Callable[[list[tuple[str, str | None]]], None] = None,
    ):
        """
        Create a Tunnel instance with a pre-defined list of tunnels.

        Args:
            port (int): The local port on which the tunnels will be created.
            tunnel_list (list[dict]): List of dictionaries specifying tunnel configurations.
                Each dictionary must have the keys `command`, `pattern`, `name`, `note` (optional), and `callback` (optional).
            check_local_port (bool): Flag to check if the local port is available. Default True.
            debug (bool): Flag to enable debug mode for additional output. Default False.
            timeout (int): Maximum time to wait for the tunnels to start. Default 60.
            propagate (bool): Flag to propagate log messages to the root logger, \
                if False will create custom log format to print log. Default False.
            log_dir (os.PathLike): Directory to store log files. If None it will set to os.get_cwd(). Default None.
            callback (Callable[[list[tuple[str, str | None]]], None]): A callback function to be called when Tunnel URL is printed.\
                `callback([(url1, note1), (url2, note2), ...]) -> None`
        """
        if not tunnel_list or not all(
            isinstance(i, dict)
            and {"command", "pattern", "name"}.issubset(i)
            and isinstance(i["command"], str)
            and isinstance(i["pattern"], (re.Pattern, str))
            and isinstance(i["name"], str)
            for i in tunnel_list
        ):
            raise ValueError(
                "tunnel_list must be a list of dictionaries with required key-value pairs:\n"
                "  command: str\n"
                "  pattern: re.Pattern | str\n"
                "  name: str\n"
                "optional key-value pairs:\n"
                "  note: str\n"
                "  callback: Callable[[str, str], None]"
            )
        init_cls = cls(
            port,
            check_local_port=check_local_port,
            debug=debug,
            timeout=timeout,
            propagate=propagate,
            log_dir=log_dir,
            callback=callback,
        )
        for tunnel in tunnel_list:
            init_cls.add_tunnel(**tunnel)
        return init_cls

    def add_tunnel(
        self,
        *,
        command: str,
        pattern: re.Pattern | str,
        name: str,
        note: str = None,
        callback: Callable[[str, str], None] = None,
    ):
        """
        Add a tunnel.

        Args:
            command (str): The command to execute for the tunnel.
            pattern (re.Pattern | str): A regular expression pattern to match the tunnel URL.
            name (str): The name of the tunnel.
            note (Optional[str]): A note about the tunnel.
            callback (Callable[[str, str], None]): A callback function to be called when when the regex pattern matched.\
                `callback(url, note) -> None`
        """
        # compile pattern
        if isinstance(pattern, str):
            pattern = re.compile(pattern)
        self.tunnel_list.append(
            dict(command=command, pattern=pattern, name=name, note=note, callback=callback)
        )

    def start(self):
        """
        Start the tunnel and wait for the URLs to be printed.

        Raises:
            RuntimeError: Raise if tunnel is already running
        """
        if self._is_running:
            raise RuntimeError("Tunnel is already running")

        _check_local_port = self.check_local_port
        self.check_local_port = False

        log = self.logger
        self.__enter__()

        try:
            while not self.printed.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            log.warning("Keyboard Interrupt detected, stopping tunnel")
            self.stop()
        finally:
            self.check_local_port = _check_local_port

    def stop(self):
        """
        Stop the tunnel and reset internal state.

        Raises:
            RuntimeError: Raise if tunnel is not running
        """
        if not self._is_running:
            raise RuntimeError("Tunnel is not running")

        log = self.logger
        log.info("Stopping tunnel")
        self.stop_event.set()

        for process in self.processes:
            log.debug(f"Stopping {process}")
            while process.poll() is None:
                try:
                    process.communicate(timeout=15)
                except subprocess.TimeoutExpired:
                    if self.WINDOWS:
                        process.send_signal(signal.CTRL_BREAK_EVENT)
                        process.send_signal(signal.CTRL_C_EVENT)
                    process.kill()
            process.communicate()

        for job in self.jobs:
            log.debug(f"Join thread {job}")
            job.join()

        self.reset()

    def __enter__(self):
        if self._is_running:
            raise RuntimeError("Tunnel is already running by another method")

        if not self.tunnel_list:
            raise ValueError("No tunnels added")

        log = self.logger
        log.info("Tunnel Started")

        # Add print job
        print_job = Thread(target=self._print)
        print_job.start()
        self.jobs.append(print_job)

        # Add tunnels job
        for tunnel in self.tunnel_list:
            cmd = tunnel["command"]
            name = tunnel.get("name")
            tunnel_thread = Thread(
                target=self._run,
                args=(cmd.format(port=self.port),),
                kwargs={"name": name},
            )
            tunnel_thread.start()
            self.jobs.append(tunnel_thread)

        self._is_running = True

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.stop()

    def reset(self):
        """
        Reset internal state.
        """
        self.urls = []
        self.jobs = []
        self.processes = []
        self.stop_event.clear()
        self.printed.clear()
        self._is_running = False

    @staticmethod
    def is_port_available(port: int) -> bool:
        """
        Check if the specified port is available.

        Args:
            port (int): The port to check.

        Returns:
            bool: True if the port is available, False otherwise.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                # equal to 0 meaning there is an app that use it
                return s.connect_ex(("localhost", port)) != 0
        except OSError:
            return False

    @staticmethod
    def wait_for_condition(
        condition: Callable[[], bool], *, interval: int = 1, timeout: int | None = 10
    ) -> bool:
        """
        Wait for the condition to be true until the specified timeout.

        Mostly for internal use but can be used for anything else.

        Args:
            condition (Callable[[], bool]): The condition to check.
            interval (int): The interval (in seconds) between condition checks.
            timeout (int): Maximum time to wait for the condition. None for no timeout.

        Returns:
            bool: True if the condition is met, False if timeout is reached.
        """
        start_time = time.time()

        # Initialize variables to track elapsed time and number of checks
        elapsed_time = 0
        checks_count = 0

        # Prevent zero or negative timeout
        if timeout is not None:
            timeout = max(1, timeout)

        while True:
            if condition():
                return True

            checks_count += 1

            if timeout is not None:
                elapsed_time = time.time() - start_time
                remaining_time = timeout - elapsed_time

                # If remaining time is non-positive, return False (timeout occurred)
                if remaining_time <= 0:
                    return False

                # Adjust the interval to respect the remaining time
                # and distribute it evenly among the remaining checks
                next_interval = min(interval, remaining_time / (checks_count + 1))
            else:
                next_interval = interval

            time.sleep(next_interval)

    def _process_line(self, line: str) -> bool:
        """
        Process a line of output to extract tunnel information.

        Args:
            line (str): A line of output from the tunnel process.

        Returns:
            bool: True if a URL is extracted, False otherwise.
        """
        for tunnel in self.tunnel_list:
            note = tunnel.get("note")
            callback = tunnel.get("callback")
            regex = tunnel["pattern"]
            matches = regex.search(line)
            if matches:
                link = matches.group().strip()
                link = link if link.startswith("http") else "http://" + link
                with self.urls_lock:
                    self.urls.append((link, note))
                if callback:
                    callback(link, note)
                return True
        return False

    def _run(self, cmd: str, name: str) -> None:
        """
        Run the tunnel process and monitor its output.

        Args:
            cmd (str): The command to execute for the tunnel.
            name (str): Name of the tunnel.
        """
        log_path = Path(self.log_dir, f"tunnel_{name}.log")
        log_path.write_text("")  # Clear the log

        # setup command logger
        log = self.logger.getChild(name)
        if not log.handlers:
            handler = logging.FileHandler(log_path, encoding="utf-8")
            handler.setLevel(logging.DEBUG)
            log.addHandler(handler)

        try:
            if self.check_local_port:
                # Wait until the port is available or stop_event is set
                log.debug(
                    f"Wait until port: {self.port} online before running the command for {name}"
                )
                self.wait_for_condition(
                    lambda: not self.is_port_available(self.port) or self.stop_event.is_set(),
                    interval=1,
                    timeout=None,
                )
            if not self.WINDOWS:
                cmd = shlex.split(cmd)
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if self.WINDOWS else 0,
            )
            self.processes.append(process)

            url_extracted = False
            while not self.stop_event.is_set() and process.poll() is None:
                line = process.stdout.readline()
                if not line:
                    break
                if not url_extracted:
                    url_extracted = self._process_line(line)

                log.debug(line.rstrip())

        except Exception:
            log.error(f"An error occurred while running the command: {cmd}", exc_info=True)
        finally:
            for handler in log.handlers:
                handler.close()

    def _print(self) -> None:
        """
        Print the tunnel URLs.
        """
        log = self.logger
        log.info("Getting URLs")

        if self.check_local_port:
            # Wait until the port is available or stop_event is set
            log.info(f"Wait until port: {self.port} online before print URLs")
            self.wait_for_condition(
                lambda: not self.is_port_available(self.port) or self.stop_event.is_set(),
                interval=1,
                timeout=None,
            )
            if not self.stop_event.is_set():
                log.info(f"Port is online, waiting tunnel URLs (timeout: {self.timeout}s)")

        # Wait until all URLs are available or stop_event is set
        if not self.wait_for_condition(
            lambda: len(self.urls) == len(self.tunnel_list) or self.stop_event.is_set(),
            interval=1,
            timeout=self.timeout,
        ):
            log.warning("Timeout while getting tunnel URLs, print available URLs")

        # Print URLs
        if not self.stop_event.is_set():
            with self.urls_lock:
                for url, note in self.urls:
                    log.info(f"* Running on: {url}{(' ' + note) if note else ''}")
                if self.callback:
                    self.callback(self.urls)
            self.printed.set()
