#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"
. /etc/os-release
[[ "$ID" == debian && "$VERSION_ID" == 13 && "$VERSION_CODENAME" == trixie ]]
arch=$(dpkg --print-architecture)
[[ "$arch" == amd64 || "$arch" == arm64 ]]
export DEB_BUILD_PROFILES='nodoc noinsttest noudeb'

python3 scripts/prepare-source.py
mkdir -p _build/deps
(
  cd _build/deps
  sudo mk-build-deps --install --remove \
    --build-profiles "${DEB_BUILD_PROFILES// /,}" \
    --tool 'apt-get --yes --no-install-recommends' ../gtk4/debian/control
)

jobs=$(nproc)
(( jobs <= 2 )) || jobs=2
(
  cd _build/gtk4
  # Keep Debian's build rules and ABI checks. Run focused tests below instead
  # of the full display/font/GPU-dependent X11 and Wayland test matrix.
  DEB_BUILD_OPTIONS="parallel=$jobs nocheck" dpkg-buildpackage -b -us -uc
)

# Verify the produced library and headers together, installed inside this CI
# runner. These commands never execute on the user's machine.
core_packages=(libgtk-4-1 libgtk-4-common libgtk-4-bin libgtk-4-dev libgtk-4-media-gstreamer gir1.2-gtk-4.0 gtk-update-icon-cache)
core_debs=()
for package in "${core_packages[@]}"; do
  matches=("$repo_dir/_build/${package}_"*.deb)
  [[ ${#matches[@]} == 1 && -f "${matches[0]}" ]]
  core_debs+=("${matches[0]}")
done
sudo apt-get --yes --no-remove --no-install-recommends install "${core_debs[@]}"
mkdir -p _build/test-config
cc -Wall -Wextra _build/gtk4/testsuite/gtk/scrolledwindow.c \
  -o _build/scrolledwindow $(pkg-config --cflags --libs gtk4)
env XDG_CONFIG_HOME="$repo_dir/_build/test-config" GDK_BACKEND=x11 GSK_RENDERER=cairo GTK_A11Y=none GSETTINGS_BACKEND=memory LIBGL_ALWAYS_SOFTWARE=1 \
  xvfb-run -a dbus-run-session -- _build/scrolledwindow --tap -k
cc -Wall -Wextra -Werror scripts/render-smoke.c -o _build/render-smoke $(pkg-config --cflags --libs gtk4)
env XDG_CONFIG_HOME="$repo_dir/_build/test-config" GDK_BACKEND=x11 GSK_RENDERER=cairo GTK_A11Y=none LIBGL_ALWAYS_SOFTWARE=1 \
  xvfb-run -a dbus-run-session -- _build/render-smoke

python3 scripts/bundle.py
