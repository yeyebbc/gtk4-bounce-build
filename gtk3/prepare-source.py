#!/usr/bin/env python3
"""Unpack the pinned Ubuntu source and apply the GTK 3 bounce patch."""
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

root = Path(__file__).resolve().parents[1]
config = json.loads((root / "gtk3/source.json").read_text())
downloads = root / "_gtk3/downloads"
downloads.mkdir(parents=True, exist_ok=True)
source = root / "_gtk3/source"
if source.exists():
    raise SystemExit("Refusing to overwrite existing source")
for filename, expected in config["files"].items():
    path = downloads / filename
    if not path.exists():
        with urllib.request.urlopen(config["archive"] + filename, timeout=120) as response:
            path.write_bytes(response.read())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, filename
    print("Verified SHA256:", filename, flush=True)
subprocess.run(["dpkg-source", "--no-check", "-x",
                str(downloads / ("gtk+3.0_" + config["base_version"] + ".dsc")), str(source)], check=True)
subprocess.run(["patch", "--batch", "--fuzz=0", "-p1", "-i",
                str(root / "gtk3/patches/gtk3-3.24.41-bounce.patch")], cwd=source, check=True)
