#!/usr/bin/env python3
"""Enable/verify/restore narrowly scoped user overrides for a matching runtime."""
import argparse
import base64
import configparser
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "provenance/bundle.json").read_text())
STATE = ROOT / "override-state.json"
OVERRIDES = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "flatpak/overrides"

def run(*args):
    return subprocess.check_output(args, text=True).strip()

def parser(text):
    value = configparser.ConfigParser(interpolation=None, strict=False)
    value.optionxform = str
    value.read_string(text)
    return value

def digest(data):
    return hashlib.sha256(data).hexdigest()

def verify_bundle():
    for line in (ROOT / "SHA256SUMS").read_text().splitlines():
        expected, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.resolve().is_relative_to(ROOT) or digest(path.read_bytes()) != expected:
            raise SystemExit("Bundle checksum failed: " + relative)
    link = ROOT / "lib/libgtk-4.so.1"
    if not link.is_symlink() or os.readlink(link) != CONFIG["library"]:
        raise SystemExit("Unexpected GTK library symlink")
    print("PASS: bundle checksums")

def check_app(app):
    actual = run("flatpak", "info", "--show-runtime", app)
    if actual != CONFIG["runtime"]:
        raise SystemExit(f"{app}: runtime {actual} differs from {CONFIG['runtime']}")
    location = Path(run("flatpak", "info", "--show-location", actual))
    manifest = json.loads((location / "files/manifest.json").read_text())
    gtk = next(module for module in manifest["modules"] if module.get("name") == "sdk/gtk.bst")
    sources = gtk.get("sources", [])
    if not any(source.get("sha256") == CONFIG["source_sha256"] for source in sources):
        raise SystemExit(f"{app}: runtime GTK changed; rebuild the bundle before enabling it.")
    print(f"PASS: {app} matches GTK {CONFIG['gtk_version']} / GNOME 50")

def effective_library_path(app):
    value = "/app/lib"
    metadata = parser(run("flatpak", "info", "--show-metadata", app))
    if metadata.has_option("Environment", "LD_LIBRARY_PATH"):
        value = metadata.get("Environment", "LD_LIBRARY_PATH")
    for scope in ("--system", "--user"):
        for target in ((), (app,)):
            overrides = parser(run("flatpak", "override", scope, "--show", *target))
            if overrides.has_option("Environment", "LD_LIBRARY_PATH"):
                value = overrides.get("Environment", "LD_LIBRARY_PATH")
    return value

def save_state(state):
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    temporary.replace(STATE)

def restore(app, item):
    path = OVERRIDES / app
    if item["before"] is None:
        path.unlink(missing_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".gtk-bounce-tmp")
        temporary.write_bytes(base64.b64decode(item["before"]))
        temporary.replace(path)

def verify_loaded(app):
    code = """import ctypes, json, pathlib, sys
gtk = ctypes.CDLL("libgtk-4.so.1")
version = ".".join(str(getattr(gtk, "gtk_get_" + part + "_version")()) for part in ("major", "minor", "micro"))
assert version == sys.argv[2], version
paths = {line.split()[-1] for line in pathlib.Path("/proc/self/maps").read_text().splitlines() if "libgtk-4.so" in line}
assert any(path.startswith(sys.argv[1] + "/") for path in paths), paths
ctypes.CDLL("libadwaita-1.so.0")
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
assert Gtk.get_micro_version() == gtk.gtk_get_micro_version()
print(json.dumps({"gtk": version, "loaded_library": sorted(paths), "libadwaita": "OK", "introspection": "OK"}))
"""
    print(app + ": " + run("flatpak", "run", "--command=python3", app,
                          "-c", code, str(ROOT / "lib"), CONFIG["gtk_version"]))

def main():
    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument("action", choices=("install", "rollback", "verify", "status"))
    argparser.add_argument("--dry-run", action="store_true")
    argparser.add_argument("apps", nargs="*", choices=CONFIG["apps"])
    args = argparser.parse_args()
    if os.geteuid() == 0:
        raise SystemExit("Run this as your desktop user, without sudo.")
    state = json.loads(STATE.read_text()) if STATE.exists() else {"bundle": str(ROOT), "apps": {}}
    if state["bundle"] != str(ROOT):
        raise SystemExit("The active bundle was moved; restore it to " + state["bundle"])
    apps = args.apps or (list(state["apps"]) if args.action == "rollback" else CONFIG["apps"])
    if args.action == "rollback":
        for app in apps:
            item = state["apps"].get(app)
            if item is None:
                continue
            path = OVERRIDES / app
            current = path.read_bytes() if path.exists() else b""
            if item["after_sha256"] is None or digest(current) != item["after_sha256"]:
                raise SystemExit(f"{app}: overrides were edited after installation; refusing to overwrite newer settings.")
        for app in apps:
            item = state["apps"].get(app)
            if item is not None:
                print("Restore original user overrides:", app)
                if not args.dry_run:
                    restore(app, item)
                    del state["apps"][app]
        if not args.dry_run:
            if state["apps"]:
                save_state(state)
            else:
                STATE.unlink(missing_ok=True)
        return
    verify_bundle()
    for app in apps:
        check_app(app)
    if args.action == "status":
        print("Enabled apps:", ", ".join(state["apps"]) or "(none)")
        return
    if args.action == "verify":
        for app in apps:
            verify_loaded(app)
        return
    for app in apps:
        if app in state["apps"]:
            current = (OVERRIDES / app).read_bytes()
            if digest(current) != state["apps"][app]["after_sha256"]:
                raise SystemExit(f"{app}: existing GTK override state differs; inspect it before reinstalling.")
            continue
        previous = effective_library_path(app)
        library_path = str(ROOT / "lib") + (":" + previous if previous else "")
        command = ["flatpak", "override", "--user", "--filesystem=" + str(ROOT) + ":ro",
                   "--env=LD_LIBRARY_PATH=" + library_path, app]
        print("Enable patched GTK:", app, flush=True)
        if args.dry_run:
            print("  " + " ".join(command))
            continue
        path = OVERRIDES / app
        before = path.read_bytes() if path.exists() else None
        state["apps"][app] = {"before": base64.b64encode(before).decode() if before is not None else None,
                              "after_sha256": None}
        save_state(state)
        try:
            subprocess.run(command, check=True)
            state["apps"][app]["after_sha256"] = digest(path.read_bytes())
            save_state(state)
            verify_loaded(app)
        except BaseException:
            restore(app, state["apps"][app])
            del state["apps"][app]
            save_state(state)
            raise
    if not args.dry_run:
        print("Enabled. Restart these applications to use the patched GTK. Use rollback to restore their saved overrides.")

if __name__ == "__main__":
    main()
