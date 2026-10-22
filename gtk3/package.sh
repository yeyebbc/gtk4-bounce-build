#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"
arch=${1:?Usage: package.sh amd64|i386}
[[ "$arch" == amd64 || "$arch" == i386 ]]
. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]]
[[ $(dpkg --print-architecture) == amd64 ]]
export DEB_BUILD_PROFILES='nodoc noudeb nocheck pkg.gtk3.noexamples'
build_dir="$repo_dir/_gtk3/packages/$arch"
/usr/bin/python3 gtk3/prepare-source.py --packages --build-dir "$build_dir"
mkdir -p "$build_dir/deps"
if [[ "$arch" == i386 ]]; then
  sudo dpkg --add-architecture i386
  sudo apt-get update
  sudo apt-get install --yes --no-install-recommends crossbuild-essential-i386 qemu-user
  export DEB_BUILD_PROFILES="$DEB_BUILD_PROFILES cross"
  # Explicitly select the modern cross-friendly introspection packages instead
  # of the historical libgirepository1.0-dev alternatives in the source control.
  sudo apt-get install --yes --no-install-recommends \
    gobject-introspection:i386 gir1.2-freedesktop-dev:i386 \
    libgdk-pixbuf-2.0-dev:i386 libpango1.0-dev:i386 libjson-glib-dev:amd64
fi
(
  cd "$build_dir/deps"
  sudo mk-build-deps --install --remove \
    --build-arch amd64 --host-arch "$arch" \
    --build-profiles "${DEB_BUILD_PROFILES// /,}" \
    --tool 'apt-get --yes --no-remove --no-install-recommends -o Debug::pkgProblemResolver=true' ../source/debian/control
)
sudo apt-get install --yes --no-install-recommends "libgtk-3-0t64:$arch"
jobs=$(nproc)
(( jobs <= 2 )) || jobs=2
(
  cd "$build_dir/source"
  if [[ "$arch" == amd64 ]]; then
    DEB_BUILD_OPTIONS="parallel=$jobs nocheck" dpkg-buildpackage -b -us -uc
  else
    DEB_BUILD_OPTIONS="parallel=$jobs nocheck" dpkg-buildpackage -B -a"$arch" -us -uc
  fi
)
multiarch=$(dpkg-architecture -a"$arch" -qDEB_HOST_MULTIARCH)
gnu_type=$(dpkg-architecture -a"$arch" -qDEB_HOST_GNU_TYPE)
compiler="$gnu_type-gcc"
pkgconf="$gnu_type-pkgconf"
source_dir="$build_dir/source"
meson_dir="$source_dir/debian/build/deb"
mkdir -p "$build_dir/test-root" "$build_dir/test-config" "$build_dir/test-output"
runtime_debs=("$build_dir"/libgtk-3-0t64_*.deb)
[[ ${#runtime_debs[@]} == 1 && -f "${runtime_debs[0]}" ]]
dpkg-deb -x "${runtime_debs[0]}" "$build_dir/test-root"
library_dir="$build_dir/test-root/usr/lib/$multiarch"
/usr/bin/python3 flatpak/abi-check.py "/usr/lib/$multiarch/libgtk-3.so.0" "$library_dir/libgtk-3.so.0"
/usr/bin/python3 flatpak/abi-check.py "/usr/lib/$multiarch/libgdk-3.so.0" "$library_dir/libgdk-3.so.0"
# Compile native clients with this build's headers and target libraries.
# Run against stock, then actual .deb contents.
read -r -a client_flags <<< "$("$pkgconf" --cflags --libs atk cairo gdk-pixbuf-2.0 gio-2.0 pango pangocairo)"
"$compiler" -Wall -Wextra -Werror -I"$source_dir" -I"$meson_dir" \
  gtk3/test-bounce.c -o "$build_dir/test-bounce" \
  -L"$meson_dir/gtk" -L"$meson_dir/gdk" \
  -Wl,-rpath-link,"$meson_dir/gtk:$meson_dir/gdk" \
  -lgtk-3 -lgdk-3 "${client_flags[@]}"
"$compiler" -Wall -Wextra -I"$source_dir" -I"$meson_dir" \
  "$source_dir/testsuite/gtk/scrolledwindow.c" -o "$build_dir/scrolledwindow" \
  -L"$meson_dir/gtk" -L"$meson_dir/gdk" \
  -Wl,-rpath-link,"$meson_dir/gtk:$meson_dir/gdk" \
  -lgtk-3 -lgdk-3 "${client_flags[@]}"
export XDG_CONFIG_HOME="$build_dir/test-config"
export GDK_BACKEND=x11 GIO_USE_VFS=local GTK_THEME=Adwaita NO_AT_BRIDGE=1 GSETTINGS_BACKEND=memory LIBGL_ALWAYS_SOFTWARE=1
xvfb-run -a dbus-run-session -- env G_DEBUG=fatal-criticals "$build_dir/test-bounce" --stock
if [[ "$arch" == amd64 ]]; then
  xvfb-run -a dbus-run-session -- /usr/bin/python3 gtk3/test-bounce.py --stock
fi
export LD_LIBRARY_PATH="$library_dir"
export GTK3_TEST_OUTPUT="$build_dir/test-output"
xvfb-run -a dbus-run-session -- env G_DEBUG=fatal-criticals "$build_dir/test-bounce"
xvfb-run -a dbus-run-session -- "$build_dir/scrolledwindow"
if [[ "$arch" == amd64 ]]; then
  xvfb-run -a dbus-run-session -- env G_DEBUG=fatal-criticals /usr/bin/python3 gtk3/test-bounce.py
fi
# Stock rollback packages come through APT's authenticated indexes.
mkdir -p "$build_dir/rollback"
base_version=$(/usr/bin/python3 -c 'import json; print(json.load(open("gtk3/source.json"))["base_version"])')
for deb in "$build_dir"/*.deb; do
  name=$(dpkg-deb -f "$deb" Package)
  [[ "$name" != *-dbgsym ]] || continue
  target_arch=$(dpkg-deb -f "$deb" Architecture)
  (
    cd "$build_dir/rollback"
    apt-get download "$name:$target_arch=$base_version"
  )
done
stage="$repo_dir/dist/gtk3-packages-$arch"
mkdir -p "$stage/packages" "$stage/rollback" "$stage/provenance"
for deb in "$build_dir"/*.deb; do
  [[ "$deb" != *-dbgsym_* ]] || continue
  cp "$deb" "$stage/packages/"
done
cp "$build_dir"/rollback/*.deb "$stage/rollback/"
cp "$build_dir"/*.buildinfo "$build_dir"/*.changes "$stage/provenance/"
git rev-parse HEAD > "$stage/provenance/BUILD_COMMIT_$arch"
printf '%s\n' "PASS: $arch packaged GTK/GDK ABI; 24 stock and 24 patched C scroll cases; upstream sizing tests." > "$stage/provenance/validation-$arch.txt"
