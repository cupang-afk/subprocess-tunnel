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

- **Tunnel._run**: wait for port to be available before running the command if check_local_port is True
- **build**: move build process to build_tunnel.py instead in tunnel.py (as expected)

## 0.0.1 (2024-02-10)

### Refactor

- use commitizen for versioning

### Fix

- **Tunnel.__init__**: set propagate to False to prevent log message being sent to root logger
