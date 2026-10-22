GTK 4 bounce scrolling for Ubuntu 24.04 / Linux Mint 22.x, amd64

Extract the GitHub Actions artifact, open a terminal in this folder, then run:

    bash install.sh --dry-run
    bash install.sh

The helper verifies bundle checksums and package metadata, checks your OS and
architecture, and replaces only GTK packages you already have installed.
APT shows the proposed transaction and asks for confirmation. Package removal
is disabled. No library files are copied manually.

Log out and back in, or reboot, after installing. Test touchpad/touchscreen
overscroll in a native GTK 4 application such as GNOME Settings or Files.
GTK 3 applications and Flatpak runtimes are separate.

To restore the original Ubuntu packages included in this artifact:

    bash rollback.sh --dry-run
    bash rollback.sh

Keep this extracted folder for rollback. A text console (Ctrl+Alt+F3) can run
the same rollback command if a graphical application has problems.

The custom version ends in +bounce2. A later Ubuntu revision supersedes it
normally; no package holds or APT pins are added. Rebuild the patch against
new Ubuntu security updates if you want to retain the effect.

Validation and build provenance are in provenance/build.json. Physical input
and the animation's feel still need manual testing. The full upstream test
matrix is not run; CI runs focused scrolled-window tests and an installed
library rendering/scroll-boundary smoke test. The build omits documentation,
example/test packages and Debian-installer packages; it includes the six
desktop runtime, utilities, development and introspection packages.

Source patch: Christian Hergert
https://gist.github.com/chergert/91b4feb1e359c916bcf86ae2ea1f5044
