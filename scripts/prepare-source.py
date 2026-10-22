#!/usr/bin/env python3
"""Fetch the pinned Ubuntu source and append the bounce backport to its series."""

import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "source.json").read_text())
BUILD = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "_build"
DOWNLOADS = BUILD / "downloads"
SOURCE = BUILD / "gtk4"


def main():
    if SOURCE.exists():
        sys.exit(f"Refusing to overwrite existing source: {SOURCE}")
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    for filename, expected in CONFIG["files"].items():
        destination = DOWNLOADS / filename
        if not destination.exists():
            with urllib.request.urlopen(CONFIG["archive"] + filename, timeout=120) as response:
                destination.write_bytes(response.read())
        actual = hashlib.sha256(destination.read_bytes()).hexdigest()
        if actual != expected:
            sys.exit(f"SHA256 mismatch for {filename}: {actual}")
        print(f"Verified SHA256: {filename}", flush=True)

    dsc = DOWNLOADS / f"gtk4_{CONFIG['base_version']}.dsc"
    # Every input, including the .dsc, has been checked against pinned SHA256s.
    # This avoids requiring a particular Ubuntu signing key in a fresh runner.
    subprocess.run(["dpkg-source", "--no-check", "-x", str(dsc), str(SOURCE)], check=True)
    patch = ROOT / "patches/bounce-gtk-4.14.5.patch"
    subprocess.run(
        ["patch", "--dry-run", "--batch", "--fuzz=0", "-p1", "-i", str(patch)],
        cwd=SOURCE, check=True,
    )
    shutil.copyfile(patch, SOURCE / "debian/patches/bounce-gtk-4.14.5.patch")
    series = SOURCE / "debian/patches/series"
    series.write_text(series.read_text().rstrip() + "\nbounce-gtk-4.14.5.patch\n")
    subprocess.run(["dpkg-source", "--before-build", str(SOURCE)], check=True)

    changelog = SOURCE / "debian/changelog"
    entry = (
        f"gtk4 ({CONFIG['version']}) noble; urgency=medium\n\n"
        "  * Backport Christian Hergert's GtkScrolledWindow bounce scrolling patch.\n"
        "  * Preserve the Ubuntu source, existing patch series and package layout.\n\n"
        f" -- Local GTK Builder <builder@localhost>  {format_datetime(datetime.now(timezone.utc))}\n\n"
    )
    changelog.write_text(entry + changelog.read_text())
    print(f"Prepared {SOURCE} at version {CONFIG['version']}", flush=True)


if __name__ == "__main__":
    main()
