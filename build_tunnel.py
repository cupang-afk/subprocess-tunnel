import argparse
import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--no-test", dest="no_test", action="store_true", default=False)
args = parser.parse_args()

cwd = Path.cwd()
tunnel = cwd / "src/tunnel.py"


@contextlib.contextmanager
def workdir(dir: str):
    _cwd = os.getcwd()
    os.chdir(dir)
    try:
        yield
    finally:
        os.chdir(_cwd)


if not args.no_test:
    print("Run Test")
    import importlib.util

    if not importlib.util.find_spec("pytest"):
        print("pytest not found, install it first or run with --no-test")
        sys.exit(1)
    if not importlib.util.find_spec("pytest_mock"):
        print("pytest-mock not found, install it first or run with --no-test")
        sys.exit(1)

    try:
        subprocess.check_call([sys.executable, "-m", "pytest"])
    except subprocess.CalledProcessError as e:
        print(e)
        sys.exit(e.returncode)

with tempfile.TemporaryDirectory() as tmp_dir:
    print("Build")
    import importlib.util

    if not importlib.util.find_spec("cloudpickle"):
        print("cloudpickle not found, install it first or run with --no-test")
        sys.exit(1)

    tmp_dir = Path(tmp_dir)
    tunnel_pkl = tunnel.with_suffix(".pkl")
    shutil.copy(tunnel.absolute(), tmp_dir)
    with workdir(tmp_dir):
        subprocess.run([sys.executable, tunnel.name])
    print(f"Copy {tmp_dir / tunnel_pkl.name} to {cwd / tunnel_pkl.name}")
    shutil.copy(tmp_dir / tunnel_pkl.name, cwd / tunnel_pkl.name)
