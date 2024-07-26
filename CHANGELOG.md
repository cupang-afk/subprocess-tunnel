## 0.2.2 (2024-07-26)

### Feat

- **Tunnel**: add tunnel name into callback calls

### Fix

- **Tunnel**: ensure typing for python 3.8 support

## 0.2.1 (2024-04-14)

### Fix

- **Tunnel**: log callback error when it happen

## 0.2.0 (2024-04-02)

### Feat

- **Tunnel**: add log_handlers parameter to add handler to Tunnel.logger
- **Tunnel**: set minimum python 3.8 (before was 3.10)
- **Tunnel**: add get_port()

### Fix

- **Tunnel.add_tunnel**: fix unique name extending to tunnel_1_2 instead of tunnel_2
- **Tunnel._print**: fix port is online log being printed when stop_event is set

### Refactor

- **Tunnel**: change is_port_available to is_port_in_use as Tunnel usually check if port is in use by another process
- **Tunnel.add_tunnel**: add name checking
- **Tunnel.stop**: make stop gracefully
- refactor output type for typing

## 0.1.2 (2024-03-31)

## 0.1.1 (2024-03-31)

### Fix

- **Tunnel**: fix Tunnel.with_tunnel_list didn't have same parameter as Tunnel.__init__ when it should be the same
- **Tunnel**: fix log_dir os.getcwd when frozen

## 0.1.0 (2024-03-30)

### Feat

- **Tunnel**: add callback
- **Tunnel**: add propagate log to root logger option

### Refactor

- **Tunnel.is_port_available**: refactor is_port_available

## 0.0.6 (2024-02-23)

### Fix

- **Tunnel.stop**: fix AttributeError: module 'signal' has no attribute 'CTRL_BREAK_EVENT' on linux (and possibly CTRL_C_EVENT)

### Refactor

- add var for Windows checking

### Perf

- **Tunnel.\_run**: use bufsize=1 to buff per line

## 0.0.5 (2024-02-13)

### Fix

- **Tunnel.stop**: fix tunnel won't stopping
- **Tunnel.start**: move check_local_port above the run (i forgot lol, now it work as expected)

### Refactor

- **logger**: by default when invoke logging.getLogger we have empty handler, so we don't need to remove the handler (getChild also apply)
- **build**: change message from --no-test to --with-test
- **build**: fix ModuleNotFoundError: No module named 'tunnel' when loading pickle file from build_tunnel.py

## 0.0.4 (2024-02-10)

### Perf

- **Tunnel.wait_for_condition**: improve wait_for_condition to wait until exact timeout

## 0.0.3 (2024-02-10)

### Refactor

- **build**: change --no-test to --with-test, and default to False (building things required testing but "build" in this case is just for pickling, so no need to test unless it set)

## 0.0.2 (2024-02-10)

### Fix

- **Tunnel.start**: ensure check_local_port is False when invoking start() to instantly print the URLs instead of waiting the port

### Refactor

- **Tunnel.\_run**: wait for port to be available before running the command if check_local_port is True
- **build**: move build process to build_tunnel.py instead in tunnel.py (as expected)

## 0.0.1 (2024-02-10)

### Fix

- **Tunnel.**init\*\*\*\*: set propagate to False to prevent log message being sent to root logger

### Refactor

- use commitizen for versioning
