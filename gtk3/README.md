# GTK 3.24.41 bounce scrolling source patch

This is a GTK 3 port of Christian Hergert's
[bounce patch](https://gist.github.com/chergert/91b4feb1e359c916bcf86ae2ea1f5044).
It targets the exact Ubuntu/Mint source **3.24.41-4ubuntu1.3**, after its distro
patches are applied. The patch is independent of CPU architecture.

The port retains the GTK 4 patch's overshoot distance, visual resistance and
spring friction. GTK 3 uses two private GdkWindows to clip and move content
while keeping native text/tree view windows, input coordinates and scrollbars
consistent. It redraws the full viewport and restores the final zero-offset
frame. Existing smooth-scroll rebound and touch drag-end handling are used.

Apply after extracting the Ubuntu source:

```bash
patch --dry-run --batch --fuzz=0 -p1 -i /path/to/gtk3-3.24.41-bounce.patch
patch --batch --fuzz=0 -p1 -i /path/to/gtk3-3.24.41-bounce.patch
```

The GitHub **Validate GTK 3 bounce patch** workflow downloads pinned Ubuntu
source inputs, compiles in CI and tests actual smooth-scroll events with
GtkTextView, GtkTreeView and a drawing area in GtkViewport. It checks all four
edges with/without overlay scrollbars, content clipping, logical adjustments,
rebound, fixed scrollbar positions and realize/unrealize/add/remove lifecycle.
The same events are run against stock GTK as a negative control. Exported ABI
symbols and upstream scrolledwindow sizing tests are also checked.

The **Build GTK 3 bounce system packages** workflow also produces an
install/rollback bundle for Ubuntu noble / Linux Mint 22.x. It builds matching
amd64 and i386 Debian packages at version **3.24.41-4ubuntu1.3+bounce1**, retaining
Ubuntu hardening, runtime backends, GIR data and strict package symbol checks.
Only docs, installer udebs and the auxiliary examples package are omitted.
Native C regression clients exercise both 32-bit and 64-bit package contents.

Extract the `gtk3-bounce-noble-multiarch` artifact and run:

```bash
bash install.sh --dry-run
bash install.sh
```

The installer verifies checksums and versions and selects only the GTK 3 packages
already installed, including matching multiarch libraries. Log out and back in,
or reboot, after installation. Run `bash rollback.sh` to restore the exact stock
packages included in the bundle. See [INSTALL.txt](INSTALL.txt) for details.

No APT holds or pins are created. Native system replacement does not change
Flatpak/Snap runtimes. Physical touchpad feel, input methods, accessibility and
the complete GTK test matrix still need manual validation.
