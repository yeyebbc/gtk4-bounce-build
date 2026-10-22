# Patched GTK for GNOME 50 Flatpak apps

This workflow builds GTK **4.22.5** with the original bounce patch inside a
pinned **org.gnome.Sdk//50**. It uses the source archive and SHA256 listed in
your GNOME Platform 50's installed manifest. Nothing is compiled on the host.

The core library is built with /usr paths so Flatpak's existing GTK resources,
translations, printing/media modules and GL/Vulkan dependencies remain usable.
Wayland, X11, Broadway, Vulkan and Sysprof match the GNOME build recipe.
Only auxiliary demos/docs/tests and introspection generation are disabled;
the existing runtime's matching typelib is used.

CI verifies that every original exported GTK symbol is present, then runs
upstream scrolledwindow sizing tests and a rendering test under Xvfb in the
pinned **Platform** runtime. The render test asserts that the custom library
was actually loaded. Physical bounce behavior requires manual input testing.

Download **gtk4-bounce-gnome50-x86_64**, extract its tar.gz inside the project
at `installed/`, and run `bash enable-flatpak.sh`. Run
`bash disable-flatpak.sh` to restore the saved per-app user overrides.
The bundle's README describes update handling and direct helper commands.

Source URL/hash, runtime/SDK commits, build recipe, patch and LGPL license are
included in the artifact. No applications or Flatpak runtimes are rebuilt or
replaced, and no global Flatpak overrides are changed.
