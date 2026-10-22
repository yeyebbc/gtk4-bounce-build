#!/usr/bin/env python3
"""Package only the patched core library, provenance and override helpers."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

root = Path(__file__).resolve().parents[1]
config = json.loads((root / "flatpak/source.json").read_text())
name = "gtk4-bounce-gnome50-x86_64"
bundle = root / "dist" / name
bundle.mkdir(parents=True, exist_ok=False)
(bundle / "lib").mkdir()
shutil.copy2(root / "_flatpak/app/files/lib/gtk-bounce" / config["library"],
             bundle / "lib" / config["library"])
(bundle / "lib/libgtk-4.so.1").symlink_to(config["library"])
for path in (root / "flatpak/bundle").iterdir():
    if path.is_file():
        shutil.copy2(path, bundle / path.name)
provenance = bundle / "provenance"
provenance.mkdir()
for filename in ("source.json", "build.json", "bounce.patch"):
    shutil.copy2(root / "flatpak" / filename, provenance / filename)
shutil.copy2(root / "_flatpak/app/files/share/licenses/gtk-bounce/COPYING", bundle / "COPYING")
config["git_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
(provenance / "bundle.json").write_text(json.dumps(config, indent=2) + "\n")
checksums = []
for path in sorted(bundle.rglob("*")):
    if path.is_file() and not path.is_symlink():
        checksums.append(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + str(path.relative_to(bundle)))
(bundle / "SHA256SUMS").write_text("\n".join(checksums) + "\n")
destination = root / "dist" / (name + ".tar.gz")
with tarfile.open(destination, "w:gz") as archive:
    archive.add(bundle, arcname=name)
print("Bundled", destination, destination.stat().st_size, "bytes")
