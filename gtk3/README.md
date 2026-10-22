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

This deliverable is a source patch and validation bundle. No installed GTK 3
packages are modified. The target machine has both amd64 and i386 GTK 3
libraries installed; a system replacement needs matching multiarch packages,
rather than installing only an amd64 build. Physical touchpad feel, input
methods, accessibility and the complete GTK test matrix still need broader
manual validation before deployment as a system library.
