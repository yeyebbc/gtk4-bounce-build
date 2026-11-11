#!/usr/bin/env python3
"""Combine tested amd64+i386 Debian packages with verified rollback packages."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "gtk3/source.json").read_text())
DIST = ROOT / "dist/gtk3-bounce-trixie-multiarch"

def metadata(path):
    fields = ("Package", "Version", "Architecture", "Source")
    return dict(zip(fields, (subprocess.check_output(
        ["dpkg-deb", "--field", str(path), field], text=True).strip() for field in fields)))

def main():
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    DIST.mkdir(parents=True, exist_ok=False)
    for directory in ("packages", "rollback", "provenance"):
        (DIST / directory).mkdir()
    records = []
    seen = set()
    for architecture in CONFIG["architectures"]:
        incoming = ROOT / "_gtk3/incoming" / ("gtk3-packages-" + architecture)
        assert (incoming / "provenance" / ("BUILD_COMMIT_" + architecture)).read_text().strip() == commit
        assert (incoming / "provenance" / ("validation-" + architecture + ".txt")).read_text().startswith("PASS:")
        for deb in sorted((incoming / "packages").glob("*.deb")):
            info = metadata(deb)
            assert info["Source"].split(" ")[0] == CONFIG["source"], info
            assert info["Version"] == CONFIG["version"], info
            assert info["Architecture"] in (architecture, "all"), info
            key = (info["Package"], info["Architecture"])
            assert key not in seen, key
            seen.add(key)
            original_name = f"{info['Package']}_{CONFIG['base_version']}_{info['Architecture']}.deb"
            original = incoming / "rollback" / original_name
            stock = metadata(original)
            assert stock["Package"] == info["Package"] and stock["Architecture"] == info["Architecture"], stock
            assert stock["Version"] == CONFIG["base_version"], stock
            rebuilt_relative = Path("packages") / deb.name
            stock_relative = Path("rollback") / original.name
            shutil.copyfile(deb, DIST / rebuilt_relative)
            shutil.copyfile(original, DIST / stock_relative)
            records.append({"name": info["Package"], "architecture": info["Architecture"],
                            "file": str(rebuilt_relative), "rollback_file": str(stock_relative)})
        provenance = DIST / "provenance" / architecture
        shutil.copytree(incoming / "provenance", provenance)
    required = {("libgtk-3-0t64", "amd64"), ("libgtk-3-0t64", "i386"),
                ("libgtk-3-common", "all"), ("libgtk-3-bin", "amd64"),
                ("libgail-3-0t64", "amd64"),
                ("gir1.2-gtk-3.0", "amd64")}
    assert required <= seen, required - seen
    manifest = {key: CONFIG[key] for key in
                ("source", "base_version", "version", "architecture", "debian_codename", "architectures")}
    manifest["packages"] = records
    (DIST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for name in ("manage.py", "install.sh", "rollback.sh"):
        shutil.copyfile(ROOT / "bundle" / name, DIST / name)
        (DIST / name).chmod(0o755)
    shutil.copyfile(ROOT / "gtk3/INSTALL.txt", DIST / "README.txt")
    for source, destination in (
        ("gtk3/source.json", "source.json"),
        ("gtk3/patches/gtk3-3.24.41-bounce.patch", "bounce.patch"),
        ("gtk3/test-bounce.c", "test-bounce.c"),
        ("gtk3/test-bounce.py", "test-bounce.py"),
    ):
        shutil.copyfile(ROOT / source, DIST / "provenance" / destination)
    info = {
        "commit": commit,
        "run_url": f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
        "validation": [
            "Debian packaging and strict GTK/GDK symbol checks",
            "Exported GTK/GDK ABI compared with stock on amd64 and i386",
            "24 stock and 24 patched native C smooth-scroll cases per architecture",
            "24 stock and 24 patched Python GI scroll cases on amd64",
            "Text/tree/viewport content, four edges, overlays, rebound, clipping and lifecycle",
            "Upstream scrolledwindow sizing tests against the .deb contents on both architectures",
        ],
        "build_profiles": CONFIG["build_profiles"],
        "full_test_suite": "Not run; focused tests run separately from nocheck Debian builds.",
        "physical_touchpad_test": "Manual validation required after installation.",
    }
    (DIST / "provenance/build.json").write_text(json.dumps(info, indent=2) + "\n")
    checksums = []
    for path in sorted(DIST.rglob("*")):
        if path.is_file():
            checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(DIST)}\n")
    (DIST / "SHA256SUMS").write_text("".join(checksums))
    print(f"Bundled {len(records)} patched packages and their original rollback packages in {DIST}")

if __name__ == "__main__":
    main()
