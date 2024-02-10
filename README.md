# python tunnel

This Python package provides a convenient wrapper for running tunnel commands.

## Documentation

Documentation are located [here](https://cupang-afk.github.io/subprocess-tunnel/)

## Usage

This is not a module, instead, you can just download [tunnel.py](https://github.com/cupang-afk/subprocess-tunnel/blob/master/src/tunnel.py) and import it

```python
from tunnel import Tunnel

# Setting up the tunnel
wrapper = Tunnel(3000)  # Tunnel on port 3000
wrapper.add_tunnel(
    command="cloudflared tunnel --url http://localhost:{port}", # {port} automatically changed to 3000
    pattern=r"[\w-]+\.trycloudflare\.com",
    name="Cloudflare"
)

# Starting the tunnel
wrapper.start()

# Stopping the tunnel
wrapper.stop()

# Using a with block
with wrapper:
    pass

# Setting up tunnel with a list
tunnel_list = [
    {
        "command": "tunnel_1_cmd",
        "pattern": r"tunnel_1_pattern",
        "name": "tunnel_1"
    },
    {
        "command": "tunnel_2_cmd",
        "pattern": r"tunnel_1_pattern",
        "name": "tunnel_2"
    }
]
wrapper = Tunnel.with_tunnel_list(3000, tunnel_list)

wrapper.start()
```

## TODO

- [ ] -

---

Licensed under the terms of the MIT License. See the [LICENSE](https://github.com/cupang-afk/subprocess-tunnel/blob/master/LICENSE) file for details.
