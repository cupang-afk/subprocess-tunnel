# python tunnel

This Python package provides a convenient wrapper for running tunnel commands.

## Documentation

Documentation are located [here](https://cupang-afk.github.io/subprocess-tunnel/)

## Usage

This is not a module, instead, you can just download [tunnel.py](https://github.com/cupang-afk/subprocess-tunnel/blob/master/src/tunnel.py) and import it

you need atleast python 3.8

```python
from tunnel import Tunnel

# Setting up the tunnel
tunnel = Tunnel(3000)  # Tunnel on port 3000
tunnel.add_tunnel(
    command="cloudflared tunnel --url http://localhost:{port}", # {port} automatically changed to 3000
    pattern=r"[\w-]+\.trycloudflare\.com",
    name="Cloudflare"
)

# Starting the tunnel
tunnel.start()

# Stopping the tunnel
tunnel.stop()

# Using a with block
with tunnel:
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
tunnel = Tunnel.with_tunnel_list(3000, tunnel_list)

tunnel.start()
```

## Logger Propagate

by default `propagate` is `False` when initializing `Tunnel`

meaning the logger for `Tunnel` is detached from root logger

you can set to `True` to propagate log message to root logger, to use root logger message format, etc

```python
tunnel = Tunnel(3000, propagate=True)
```

## Callback

since version 0.1.0 `Tunnel` now has 2 callback

set it up when initializing `Tunnel`
or when adding tunnel `Tunnel.add_tunnel`

example

```python
def print_callback(urls: list[tuple[str, str | None]]) -> None:
    print(urls)
def regex_callback(url: str, note: str | None) -> None:
    print(url, note)

tunnel = Tunnel(3000, callback=print_callback)
tunnel.add_tunnel(command=..., pattern=..., name=..., callback=regex_callback)

with tunnel:
    # code goes here
```

in code above, difference between `print_callback` and `regex_callback` is

- `print_callback` executed after all the URLs is printed. will retrive a list of `tuple(url, note)`
- `regex_callback` executed after regex pattern is matched to URL (before print happen). will retrive `url: str` and `note: str | None`

example usage is to set callback to send the urls using discord webhook maybe ?

## TODO

- [ ] fixing stuff, adding stuff idk

## Personal Note

well, in 23 Feb 2024, i accidentaly force push to the repo which overwrite the date of the commit

but the project still work, so whatever

for the future me, **DO NOT USE `git push -f`** for whatever reason

---

Licensed under the terms of the MIT License. See the [LICENSE](https://github.com/cupang-afk/subprocess-tunnel/blob/master/LICENSE) file for details.
