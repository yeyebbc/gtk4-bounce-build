# GTK 4 bounce packages for Linux Mint 22 / Ubuntu 24.04

GitHub Actions builds Christian Hergert's [bounce scrolling patch](https://gist.github.com/chergert/91b4feb1e359c916bcf86ae2ea1f5044)
as native Ubuntu packages for **amd64**, based on the exact Ubuntu source
**4.14.5+ds-0ubuntu0.10**. The build keeps Ubuntu's patches, runtime backends,
compiler hardening/optimization and ABI checks. The custom version is
**4.14.5+ds-0ubuntu0.10+bounce2**.

## Download and install

1. Open **Actions → Build GTK 4 bounce packages** and choose a successful run.
2. Download the **gtk4-bounce-noble-amd64** artifact and extract it.
3. Open a terminal in the extracted folder and run:

   ```bash
   bash install.sh --dry-run
   bash install.sh
   ```

The helper checks the OS, architecture, package versions, metadata and bundle
checksums, then passes only your already installed GTK packages to APT. APT
shows the transaction and asks for confirmation. It refuses package removals.
Matching development and introspection packages are upgraded together when
they are installed, keeping exact-version dependencies consistent.

Log out and back in, or reboot, so applications use the new library. Test
overscroll with a physical touchpad/touchscreen in native GTK 4 applications.
GTK 3 applications and Flatpak runtimes need separate changes.

## Roll back

Keep the extracted artifact: it includes the exact original Ubuntu `.deb`
packages for offline rollback of the GTK replacement itself.

```bash
bash rollback.sh --dry-run
bash rollback.sh
```

The same command can be run from a text console with **Ctrl+Alt+F3**. Log out
and back in, or reboot, after rollback.

No package holds or APT pins are added. A later Ubuntu revision upgrades over
`+bounce2` normally, so the patch must be rebuilt against future Ubuntu updates.
The installer refuses a bundle whose base does not match the installed GTK.

## Build and validation

Pushes to `main` and manual **Run workflow** requests build on `ubuntu-24.04`.
Inputs and third-party actions are pinned to SHA256 hashes / commit SHAs.
The build downloads Ubuntu's original source and Debian patch archive, applies
the existing distro patch series, and adds the bounce patch as the last patch.
The only backport change removes a context line absent from GTK 4.14.5.

CI uses `dpkg-buildpackage` with Ubuntu's supported `nodoc`, `noinsttest` and
`noudeb` profiles to build the six desktop packages. It disables compilation
of the large auxiliary test suite and manual test programs. It then installs
the runtime and development packages inside the runner, compiles/runs the
upstream `scrolledwindow` tests against that installed library under Xvfb,
and runs a rendering/scroll-boundary smoke test. The complete upstream
display/font/GPU test matrix is skipped (`nocheck` during packaging); focused
tests run separately. Physical input behavior and the animation's feel need
manual testing on the machine.

The artifact includes rebuilt packages, official rollback packages, SHA256
checksums, source/patch/build provenance, and install/rollback helpers. Separate
build-log artifacts are uploaded even when the build fails. Install bundles
are retained for 90 days; downloaded copies do not expire.

GTK source licensing and notices are preserved in the packages. The patch is
by Christian Hergert; this repository contains build helpers and its GTK 4.14.5
backport, not a fork of the toolkit.

## GNOME 50 Flatpak applications

See [the separate Flatpak build](flatpak/README.md) for a runtime-compatible
GTK 4.22.5 library and reversible per-app overrides. The Ubuntu .deb build
above is independent of this artifact.
