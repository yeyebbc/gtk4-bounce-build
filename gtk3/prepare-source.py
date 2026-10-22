#!/usr/bin/env python3
"""Unpack pinned Ubuntu source; optionally prepare native Debian packaging."""
import argparse
from datetime import datetime, timezone
from email.utils import format_datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

root = Path(__file__).resolve().parents[1]
config = json.loads((root / "gtk3/source.json").read_text())
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--packages", action="store_true")
parser.add_argument("--build-dir", type=Path, default=root / "_gtk3")
args = parser.parse_args()
downloads = root / "_gtk3/downloads"
downloads.mkdir(parents=True, exist_ok=True)
source = args.build_dir.resolve() / "source"
if source.exists():
    raise SystemExit("Refusing to overwrite existing source: " + str(source))
source.parent.mkdir(parents=True, exist_ok=True)
for filename, expected in config["files"].items():
    path = downloads / filename
    if not path.exists():
        with urllib.request.urlopen(config["archive"] + filename, timeout=120) as response:
            path.write_bytes(response.read())
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit("SHA256 mismatch: " + filename)
    print("Verified SHA256:", filename, flush=True)
subprocess.run(["dpkg-source", "--no-check", "-x",
                str(downloads / ("gtk+3.0_" + config["base_version"] + ".dsc")), str(source)], check=True)
patch = root / "gtk3/patches/gtk3-3.24.41-bounce.patch"
subprocess.run(["patch", "--dry-run", "--batch", "--fuzz=0", "-p1", "-i",
                str(patch)], cwd=source, check=True)
if not args.packages:
    subprocess.run(["patch", "--batch", "--fuzz=0", "-p1", "-i", str(patch)], cwd=source, check=True)
else:
    shutil.copyfile(patch, source / "debian/patches/gtk3-bounce.patch")
    series = source / "debian/patches/series"
    series.write_text(series.read_text().rstrip() + "\ngtk3-bounce.patch\n")
    subprocess.run(["dpkg-source", "--before-build", str(source)], check=True)
    control = source / "debian/control"
    marker = "Package: gtk-3-examples\n"
    assert control.read_text().count(marker) == 1
    text = control.read_text().replace(marker, marker + "Build-Profiles: <!pkg.gtk3.noexamples>\n")
    # Ubuntu's architecture-independent translation helper lacks Multi-Arch:
    # foreign, so cross builds must explicitly request the native tool.
    text = text.replace("dh-sequence-translations,", "dh-sequence-translations:native,")
    control.write_text(text)
    rules = source / "debian/rules"
    rules.write_text(rules.read_text() + "\n# CI runs focused tests against the packaged library.\n"
                     "configure_flags_deb += -Dinstalled_tests=false -Dtests=false -Ddemos=false -Dexamples=false\n")
    changelog = source / "debian/changelog"
    # Both Multi-Arch builds must ship byte-identical shared documentation.
    epoch = int(subprocess.check_output(["git", "show", "-s", "--format=%ct", "HEAD"], cwd=root, text=True))
    date = datetime.fromtimestamp(epoch, timezone.utc)
    entry = (
        f"gtk+3.0 ({config['version']}) noble; urgency=medium\n\n"
        "  * Port Christian Hergert's GtkScrolledWindow bounce scrolling to GTK 3.\n"
        "  * Preserve Ubuntu patches, runtime backends, package layout and ABI checks.\n"
        "  * Omit docs, installer udebs and examples; run focused tests in CI.\n\n"
        f" -- GTK Bounce Builder <builder@localhost>  {format_datetime(date)}\n\n"
    )
    changelog.write_text(entry + changelog.read_text())
print("Prepared source:", source, flush=True)
