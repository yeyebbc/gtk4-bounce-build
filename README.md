# GTK bounce packages for Debian 13 / GNOME 48

The `codex/debian13-gnome48` branch ports the native GTK 4 and GTK 3 bounce
packages to **Debian 13 (trixie)**. The Ubuntu / Linux Mint build stays on
[`main`](https://github.com/yeyebbc/gtk4-bounce-build/tree/main).

GitHub Actions builds Debian's exact sources with the existing bounce patches:

| Toolkit | Debian source | Custom version | Architectures | Install artifact |
| --- | --- | --- | --- | --- |
| GTK 4 | `4.18.6+ds-2` | `4.18.6+ds-2+bounce1` | amd64 | `gtk4-bounce-trixie-amd64` |
| GTK 3 | `3.24.49-3` | `3.24.49-3+bounce1` | amd64 + i386 | `gtk3-bounce-trixie-multiarch` |

These are the [GTK 4](https://packages.debian.org/trixie/libgtk-4-1) and
[GTK 3](https://packages.debian.org/trixie/libgtk-3-0t64) versions shipped for
Debian 13's [GNOME 48 desktop](https://packages.debian.org/trixie/gnome-shell).
No GNOME Shell or Mutter patch is needed. Both bounce patches apply unchanged
with zero fuzz; their historical filenames are retained for reuse.

## Download and install

1. Open **Actions** and select this branch's successful **Build Debian 13 GTK 4
   bounce packages** or **Build Debian 13 GTK 3 bounce system packages** run.
2. Download the matching install artifact from the table and extract it.
3. Open a terminal in the extracted directory and run:

   ```bash
   bash install.sh --dry-run
   bash install.sh
   ```

Install each toolkit's bundle separately if you want both. The shared helper
checks Debian 13, architecture, installed versions, package metadata and bundle
checksums. It passes only GTK packages you already have installed to APT,
including matching development, introspection and GTK 3 multiarch packages.
APT shows the transaction and asks for confirmation; package removal is refused.

Log out and back in, or reboot, so applications load the replacement libraries.
Test overscroll with a physical touchpad/touchscreen in native GTK applications.
Flatpak and Snap applications use their own runtimes and are independent of
these system packages. The existing [GNOME 50 Flatpak build](flatpak/README.md)
is separate and has not been retargeted to GNOME 48.

## Roll back

Keep each extracted artifact: it includes the exact original Debian `.deb`
packages for offline rollback of that GTK replacement.

```bash
bash rollback.sh --dry-run
bash rollback.sh
```

The same command works from a text console with **Ctrl+Alt+F3**. Log out and
back in, or reboot, after rollback. No package holds or APT pins are added.
A later Debian revision supersedes `+bounce1` normally; rebuild against updated
Debian sources to retain the effect. The installer refuses a bundle whose base
version does not match the installed GTK packages.

## Build and validation

Pushes to `codex/debian13-gnome48` and manual workflow requests run the package
builds in **Debian 13 containers** on GitHub's Ubuntu runners. Compilation and
runtime tests happen in CI. Source inputs are pinned by SHA256 and third-party
actions by commit SHA. Debian's patches, backends, compiler hardening and strict
package symbol checks are preserved. Debian builds `gtk-update-icon-cache`
from GTK 4, so it is included in the GTK 4 bundle.

The existing `dpkg-buildpackage` scripts omit documentation, installer udebs
and auxiliary examples/tests, then run focused tests separately from the
`nocheck` package build:

- GTK 4: upstream scrolledwindow sizing tests against installed packages and
  the installed-library rendering/scroll-boundary smoke test under Xvfb.
- GTK 3: native C scroll tests and GTK/GDK ABI checks for amd64 and i386;
  Python GI scroll tests on amd64; upstream scrolledwindow sizing tests on both.
  Stock GTK provides a negative control for the bounce behavior. See
  [the GTK 3 tests](gtk3/README.md).

Artifacts contain rebuilt packages, stock rollback packages, checksums,
source/patch/build provenance and install/rollback helpers. Install artifacts
are retained for 90 days and failure logs for 30 days. Downloaded copies do not
expire. The complete upstream display/font/GPU matrix and physical input feel
still need manual validation.

GTK licensing and notices are preserved in the packages. The GTK 4 bounce patch
is by [Christian Hergert](https://gist.github.com/chergert/91b4feb1e359c916bcf86ae2ea1f5044);
this repository reuses that patch and its existing GTK 3 port.
