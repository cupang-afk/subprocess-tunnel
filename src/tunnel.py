import logging
import os
import re
import shlex
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


class Tunnel:
    """
    Tunnel class for managing subprocess-based tunnels.
    """

    def __init__(
        self,
        port: int,
        *,
        check_local_port: bool = True,
        debug: bool = False,
        timeout: int = 60,
    ):
        """
        Tunnel class for managing subprocess-based tunnels.

        Args:
            port (int): The local port on which the tunnels will be created.
            check_local_port (bool): Flag to check if the local port is available. Default True.
            debug (bool): Flag to enable debug mode for additional output. Default False.
            timeout (int): Maximum time to wait for the tunnels to start. Default 60.
        """
        self._is_running = False

        self.urls: list[str] = []
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

        self.logger = logging.getLogger("Tunnel")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        for handler in self.logger.handlers:
            self.logger.removeHandler(handler)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG if debug else logging.INFO)
        handler.setFormatter(
            CustomLogFormat("[{asctime} {levelname}]: {message}", datefmt="%X", style="{")
        )
        self.logger.addHandler(handler)

    @classmethod
    def with_tunnel_list(
        cls,
        port: int,
        tunnel_list: list[TunnelDict],
        *,
        check_local_port: bool = True,
        debug: bool = False,
        timeout: int = 60,
    ):
        """
        Create a Tunnel instance with a pre-defined list of tunnels.

        Args:
            port (int): The local port on which the tunnels will be created.
            tunnel_list (list[dict]): List of dictionaries specifying tunnel configurations.
                Each dictionary must have the keys 'command', 'pattern', 'name', and 'note' (optional).
            check_local_port (bool): Flag to check if the local port is available. Default True.
            debug (bool): Flag to enable debug mode for additional output. Default False.
            timeout (int): Maximum time to wait for the tunnels to start. Default 60.
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
                "  note: str"
            )
        init_cls = cls(port, check_local_port=check_local_port, debug=debug, timeout=timeout)
        for tunnel in tunnel_list:
            init_cls.add_tunnel(**tunnel)
        return init_cls

    def add_tunnel(
        self, *, command: str, pattern: re.Pattern | str, name: str, note: Optional[str] = None
    ):
        """
        Add a tunnel.

        Args:
            command (str): The command to execute for the tunnel.
            pattern (re.Pattern | str): A regular expression pattern to match the tunnel URL.
            name (str): The name of the tunnel.
            note (Optional[str]): A note about the tunnel.
        """
        # compile pattern
        if isinstance(pattern, str):
            pattern = re.compile(pattern)
        self.tunnel_list.append(dict(command=command, pattern=pattern, name=name, note=note))

    def start(self):
        """
        Start the tunnel and wait for the URLs to be printed.

        Raises:
            RuntimeError: Raise if tunnel is already running
        """
        if self._is_running:
            raise RuntimeError("Tunnel is already running")

        log = self.logger
        self.__enter__()

        try:
            while not self.printed.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            log.warning("Keyboard Interrupt detected, stopping tunnel")
            self.stop()

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
            process.terminate()

            # If the process was a script and has leftovers
            # (e.g., on Windows when running a .cmd file)
            if process.stdin is not None:
                process.stdin.write(os.linesep)

        for job in self.jobs:
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
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except (socket.timeout, ConnectionRefusedError):
            return False

    @staticmethod
    def wait_for_condition(
        condition: Callable[[], bool], *, interval: int = 1, timeout: int = None
    ) -> bool:
        """
        Wait for the condition to be true until the specified timeout.

        Mostly for internal use but you can use it for anything else.

        Args:
            condition (Callable[[], bool]): The condition to check.
            interval (int): The interval (in seconds) between condition checks.
            timeout (int): Maximum time to wait for the condition. None for no timeout.

        Returns:
            bool: True if the condition is met, False if timeout is reached.
        """
        start_time = time.time()

        if isinstance(interval, float):
            # round up without import anything
            # https://stackoverflow.com/a/35125872
            interval = -(-interval // 1)
        if interval < 1:
            interval = 1
        while not condition():
            if timeout is not None and time.time() - start_time > timeout:
                return False
            time.sleep(interval)

        return True

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
            regex = tunnel["pattern"]
            matches = regex.search(line)
            if matches:
                link = f"{matches.group()}{(' ' + note) if note else ''}".strip()
                with self.urls_lock:
                    self.urls.append(link if link.startswith("http") else "http://" + link)
                return True
        return False

    def _run(self, cmd: str, name: str) -> None:
        """
        Run the tunnel process and monitor its output.

        Args:
            cmd (str): The command to execute for the tunnel.
            name (str): Name of the tunnel.
        """
        log_path = Path(f"tunnel_{name}.log")
        log_path.write_text("")  # Clear the log

        # setup command logger
        log = self.logger.getChild(name)
        for handler in log.handlers:
            log.removeHandler(handler)
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        log.addHandler(handler)

        try:
            if not os.name == "nt":
                cmd = shlex.split(cmd)
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                universal_newlines=True,
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
                lambda: self.is_port_available(self.port) or self.stop_event.is_set(),
                interval=1,
            )

        # Wait until all URLs are available or stop_event is set
        if not self.wait_for_condition(
            lambda: len(self.urls) == len(self.tunnel_list) or self.stop_event.is_set(),
            interval=1,
            timeout=self.timeout,
        ):
            log.warning("Timeout while getting tunnel URLs, print available URLs")

        # Print URLs
        if not self.stop_event.is_set():
            for url in self.urls:
                log.info(f"* Running on: {url}")
            self.printed.set()


if __name__ == "__main__":
    import cloudpickle as pickle

    with Path(__file__).with_suffix(".pkl").open("wb") as f:
        f.write(pickle.dumps(Tunnel))
