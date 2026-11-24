#!/usr/bin/env python3
"""Bundle rebuilt binary packages, their exact stock counterparts and helpers."""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "source.json").read_text())
CORE = {"libgtk-4-1", "libgtk-4-common", "libgtk-4-bin", "libgtk-4-dev",
        "libgtk-4-media-gstreamer", "gir1.2-gtk-4.0", "gtk-update-icon-cache"}


def metadata(path):
    fields = ["Package", "Version", "Architecture", "Source"]
    return dict(zip(fields, (
        subprocess.check_output(["dpkg-deb", "--field", str(path), field], text=True).strip()
        for field in fields
    )))


def main():
    architecture = subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip()
    assert architecture in ("amd64", "arm64"), architecture
    dist = ROOT / "dist" / f"gtk4-bounce-trixie-{architecture}"
    dist.mkdir(parents=True, exist_ok=False)
    (dist / "packages").mkdir()
    (dist / "rollback").mkdir()
    records = []
    for deb in sorted((ROOT / "_build").glob("*.deb")):
        info = metadata(deb)
        if info["Source"].split(" ")[0] != "gtk4" or info["Package"].endswith("-dbgsym"):
            continue
        assert info["Version"] == CONFIG["version"], info
        assert info["Architecture"] in ("all", architecture), info
        relative = Path("packages") / deb.name
        shutil.copyfile(deb, dist / relative)
        subprocess.run(["apt-get", "download", f"{info['Package']}={CONFIG['base_version']}"],
                       cwd=dist / "rollback", check=True)
        originals = list((dist / "rollback").glob(f"{info['Package']}_*.deb"))
        assert len(originals) == 1, info
        stock = metadata(originals[0])
        assert stock["Version"] == CONFIG["base_version"], stock
        assert stock["Architecture"] == info["Architecture"], stock
        records.append({"name": info["Package"], "architecture": info["Architecture"],
                        "file": str(relative), "rollback_file": str(originals[0].relative_to(dist))})
    assert CORE <= {record["name"] for record in records}, records
    manifest = {key: CONFIG[key] for key in
                ("source", "base_version", "version", "debian_codename")}
    manifest["architecture"] = architecture
    manifest["packages"] = records
    (dist / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for helper in (ROOT / "bundle").iterdir():
        if helper.is_file():
            shutil.copyfile(helper, dist / helper.name)
    provenance = dist / "provenance"
    provenance.mkdir()
    shutil.copyfile(ROOT / "source.json", provenance / "source.json")
    shutil.copyfile(ROOT / "patches/bounce-gtk-4.14.5.patch", provenance / "bounce.patch")
    for pattern in ("*.buildinfo", "*.changes"):
        for path in (ROOT / "_build").glob(pattern):
            shutil.copyfile(path, provenance / path.name)
    info = {
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "run_url": f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
        "validation": ["Debian packaging and ABI checks", "upstream scrolledwindow tests against installed library under Xvfb",
                       "installed library rendering/scroll-boundary smoke test"],
        "build_profiles": CONFIG["build_profiles"],
        "full_test_suite": "not run; dpkg build uses nocheck and focused tests run separately",
        "physical_touchpad_test": "requires manual testing after installation",
    }
    (provenance / "build.json").write_text(json.dumps(info, indent=2) + "\n")
    checksums = []
    for path in sorted(dist.rglob("*")):
        if path.is_file():
            checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(dist)}\n")
    (dist / "SHA256SUMS").write_text("".join(checksums))
    print(f"Bundled {len(records)} rebuilt packages and their stock rollback packages in {dist}")


if __name__ == "__main__":
    main()
