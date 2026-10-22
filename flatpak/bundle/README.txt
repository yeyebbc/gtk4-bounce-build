GTK 4 bounce for GNOME 50 Flatpak applications (x86_64)

Built from the same GTK 4.22.5 archive as GNOME Platform 50, with Christian
Hergert's bounce patch. The library retains /usr paths and the runtime's
public backends. Runtime resources, printing and media modules stay in the
normal Flatpak runtime.

Run as your desktop user (no sudo):
  python3 manage.py install --dry-run
  python3 manage.py install
  python3 manage.py verify
  python3 manage.py status
  python3 manage.py rollback --dry-run
  python3 manage.py rollback

Defaults: Flatseal, NewsFlash and Resources. An app ID may be supplied to act
on one app. Installation checks archive checksums, the app's runtime and the
runtime's exact GTK source hash. It adds a read-only grant to this bundle
and prepends its lib/ directory to the app's existing LD_LIBRARY_PATH.
Existing user overrides are saved before changing them; global overrides
(including cursor preloads), application files and runtime files are untouched.
Rollback restores those user overrides, provided they have not subsequently
been edited. Keep this directory at the same path while enabled.

The overrides persist across app updates. Normal runtime updates remain
enabled; however, the custom GTK shadows runtime GTK fixes until this bundle
is rebuilt or disabled. Rebuild when GNOME Platform's GTK is updated or the
apps move to a different runtime. There is no APT hold or Flatpak mask.

CI checks exported symbols, upstream scrolledwindow sizing tests and rendering
in the actual Platform runtime. Physical touchpad bounce needs manual testing.

Source/patch and pinned runtime/SDK commits are recorded in provenance/.
GTK is LGPL-2.0-or-later; see COPYING. Sources are available from the pinned
upstream source URL and patch, together with the build recipe in the build
repository. To rebuild, run the Flatpak workflow in:
https://github.com/yeyebbc/gtk4-bounce-build
