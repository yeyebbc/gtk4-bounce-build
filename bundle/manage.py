#!/usr/bin/env python3
"""Install or roll back only GTK packages already installed on this machine."""

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def fail(message):
    sys.exit(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("install", "rollback"))
    parser.add_argument("--dry-run", action="store_true", help="Ask APT to simulate the transaction")
    args = parser.parse_args()

    for line in (ROOT / "SHA256SUMS").read_text().splitlines():
        expected, filename = line.split("  ", 1)
        path = (ROOT / filename).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            fail(f"Missing or invalid bundle file: {filename}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            fail(f"Checksum mismatch: {filename}")
    manifest = json.loads((ROOT / "manifest.json").read_text())
    architecture = subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip()
    if architecture != manifest["architecture"]:
        fail(f"This bundle requires {manifest['architecture']}; this machine is {architecture}.")
    release = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            release[key] = value.strip('"')
    codename = release.get("VERSION_CODENAME")
    if (release.get("ID") != "debian" or release.get("VERSION_ID") != "13"
            or codename != manifest["debian_codename"]):
        fail(f"This bundle targets Debian 13 (trixie); found {release.get('PRETTY_NAME', codename)!r}.")

    format_string = "${Package}\t${Architecture}\t${Version}\t${source:Package}\t${db:Status-Status}\n"
    installed = subprocess.check_output(["dpkg-query", "-W", "-f=" + format_string], text=True)
    available = {(p["name"], p["architecture"]): p for p in manifest["packages"]}
    selected = []
    for line in installed.splitlines():
        name, arch, version, source, status = line.split("\t")
        if source != manifest["source"] or status != "installed":
            continue
        if args.mode == "rollback" and version != manifest["version"]:
            continue
        package = available.get((name, arch))
        if package is None:
            fail(f"No matching package for installed {name}:{arch}. Do not mix GTK architectures/builds.")
        if version not in (manifest["base_version"], manifest["version"]):
            fail(f"Installed {name} is {version}; this bundle targets {manifest['base_version']}. Rebuild for that version.")
        filename = package["file" if args.mode == "install" else "rollback_file"]
        path = ROOT / filename
        expected_version = manifest["version" if args.mode == "install" else "base_version"]
        for field, expected in (("Package", name), ("Version", expected_version), ("Architecture", arch)):
            actual = subprocess.check_output(["dpkg-deb", "--field", str(path), field], text=True).strip()
            if actual != expected:
                fail(f"Package metadata mismatch in {filename}: {field}={actual}")
        selected.append(str(path))
    if not selected:
        fail("No matching GTK packages need this operation.")
    print(f"{args.mode.capitalize()} {len(selected)} currently installed GTK packages:", flush=True)
    for path in selected:
        print(f"  {Path(path).name}", flush=True)
    command = ["apt-get", "--no-remove", "--no-install-recommends"]
    if args.dry_run:
        command.append("--simulate")
    if args.mode == "rollback":
        command.append("--allow-downgrades")
    command += ["install", "--reinstall", *selected]
    if os.geteuid() != 0 and not args.dry_run:
        command.insert(0, "sudo")
    print(shlex.join(command), flush=True)
    subprocess.run(command, check=True)
    if not args.dry_run:
        print("Done. Log out and back in, or reboot, so all applications load the installed GTK.")


if __name__ == "__main__":
    main()
