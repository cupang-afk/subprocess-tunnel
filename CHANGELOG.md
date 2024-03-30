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
