#!/usr/bin/env bash
# Run as the project owner, after installing the GPU driver and python3-venv.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$HOME/.local/bin" "$HOME/.local/opt" runs/setup

python3 -m venv "$HOME/.local/opt/yixian-bootstrap"
"$HOME/.local/opt/yixian-bootstrap/bin/python" -m pip install --disable-pip-version-check --index-url https://mirrors.tencentyun.com/pypi/simple 'uv==0.13.7'
UV="$HOME/.local/opt/yixian-bootstrap/bin/uv"
"$UV" python install 3.14
if [ ! -x .venv/bin/python ]; then
    "$UV" venv --python 3.14 .venv
fi

# Node's official archive is checked against its published SHA-256 manifest.
python3 - <<'PY'
import hashlib
from pathlib import Path
import tarfile
import urllib.request

version = 'v22.23.4'
name = f'node-{version}-linux-x64'
filename = name + '.tar.xz'
base = f'https://nodejs.org/dist/{version}/'
home = Path.home()
destination = home / '.local/opt' / name
if not (destination / 'bin/node').is_file():
    with urllib.request.urlopen(base + 'SHASUMS256.txt', timeout=60) as response:
        hashes = dict((row.split()[1], row.split()[0]) for row in response.read().decode().splitlines())
    archive = home / '.local/opt' / filename
    with urllib.request.urlopen(base + filename, timeout=90) as response, archive.open('wb') as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != hashes[filename]:
        raise RuntimeError('Official Node.js archive checksum mismatch')
    with tarfile.open(archive) as source:
        source.extractall(home / '.local/opt', filter='data')
    archive.unlink()
for executable in ('node', 'npm', 'npx'):
    link = home / '.local/bin' / executable
    expected = destination / 'bin' / executable
    if link.is_symlink() and link.resolve() == expected.resolve():
        continue
    if link.exists() or link.is_symlink():
        raise RuntimeError(f'Existing executable is not the selected Node version: {link}')
    link.symlink_to(expected)
PY

# Tencent's HTTPS PyPI mirror avoids the slow overseas package download path.
# Keep the release pinned; verify the installed CUDA runtime on the actual GPU.
"$UV" pip install --python .venv/bin/python --index-url https://mirrors.tencentyun.com/pypi/simple -r requirements-gpu.txt
.venv/bin/python tools/setup_yisim.py
"$UV" pip freeze --python .venv/bin/python > runs/setup/packages.lock.txt
.venv/bin/python --version
node --version
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
printf 'CLOUD_BOOTSTRAP_COMPLETE\n'
