#!/usr/bin/env python3
"""Run the verified CI bundle's helper with the project's local app registry."""
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "installed/gtk4-bounce-gnome50-x86_64/manage.py"

def main():
    if not HELPER.is_file():
        raise SystemExit("Extract the CI bundle into installed/ first.")
    apps = json.loads((ROOT / "flatpak-apps.json").read_text())
    if not isinstance(apps, list) or not all(isinstance(app, str) and "." in app for app in apps):
        raise SystemExit("flatpak-apps.json must contain a list of Flatpak app IDs.")
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("gtk_bounce_bundle", HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    # Extend only app selection. The original artifact, library checksums,
    # runtime/source checks, backup and restore behavior remain in the CI helper.
    helper.CONFIG["apps"] = list(dict.fromkeys(helper.CONFIG["apps"] + apps))
    helper.main()

if __name__ == "__main__":
    main()
