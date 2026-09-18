# Phase 0 findings — de-risking the Fedora variant

Status date: 2026-09-17. This records what was actually verified before Phase
1+ work started, per the build brief's "do not proceed with full packaging
work until both [Phase 0] risks are validated or a fallback decision is
made" rule.

## Environment disclosure

This pass was done from a headless Ubuntu container with no GUI, no
`dnf`/`rpm`/`rpmbuild`, no KDE Frameworks/KWin development headers, and no
ability to boot Fedora KDE Spin. That means **neither Phase 0 checklist item
could be executed literally** ("attempt build", "install Fedora KDE Spin and
test"). What follows is source-level research against the real upstream
repos instead — enough to narrow both risks to a small number of concrete,
testable questions, but not a substitute for running the two checklist items
on real hardware/a VM. That remains the first thing to do with a real Fedora
KDE Spin box.

## 1. `liquid-gel` build compatibility

Cloned `pearOS-archlinux/liquid-gel` directly and read `CMakeLists.txt`,
`PKGBUILD`, and `README.md`:

- It's a fork of `kwin-effects-forceblur` (a.k.a. "Better Blur"), building
  two separate compiled plugin variants from one tree:
  `kwin/effects/plugins/forceblur.so` (Wayland) and
  `kwin-x11/effects/plugins/forceblur_x11.so` (X11, built only if
  `kwin-x11` is present on the system). Dual-backend support is already a
  design goal upstream, not something that needs to be added — that's a
  meaningfully lower risk than if it were Wayland- or X11-only.
- Version floor: `find_package(KF6 5.240.0 ...)`, `Qt 6.6.0`, C++20.
- The README states explicitly: *"Better Blur will usually support at least
  one previous Plasma release... Currently supported versions: 6.4."* — i.e.
  even upstream doesn't promise more than a one-minor-version compatibility
  window. KWin's effect-plugin ABI is not stable across Plasma point
  releases, so this is a real, named constraint, not a hypothetical one.
- Checked what Fedora actually ships (via Fedora's own spec files in
  `src.fedoraproject.org`, `rawhide` and `f42` branches):
  - **Fedora 42** (current stable): `kf6-kwindowsystem` **6.25.0**,
  - **Fedora Rawhide**: `kf6-kwindowsystem` **6.30.0**, `plasma-workspace`
    **6.7.90** (i.e. pre-6.8, tracking upstream's unstable branch).
  - Both satisfy liquid-gel's `5.240.0` floor on paper, but that floor is a
    minimum-version gate, not a compatibility guarantee — the README's own
    "6.4-ish window" statement means Rawhide's 6.7.90/6.30.0 is well outside
    what upstream tests against, and even Fedora 42's 6.25.0 is several
    minor releases ahead of the "6.4" line named in the README.

- `CMakeLists.txt` itself proves this isn't theoretical: it hard-fails the
  build (`message(FATAL_ERROR ...)`) if the detected KWin version is below
  **6.4**, and separately does a `try_compile()` probe
  (`KWIN_DRAWWINDOW_RETURNS_BOOL`) to detect whether `Effect::drawWindow()`
  returns `bool` or `void` on the target KWin — a signature change between
  KWin releases upstream is already patching around. That's a live
  compatibility shim for exactly the kind of KWin ABI drift this risk is
  about, not a hypothetical.

**Read on this risk**: this is very likely to need patching, particularly on
Rawhide. Fedora's KDE Spin (like the brief anticipated) tracks Plasma faster
than Arch does, so the version gap between what liquid-gel is tested against
and what Fedora ships is the binding constraint, not the CMake/Qt floors.
**Not yet attempted**: an actual compile against Fedora's `kf6-kwindowsystem-devel`/`kwin-devel`/`plasma-workspace-devel` headers — that requires a
real Fedora box and is the concrete next step (see Open items below).

## 2. Wayland vs. X11 — identifying the actual dock

Confirmed via `pearOS-archlinux/iso`'s live `packages/packages.x86_64` (the
actual package list the Arch ISO installs) that the dock package is literally
named `pearos-dock`. Found its source in
`pearOS-archlinux/pkgbuilds/pearos-dock/`:

- It is **not** the Android/Trebuchet-based dock from `ProjectPearOS` — the
  brief's caution was correct to flag that as a different, unrelated fork.
- It's a native **KPackage Plasma 6 Applet** (`metadata.json`:
  `"Id": "PearDock"`, `"Name": "Pear Dock"`, description *"macOS-style dock
  for KDE Plasma... Forked from: Victor Calles' Task Manager"*,
  `X-Plasma-Provides: org.kde.plasma.multitasking`), built from
  QML + a C++ plugin (`plugin/backend.cpp`, `smartlauncherbackend.cpp`) and
  custom Qt Quick shaders (`dock_prism.vert`/`.frag`, pre-baked to `.qsb` —
  Qt's RHI shader format, meaning rendering already goes through Qt6's
  backend-agnostic RHI layer rather than raw GLX/EGL calls).
  `PKGBUILD` makedepends include `vulkan-headers`, `kwin`, `plasma-workspace`,
  `plasma-activities`.
- Also present in the same `pkgbuilds` tree: `PearLauncher`, `PearFinder`,
  `PearFolderArc`, `PearTrash` — all standard KPackage Plasma applets/
  plasmoids, same story.
- The Arch package list has `#plasma-x11-session` **commented out** —
  i.e. upstream pearOS-Arch already defaults to the Wayland session today
  and doesn't ship the X11 session by default.

One more thing worth flagging that changes the read on this risk: the
dock's compiled QML plugin (`plugin/CMakeLists.txt`) links directly against
`PW::LibTaskManager`, `PW::LibNotificationManager` (plasma-workspace's
*private*, unversioned internal libraries — not the stable public KF6/Plasma
API surface) and `KSysGuard::ProcessCore`. Private plasma-workspace libs are
not ABI- or even API-stable across point releases the way liquid-gel's KWin
effect API at least has some compatibility expectations for — so
`pearos-dock`'s build-compatibility risk against Fedora's fast-moving
`plasma-workspace` package is arguably **sharper** than liquid-gel's, even
though the brief's own risk framing (and this repo's Phase 0 checklist)
focused on liquid-gel and on Wayland runtime behavior for the dock. Worth
tracking as its own build-compatibility risk, not just a runtime one.

**Read on this risk**: because the dock is a native Plasma 6 applet running
inside `plasmashell` via QtQuick/RHI — not an external X11-only window-manager
hack like Cairo-Dock or old Latte-Dock — there's a structurally better chance
it behaves correctly under Wayland than the brief's cautious framing assumed.
That said, this is still a read of the source, not a running test; RHI
backend-agnostic rendering doesn't guarantee correct window-matching/screen-
edge behavior under `kwin_wayland` specifically. **Not yet attempted**:
actually running Fedora KDE Spin's Wayland session with `pearos-dock`
installed and watching for misbehavior — the literal Phase 0 checklist item.

## Other confirmations picked up along the way (not blocking, but relevant to later phases)

- **Ploader** (`pearos-bootloader`) is exactly what the brief said: a stock
  rEFInd fork built with GNU-EFI/EDK2 + a normal Linux GCC toolchain — no
  distro-specific build dependency. Nothing to port for Phase 4.
- **`pafari`** builds with Meson/Ninja (GNOME Web/Epiphany fork); its Debian
  `builddepends` map cleanly to Fedora `*-devel` package names
  (`libgtk-4-dev` → `gtk4-devel`, etc.) — no unusual build-system porting
  needed beyond the spec file itself.
- **`pearos-settings`** is almost entirely static files (`etc/skel`,
  `usr/share`, `scripts/`) — a simple noarch RPM, not a compiled package.
- Branding repos (`Pear-Project/pearOS-Default-Icons`, `-SDDM`,
  `-GTK-Theme`, `-Wallpapers`) are plain file trees with a `whiptail`
  installer script, confirmed no compiled/distro-specific content. Note:
  upstream's SDDM installer *overwrites* `/usr/share/sddm/themes/breeze/`
  in place rather than installing under its own theme name — the Fedora RPM
  should install to `/usr/share/sddm/themes/pearos/` instead and set it via
  `/etc/sddm.conf.d/`, which is cleaner and avoids clobbering the stock
  Breeze theme. Called out in `packaging/pearos-branding/`.
- Two referenced repos (`Pear-Project/pearOS-Default-Kvantum`,
  `Pear-Project/pear-calamares-config`) returned 404 while cloning — either
  renamed, private, or not yet published. For Kvantum specifically, this
  may not matter: `pearos-settings`'s actual tree ships the Kvantum theme
  itself under `etc/skel/.config/Kvantum/pearOS/` (`.kvconfig` + `.svg`
  files), i.e. as per-user skel content bundled with settings, not a
  separate system-wide theme package. `packaging/pearos-settings/` follows
  that — installs to skel *and* to `/usr/share/Kvantum/` so the live
  session's system-wide default (set in `customize.sh`) has something to
  point at even before a user's skel is populated. `pear-calamares-config`
  has no such explanation and is still a real open item before Phase 4.

## Hands-on update — real Fedora KDE Spin VM (2026-09-17)

A real Fedora KDE Spin box now exists: the build VM ("plumos-fedora-kde-testbed")
on the user's the hypervisor cluster, installed from the official
`Fedora-KDE-Desktop-Live-44-1.7.x86_64.iso`. This is the machine the two
"not yet attempted" items above call for. Progress so far:

- Confirmed on-disk versions from the installed ISO snapshot:
  `kf6-kwindowsystem-6.25.0-1.fc44`, `kwin-6.6.4-2.fc44`,
  `plasma-workspace-6.6.4-1.fc44`. Notably this matches the `6.25.0`
  `kf6-kwindowsystem` version this doc previously only had for **Fedora
  42** — i.e. Fedora 44's initial ISO ships the same KWindowSystem baseline,
  not something newer. Fedora's Updates repo separately offers a much newer
  `plasma-workspace-26.08.1` (see below), so "installed baseline" and
  "latest available via `dnf upgrade`" are two different version targets
  worth testing `liquid-gel` against.
- Attempting `sudo dnf install kf6-kwindowsystem-devel kwin-devel
  plasma-workspace-devel qt6-qtbase-devel qt6-qtdeclarative-devel
  qt6-qtwayland-devel vulkan-headers wayland-devel libepoxy-devel` (the
  headers needed to even attempt compiling `liquid-gel`) surfaced a real
  Fedora packaging bug — not anything liquid-gel-specific. Pulling current
  Updates-repo packages produces a partial-cohort transaction:
  `kf6-kmime-6.30.0` (new KDE-Frameworks-style package name) and the
  already-installed `kmime-25.12.3` (old name) both ship the same files
  (`libkmime6_qt.qm` translations for several locales, `kmime.categories`)
  with **no `Obsoletes:` relationship between them**, so RPM refuses the
  transaction with a file-conflict error. `dnf install --allowerasing` does
  **not** resolve this (still fails identically). `dnf repoquery
  --whatrequires kmime` / `--whatrequires kf6-kmime` shows the whole
  Akonadi/PIM stack (kmail, kleopatra, akonadi-*, etc.) exists in the repo
  as two parallel version cohorts — 25.12.3 (needs old `kmime`) and 26.08.1
  (needs `kf6-kmime`) — plus a **third**, independently-versioned
  `kmime-26.04.3` still under the *old* name. This is exactly the "Fedora's
  KDE packaging moves fast and can be internally inconsistent" risk this
  doc's Section 1 predicted for KWin — it turned up first in the unrelated
  PIM/Akonadi dependency chain instead.
- Resolved by running a full `sudo dnf upgrade -y --exclude=systemd-udev
  --exclude=intel-gpu-firmware` (plain `--allowerasing` alone tried to
  **remove the protected `systemd-udev` package** to satisfy a
  `systemd-networkd` version bump — refused, do not force this; excluding
  it just leaves `systemd-networkd` at its old version, which is fine,
  nothing on this box uses it). `intel-gpu-firmware` hit the exact same
  unresolved-rename pattern as `kmime` (file conflict with `linux-firmware`,
  irrelevant to this VM anyway — excluded). 1473 package
  operations, one new kernel, one reboot, and the system landed on
  `kwin-6.7.5`/`kf6-kwindowsystem-6.30.0`/`plasma-workspace-6.7.5`.
- **`liquid-gel` now compiles.** `sudo dnf install` for the full real
  BuildRequires list (see the corrected
  `packaging/pearos-liquidgel/pearos-liquidgel.spec`) succeeded cleanly on
  the upgraded system — no more file conflicts once everything was on one
  cohort. `cmake -B build -S .` (no special flags — `BETTERBLUR_WAYLAND`
  and `BETTERBLUR_X11` both default `ON` in liquid-gel's own
  `CMakeLists.txt`) configured successfully, and `cmake --build build`
  produced a working **`forceblur.so`** (the Wayland KWin effect plugin)
  and **`pearos_liquidgel_config.so`** (its KCM config module) — Risk #1
  from Section 1 above is resolved for the Wayland target: liquid-gel
  builds against Fedora 44's real KWin 6.7.5 without any patching, despite
  being several minor versions past the "6.4-ish" window its own README
  warns about.
- The **X11 variant does not build**: `forceblur_x11.so` fails with
  `fatal error: core/region.h: No such file or directory` compiling the
  *same* `blur.cpp` that succeeds for Wayland. This points at a header
  gap in Fedora's `kwin-x11-devel` package, not a missing BuildRequires or
  a liquid-gel bug (nothing else needed for X11 was missing — `KWinX11`,
  `KDecoration3`, `libdrm` all resolved fine at configure time). Given this
  project's fallback decision already defaults to Wayland (see below), the
  spec now builds with `-DBETTERBLUR_X11=OFF` and treats fixing the X11
  variant as a nice-to-have, not a blocker.
- The real, corrected BuildRequires list needed several packages beyond
  what Section 1's speculative reading assumed: full KF6 component set
  (`kf6-kconfigwidgets-devel`, `kf6-kcrash-devel`, `kf6-kglobalaccel-devel`,
  `kf6-ki18n-devel`, `kf6-kio-devel`, `kf6-knotifications-devel`,
  `kf6-kwidgetsaddons-devel`, `kf6-kguiaddons-devel`, `kf6-kcmutils-devel`,
  each pulling their own further transitive `-devel` deps), plus
  `kdecoration-devel`, `libdrm-devel`, `vulkan-headers`, and
  `wayland-devel` — none of which the original spec draft or this doc's
  Section 1 had listed. Now reflected in
  `packaging/pearos-liquidgel/pearos-liquidgel.spec`.

## Fallback decision (for now)

Per the brief's instruction to pick a fallback if a risk isn't resolved:
default `profiles/pearos/profile.conf` targets **Plasma Wayland** (matching
upstream Arch pearOS's own current default), with an explicit, documented
one-line override to force the X11 session if hands-on testing on real
Fedora KDE Spin shows `pearos-dock` misbehaving under `kwin_wayland`. See
`PROFILE_SESSION` in `profiles/pearos/profile.conf`.

## Open items before Phase 2 packaging work should be trusted

1. **Done for Wayland — compile and runtime both verified.**
   `liquid-gel`'s Wayland plugin (`forceblur.so` + `pearos_liquidgel_config.so`)
   compiles cleanly against real Fedora 44 `kwin-6.7.5`/
   `kf6-kwindowsystem-6.30.0` (post `dnf upgrade` cohort — the installed-ISO
   baseline of `kwin-6.6.4`/`kf6-kwindowsystem-6.25.0` has not separately
   been tried, and probably isn't worth the effort now that the newer
   cohort works). `sudo cmake --install build` places it at
   `/usr/lib64/qt6/plugins/kwin/effects/plugins/forceblur.so` (+
   `metadata.json`, plugin `Id: forceblur`); enabling it
   (`kwriteconfig6 --file kwinrc --group Plugins --key forceblurEnabled
   true` + `qdbus-qt6 org.kde.KWin /KWin reconfigure` — note the binary is
   `qdbus-qt6` on this Fedora install, not `qdbus`/`qdbus6`) loads it into
   a **live** `kwin_wayland` session with no crash, and
   `qdbus-qt6 org.kde.KWin /Effects org.kde.kwin.Effects.isEffectLoaded
   forceblur` confirms `true` — genuinely active, not just present on disk.
   `.../Compositing.compositingType` reports `gl2`, i.e. KWin is running a
   real OpenGL2 scene (via software Mesa/llvmpipe in this GPU-less VM, but
   a GL scene nonetheless, which is what blur effects need — a pure
   QPainter/software-2D fallback would have made this moot). One benign
   warning logged (metadata `Id` field deprecation notice), nothing fatal.
   A screendump (via the build VM's QMP socket, `human-monitor-command
   screendump`) didn't show obvious blurring on the one dialog/panel
   visible at the time — expected, since `forceblur`'s whole feature is
   *force-adding* blur to specific windows via user-configured rules, it
   doesn't blur everything by default the way the stock `blur` effect can.
   Not yet done: configuring an actual force-blur window rule and
   confirming the visual result, and testing under real GPU acceleration
   rather than software Mesa.
   **Still open**: the X11 variant fails on a `kwin-x11-devel` header gap
   (`core/region.h`) — low priority given the Wayland-first fallback
   decision, but worth a Fedora bug report if anyone wants the X11 session
   to work later.
2. Install Fedora KDE Spin, add the (to-be-created) COPR repo, install
   `pearos-dock`, and drive a Wayland session for real: panel edge snapping,
   multi-monitor, HiDPI, and window-preview thumbnails are the specific
   things a Plasma 6 applet can still get wrong under `kwin_wayland` even
   with RHI rendering. Before that: actually compile `pearos-dock`'s
   `plugin/` against Fedora's `plasma-workspace-devel`/`libksysguard-devel` —
   given the private-lib dependency above, this may fail before the Wayland
   question is even reachable.
3. Locate or recreate `pear-calamares-config` (see above) before Phase 4
   installer work.
