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
