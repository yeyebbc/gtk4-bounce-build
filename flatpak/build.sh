#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"
[[ $(uname -m) == x86_64 ]]
mkdir -p _flatpak
flatpak-builder --user --disable-rofiles-fuse --force-clean --keep-build-dirs \
  --state-dir=_flatpak/state _flatpak/app flatpak/build.json

# The SDK does the compiling; execute the resulting tests in the pinned
# Platform runtime, matching the environment used by the user's applications.
for test_binary in scrolledwindow gtk-bounce-smoke; do
  xvfb-run -a dbus-run-session -- flatpak build --runtime --readonly \
    --socket=x11 --share=ipc \
    --env=LD_LIBRARY_PATH=/app/lib/gtk-bounce:/app/lib \
    --env=GTK_BOUNCE_EXPECT_PATH=/app/lib/gtk-bounce \
    --env=XDG_CONFIG_HOME=/tmp/gtk-bounce-test-config \
    --env=GDK_BACKEND=x11 --env=GSK_RENDERER=cairo \
    --env=GTK_A11Y=none --env=GSETTINGS_BACKEND=memory \
    --env=LIBGL_ALWAYS_SOFTWARE=1 \
    _flatpak/app "/app/bin/$test_binary"
done
python3 flatpak/bundle.py
