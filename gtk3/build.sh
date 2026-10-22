#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"
/usr/bin/python3 gtk3/prepare-source.py
meson setup _gtk3/build _gtk3/source \
  --prefix=/usr --libdir=lib/x86_64-linux-gnu --buildtype=release \
  -Dx11_backend=true -Dwayland_backend=true -Dbroadway_backend=true \
  -Dintrospection=false -Dgtk_doc=false -Dman=false \
  -Dcolord=yes -Dcloudproviders=false -Dprint_backends=cups,file \
  -Ddemos=false -Dexamples=false -Dtests=false -Dinstalled_tests=false
meson compile -C _gtk3/build -j2 gtk-3
mkdir -p _gtk3/test-config _gtk3/test-output
export XDG_CONFIG_HOME="$repo_dir/_gtk3/test-config"
export GDK_BACKEND=x11 GIO_USE_VFS=local GTK_THEME=Adwaita NO_AT_BRIDGE=1 GSETTINGS_BACKEND=memory LIBGL_ALWAYS_SOFTWARE=1
export GTK3_TEST_OUTPUT="$repo_dir/_gtk3/test-output"

# Verify the same scroll events do not move content with the stock library.
xvfb-run -a dbus-run-session -- /usr/bin/python3 gtk3/test-bounce.py --stock
export LD_LIBRARY_PATH="$repo_dir/_gtk3/build/gtk:$repo_dir/_gtk3/build/gdk"
# Confirm real event handling, fixed scrollbars, clipping, rebound and lifecycle.
xvfb-run -a dbus-run-session -- env G_DEBUG=fatal-criticals /usr/bin/python3 gtk3/test-bounce.py
/usr/bin/python3 flatpak/abi-check.py /usr/lib/x86_64-linux-gnu/libgtk-3.so.0 _gtk3/build/gtk/libgtk-3.so
cc -Wall -Wextra _gtk3/source/testsuite/gtk/scrolledwindow.c \
  -o _gtk3/scrolledwindow $(pkg-config --cflags --libs gtk+-3.0)
xvfb-run -a dbus-run-session -- _gtk3/scrolledwindow
mkdir -p dist/gtk3-bounce-3.24.41
cp gtk3/patches/gtk3-3.24.41-bounce.patch gtk3/README.md gtk3/source.json dist/gtk3-bounce-3.24.41/
cp gtk3/test-bounce.py dist/gtk3-bounce-3.24.41/
git rev-parse HEAD > dist/gtk3-bounce-3.24.41/BUILD_COMMIT
