# Phase 3 findings — branding layer

Phase 3 (per `README.md`) is: "Icons, GTK theme, Kvantum, SDDM theme,
wallpapers repackaged as RPMs and wired into the profile as live-session
defaults."

## Where things actually stand (2026-09-18)

More of Phase 3 is already done than the roadmap checkbox suggests —
`pearos-branding.spec` and the relevant parts of `pearos-settings.spec`
were written during Phase 0/2 work and now build successfully in the
real COPR repo (`alexgalicea/plumos`, see `docs/phase2-findings.md`).
What was actually missing, found by reading the real wiring rather than
assuming it worked:

### Bug found and fixed: the profile was still pointing at a placeholder COPR

`profiles/pearos/repo.sh` had `PROFILE_COPR="pearos/pearos"` — the
Phase 2 placeholder — even though the real repo
(`alexgalicea/plumos`) has been live and fully working since earlier
this session. A branded ISO build (`engine/build-iso.sh` without
`--skip-branding`) would have tried to `dnf copr enable pearos/pearos`,
which doesn't exist, and fallen through to the "not published yet"
warning path — silently building an *unbranded* ISO despite the user
asking for branding. Fixed to the real slug; also updated the stale
comments in `packages.sh` and the warning message in `repo.sh` that
still talked about Phase 2 not being done yet.

### Bug found and fixed: a look-and-feel ID that never existed anywhere

`profiles/pearos/profile.conf`'s `PROFILE_LOOKANDFEEL_ID` was set to
`"com.pearos.desktop"` — invented, not derived from anything real.
Downloaded the actual `pearos-settings` upstream tarball and confirmed
the real Plasma look-and-feel package's `KPlugin.Id` (in its
`metadata.json`) is literally `"pearOS"`. Fixed the ID — but that alone
wouldn't have been enough, since **the look-and-feel package itself
wasn't packaged by any spec at all**. Added it to
`pearos-settings.spec` (`usr/share/plasma/look-and-feel/pearOS/` and
the `pearOS-dark` variant — small, self-contained, unlike the much
larger content below). Rebuilt and resubmitted to COPR as build
`11000859` (status pending as of this writing — check
`copr-cli list-builds alexgalicea/plumos` for the current result).

### The rest of `profile_customize()` (customize.sh) — checked, looks correct

Read through the whole `profile_customize()` hook in
`profiles/pearos/customize.sh` line by line against what each spec
actually installs:

| Setting | Value | Verified against |
|---|---|---|
| SDDM theme | `pearos` | `pearos-branding.spec`'s `pearos-sddm-theme` subpackage installs to `/usr/share/sddm/themes/pearos/` — matches. |
| Kvantum theme | `pearOS` | `pearos-settings.spec` installs to `%{_datadir}/Kvantum/pearOS/` — matches (case-sensitive, checked). |
| GTK theme | `pearOS` | `pearos-branding.spec` installs to `%{_datadir}/themes/pearOS/` (renamed from upstream's internal "Sweet" name at install time) — matches. |
| Icon theme | `pearOS` | `pearos-branding.spec` installs to `%{_datadir}/icons/pearOS/` (+ `pearOS-dark`) — matches. |
| Look-and-feel | `pearOS` (was wrong, see above) | Now matches, once `11000859` lands. |
| liquid-gel enabled by default | `pearos_liquidgelEnabled=true` in `kwinrc` | Matches `pearos-liquidgel.spec`'s actual KWin plugin config key (confirmed via Phase 0's real runtime test — `isEffectLoaded` returned `true`). |

All five of these were cross-checked against the *actual* installed
paths from real upstream trees / real spec `%files` sections, not
assumed — this is the same discipline used throughout Phase 2, applied
to the wiring layer instead of the packages themselves.

## Still open: the same unclaimed-content question from Phase 2

Restating from `docs/phase2-findings.md` since it's squarely a Phase 3
scope question: `pearos-settings` upstream ships real pearOS visual
identity that's still unpackaged by anything in this project:

- `usr/share/kwin/effects/` — 55 files, custom KWin window-manager
  effects (distinct from `liquid-gel`, which is only the blur effect).
- `usr/share/plasma/desktoptheme/` — 1392 files, a full Plasma desktop
  theme (both light and dark variants).
- `usr/share/aurorae/themes/` — window-decoration (titlebar) theme.
- `usr/share/sounds/`, `usr/share/color-schemes/`, `usr/share/extras/`.

This is a real, human scope decision (fold into `pearos-settings`,
split into new packages, or deliberately skip for now) that materially
affects how "branded" the ISO actually looks once Phase 3 is called
done — the look-and-feel splash screen and SDDM/GTK/icon theming will
all work without this content, but the desktop itself (window
decorations, Plasma widget styling, KWin effects beyond the blur) will
still look stock Breeze underneath. Not decided here; flagging again so
it doesn't get lost.

## DONE: first real branded ISO build attempted (2026-09-18)

Ran `engine/build-iso.sh --profile pearos --branch 44 --version
2026.09.18-branded` on the build VM (no `--skip-branding` — the first such
attempt this entire session). Found and fixed one real bug immediately:

**Bug: `dnf copr enable` failed outright.** `Unknown argument "copr"
for command "dnf5"`. Fedora 44's `dnf` is dnf5, and dnf5's `copr`
subcommand comes from the `dnf5-plugins` package — `repo.sh` was
installing `dnf-plugins-core` (the dnf4-era name, still installable on
Fedora 44 for compat, but it doesn't provide dnf5's plugin interface).
Confirmed the real providing package via `dnf5 repoquery
--whatprovides 'dnf5-command(copr)'`. Fixed, pushed, retried.

**Second attempt: full success at the packaging/wiring level.** All 8
real COPR packages (`pafari`, `pearos-dock`, `pearos-liquidgel`,
`pearos-settings`, and `pearos-branding`'s 4 subpackages) resolved and
installed cleanly from the real `alexgalicea/plumos` repo, and
`profile_customize()` ran through every step (SDDM theme, session,
look-and-feel, Kvantum, GTK/icon theme, liquid-gel enable) without
error. ISO built successfully.

## Real bug found on boot: the SDDM theme is Qt5, this system is pure Qt6

Booted the branded ISO on the install-test VM and verified the **wiring** is
completely correct: `/etc/sddm.conf.d/10-pearos-theme.conf` says
`Current=pearos`, and `/usr/share/sddm/themes/pearos/` is a real,
complete theme (`Main.qml`, `Login.qml`, `Background.qml`,
`Preview.png`, `background.png` — not a stub). `kdeglobals` says
`LookAndFeelPackage=pearOS`, and `/usr/share/plasma/look-and-feel/`
really does contain `pearOS`/`pearOS-dark` alongside the stock Fedora
ones. No crash, no PAM/`XDG_RUNTIME_DIR` issue (Phase 1's fix held).

But the **theme itself doesn't render** — a QMP screendump shows SDDM's
own error banner right on screen:

```
The current theme cannot be loaded due to the errors below,
please select another theme.

file:///usr/share/sddm/themes/pearos/Main.qml:3:1: module
"QtQuick.Controls" version 1.1 is not installed
```

Confirmed the real scope by reading the theme's actual imports
(`grep -n "^import" /usr/share/sddm/themes/pearos/*.qml`): **4 of the
theme's 6 QML files** (`Main.qml`, `BreezeMenuStyle.qml`,
`KeyboardButton.qml`, `SessionButton.qml`) import
`QtQuick.Controls 1.1/1.3/1.4` and/or `QtQuick.Controls.Styles 1.4` —
genuine Qt5-era QML, not just an old version string. `Main.qml` also
imports `QtGraphicalEffects 1.0` (removed in Qt6, replaced by
`Qt5Compat.GraphicalEffects`), and several files import
`org.kde.plasma.components 2.0` (the Plasma 5 component set — Plasma 6
themes typically use `org.kde.plasma.components 3.0` or QQC2-based
components instead). Confirmed via `rpm -qa` that this system has
**zero** Qt5 QML packages installed at all (`qt5-qtdeclarative`,
`qt5-qtquickcontrols` — neither present), so there's no compat shim to
lean on even temporarily.

This is real, substantial porting work — Controls 1.x → 2.x is not a
version bump, the whole component/theming model changed (e.g. Controls
1.x's `Button { style: ButtonStyle { ... } }` custom-styling pattern
doesn't exist in Controls 2.x, which themes via `Material`/`Fusion`
style plugins or fully custom delegates instead). **Deliberately not
attempted in this session** — a rushed partial port risks leaving the
theme in a worse, half-broken state than the current clean "falls back
gracefully with a clear on-screen error" behavior, and this deserves
focused, dedicated attention rather than being squeezed in at the end
of an already long session.

**Next step for whoever continues**: port
`packaging/pearos-branding`'s SDDM theme source (from
`Pear-Project/pearOS-Default-SDDM` upstream) to Qt6/Plasma 6 QML:
replace `QtQuick.Controls 1.x` usage with `QtQuick.Controls 2.x` (or
drop custom `ButtonStyle`-based styling entirely in favor of
`org.kde.plasma.components 3.0`, which is likely the more idiomatic
Plasma 6 approach and would also modernize the other now-outdated
Plasma 2.0 component imports at the same time), replace
`QtGraphicalEffects 1.0` with `Qt5Compat.GraphicalEffects` (needs
`qt6-qt5compat` — check whether that's an acceptable BuildRequires/
Requires addition, it's a compat shim not core Qt6) or rewrite the
specific effects used with native Qt6 equivalents. Test iteratively the
same way this session tested every other QML fix (Phase 0's
`pearos-dock` patch is a good precedent) — reference `SDDM error`
output is exact and actionable (`file:///.../Main.qml:3:1: ...`), so
fix one file, rebuild the `pearos-branding` SRPM, resubmit to COPR,
rebuild the ISO, reboot, re-check the screendump, repeat.

## RESOLVED: SDDM theme ported to Qt6, verified working end-to-end (2026-09-18)

Rather than hand-porting upstream pearOS's bespoke Qt5 QML file by
file (a large, error-prone undertaking for 6 interdependent files),
reused Fedora's own `sddm-breeze` package's QML instead — it's already
Qt6/Plasma 6-correct, already installed as a `BuildRequires`, and
stays current automatically as Fedora updates its own theme. Fedora's
`Main.qml` delegates Clock/Battery/ActionButton/WallpaperFader/etc to
a shared `org.kde.breeze.components` module (provided by
`plasma-workspace`, already a baseline dependency), so only 5 files
needed copying at all: `Main.qml`, `Background.qml`,
`KeyboardButton.qml`, `Login.qml`, `SessionButton.qml`. pearOS keeps
its own `theme.conf`, `background.png`, `Preview.png`, and `faces/`
for the actual branding. Landed as `pearos-branding` `1.0-2`, COPR
build `11001192` (succeeded).

### Bug found: fix didn't actually deploy on the first boot test

Rebuilt the branded ISO (`branded2`) and boot-tested — the screendump
was **pixel-identical** to the original broken one. Root-caused by
inspecting the rootfs directly rather than re-testing blind:
`rpm -q pearos-sddm-theme` showed `1.0-1` (the OLD version) and
`Main.qml` still had the Qt5-era `import QtQuick.Controls 1.1` line.

Cause: `engine/build-iso.sh`'s `$ROOTFS_TARGET` is reused across
builds (by design, for speed), and `dnf5 install <pkg>` on an
already-installed package has pure "ensure presence" semantics — it
does **not** implicitly upgrade to a newer available version, with or
without `--refresh` (which only affects metadata-cache freshness, a
separate concern from package-selection behavior). Tried adding
`--refresh` alone first (`branded3` build) — confirmed via `rpm -q`
that this **still** left `1.0-1` installed, with dnf's own output
saying `Package "pearos-sddm-theme-1.0-1..." is already installed` /
`Nothing to do.` for every package in the install list. The actual fix
is `--best`, which forces dnf to select/upgrade to the best available
version. Verified this manually against the stale rootfs
(`dnf install --best pearos-sddm-theme` correctly upgraded
`1.0-1`→`1.0-2`) **before** committing the fix to `build-iso.sh`, to
avoid burning another full boot-test cycle on an unverified guess.
Fixed line (`engine/build-iso.sh`, package-install step):

```
run_in_target dnf -y --refresh --setopt=install_weak_deps=False install --best "${PROFILE_REPO_PACKAGES[@]}"
```

Rebuilt (`branded4`), verified `1.0-2` installed in the rootfs via
`rpm -q` first, then boot-tested: `journalctl -u sddm` came back
completely clean for `error`/`Error`/`module`/`not installed`, and the
screendump's hash differed from every prior (broken) capture — this
looked like success.

### Second bug found: the "clean" boot test was hiding a different failure

The screendump from `branded4` did **not** show pearOS's background or
a working login form at all — it showed a plain diagonal
pink-to-purple gradient with only a mouse cursor, no avatar, no
password field, no error text anywhere on screen. This is Plasma's
default color-fallback background, shown when `Background.qml`'s
`Image` fails to load — a *silent* fallback, not an error, which is
exactly why the narrow `grep -i "error\|Error\|module\|not installed"`
check that had declared the boot "clean" missed it entirely.

Went back to the full, unfiltered `journalctl -b` output and found the
real signal: `sddm-greeter-qt6[…]: file:///usr/share/sddm/themes/pearos/Main.qml:406:13:
Unable to assign [undefined] to QUrl`. Line 406 turned out to be
`source: config.logo` — harmless on its own, since `visible:
config.showlogo === "shown"` is false by default and pearOS's
`theme.conf` doesn't set `showlogo`, so the logo `Image` stays
invisible regardless. That warning was a **red herring that happened
to point at the right file at the right general time**, not the actual
bug.

Found the real cause by comparing pearOS's `theme.conf` against the
real, working `sddm-breeze` theme.conf on the same system:

| | pearOS's `theme.conf` (upstream, unmodified) | real `sddm-breeze` `theme.conf` |
|---|---|---|
| `background=` | `background.png` (bare relative filename) | `/usr/share/backgrounds/default.jxl` (absolute path) |

pearOS's value is a leftover convention from its old Qt5/WhiteSur-era
theme. `Main.qml`'s `Background { sceneBackgroundImage: config.background }`
assigns that raw string straight to `Background.qml`'s
`Image.source` (a `QUrl`-typed property) with no directory context to
resolve a bare relative name against — it silently fails to load, and
SDDM falls back to its own default gradient. No exception, no log
line naming the failure — the only visible symptom was the wrong
picture on screen.

**Fix**: rewrite `theme.conf`'s `background=` line to the absolute
installed path at package-install time (`pearos-branding.spec`,
`%install`):

```
sed -i "s#^background=.*#background=%{_datadir}/sddm/themes/pearos/background.png#" \
    %{buildroot}%{_datadir}/sddm/themes/pearos/theme.conf
```

Landed as `pearos-branding` `1.0-3`, COPR build `11001401`
(succeeded). Rebuilt the ISO (`branded5`), verified in the rootfs
*before* boot-testing that `pearos-sddm-theme-1.0-3` was installed and
`theme.conf` now read
`background=/usr/share/sddm/themes/pearos/background.png` — then
boot-tested.

### Final result: confirmed working, full visual verification

The `branded5` screendump shows a complete, correct pearOS-branded
SDDM greeter:

- **Background**: pearOS's real magenta-to-purple gradient wallpaper
  — confirmed by pulling `background.png` directly out of the rootfs
  and comparing it pixel-for-pixel against the screendump; identical.
  Not a fallback of any kind.
- **Login form**: a generic user-silhouette avatar, "Live System User"
  label, a password field, and a submit arrow — all rendering and
  laid out correctly (this is Fedora's own `sddm-breeze` `Login.qml`,
  reused as-is per the porting approach above).
- **Accent color**: the password field's focus border renders in
  pearOS's blue (`#5657f5`, from `theme.conf`'s `color=` key) — the
  branding accent is genuinely wired through, not just present in the
  config file.
- **Bottom action bar**: Hibernate / Sleep / Restart / Shut Down /
  Other, all with icons, all from the shared `org.kde.breeze.components`
  module.
- No error banner, no fallback gradient, no missing elements.

This closes out the SDDM theme item of Phase 3. The same benign
`Unable to assign [undefined] to QUrl` log line for `config.logo`
still appears (theme.conf never sets `showlogo`/`logo`, so the
`Image` stays invisible as intended) — cosmetically harmless and not
worth suppressing by adding unused keys to `theme.conf` just to
silence a log line with no visible effect.

### Lessons for the rest of this project

1. **A build engine that reuses a rootfs across builds must force
   package upgrades explicitly.** `dnf5 install <pkg>` on an
   already-installed package won't upgrade it on its own — `--refresh`
   only affects metadata freshness, not package-selection behavior.
   Any future engine change to the package-install step needs to keep
   `--best` (or equivalent) or this exact silent-staleness bug comes
   back.
2. **Verify a fix landed in the artifact before spending a boot-test
   cycle on it.** `rpm -q`/`grep` against the rootfs directly is
   seconds; a full ISO rebuild + VM boot + screendump round-trip is
   minutes. Adopted this as standard practice after the `branded2`
   round wasted a full cycle testing a fix that silently hadn't
   deployed at all.
3. **A "clean" narrow log grep is not proof of a working feature.** The
   `branded4` boot passed an `error|Error|module|not installed` filter
   while showing a completely broken screen — the failure was silent
   (a fallback, not an exception) and the one log line that did exist
   pointed at an unrelated, harmless property. Always read the full
   unfiltered log for anything visually load-bearing, and always
   independently confirm the *visual* result (a screendump, not just a
   log) before declaring a UI fix done.

## RESOLVED: the "unclaimed content" scope question (2026-09-18)

User decision (asked directly): fold the rest of `pearos-settings`
upstream's content into new subpackages of the same spec, following
the precedent already set by `pearos-branding.spec` (one spec, several
independent subpackages, no build step) — including the third-party
plasmoid bundle, which surfaced as a separate sub-question mid-task
(see below) and was also approved.

Verified the real upstream tarball directly before writing anything
(same discipline as every other package in this project). Five new
subpackages, all `noarch`, no compiled content anywhere (checked):

- **`pearos-kwin-effects`** — `usr/share/kwin/{effects,scripts,tabbox}/`.
  The 4 `kinetic_*` effects are forks of KDE's own stock Maximize/
  Scale/FadingPopups/Squash effects (GPL, real KWin upstream authors —
  not pearOS originals); `macsimize6`/`truely-maximized` are
  third-party GPLv3 scripts; `AquaMediumIcons` is a tabbox icon theme.
  Shipped available, not enabled by default.
- **`pearos-plasma-theme`** — `usr/share/plasma/desktoptheme/{pearOS,
  pearOS-dark}/` + `usr/share/color-schemes/*.colors`. pearOS's own
  full Plasma SVG chrome theme + matching color schemes. Wired as the
  live-session default via `customize.sh`'s new `/etc/xdg/plasmarc`
  (`[Theme] name=pearOS`) and an appended `/etc/xdg/kdeglobals`
  `[General] ColorScheme=pearOS`.
- **`pearos-aurorae-theme`** — `usr/share/aurorae/themes/{pearOS,
  pearOS-dark}/`. Window-decoration theme. Wired via an appended
  `/etc/xdg/kwinrc` `[org.kde.kdecoration2]` block
  (`library=org.kde.kwin.aurorae`, `theme=__aurorae__svg__pearOS`).
- **`pearos-sounds`** — `usr/share/sounds/pearOS-sounds/`. System event
  sound theme. Not wired as a default (no obvious single config key
  for this the way the others have; deferred, see below).
- **`pearos-plasmoids`** — `usr/share/plasma/plasmoids/*/` (20
  directories, ~1080 files). **Not pearOS originals in most cases** —
  independently-authored KDE Store widgets pearOS bundles alongside
  its own (antroids, nemmayan/zayronxio ×4, luisbocanegra ×2, upstream
  `org.kde.windowtitle`, `tt.launchpadPlasma`, plus pearOS's own
  `Pear*`/`xyz.pearos.*` widgets). Checked every single widget's own
  `metadata.json` individually before packaging — all properly
  licensed (GPL-2.0-or-later/GPL-3.0-or-later/BSD-2-Clause), no unclear
  cases. Flagged to the user mid-task specifically because
  `PearTaskManager` is a renamed copy of KDE's own stock Task Manager
  plasmoid — installing this package only makes all 20 widgets
  available via Plasma's "Add Widgets" dialog, nothing in
  `customize.sh` adds any of them to a panel, so this does **not** run
  alongside `pearos-dock` (the project's actual default dock) unless a
  user manually adds it themselves.

Deliberately **not** packaged: `usr/share/extras/` — inspected
directly and it's upstream's own messy scratch/staging directory
(loose logo files, a duplicate/stale plymouth-theme tarball, a stray
`.py` script, mis-named files like
`Pearos_fullscreen_non-transparent.png.png.png` and `svg(1).svg`) —
not real distributable content.

Two real license naming footnotes worth keeping: aurorae's and
`pearOS-dark`'s own `metadata.json` files declare their license as
"PPLv2"/"PPL_V2"/"PPL-2.0" (upstream spells it inconsistently across
files) — a non-SPDX identifier ("Pear Public License v2", presumably),
used verbatim in the spec's `License:` tags since that's genuinely what
upstream declares, not independently verified against any actual
license text. `pearos-sounds` has no license information anywhere
upstream at all (no LICENSE file, no metadata.json) — packaged as-is,
flagged rather than guessed.

### Bug found and fixed: ambiguous Python shebang (real COPR build failure)

First COPR build attempt (`11001562`) failed outright:

```
*** ERROR: ambiguous python shebang in
/usr/share/plasma/plasmoids/luisbocanegra.panel.colorizer/contents/ui/tools/service.py:
#!/usr/bin/env python. Change it to python3 (or python2) explicitly.
```

Fedora's `brp-mangle-shebangs` build policy hard-fails `%install` on
any bundled script with a version-ambiguous `#!/usr/bin/env python`
shebang. Checked the rest of the new content for the same pattern
(`grep -rlE "^#!.*env python$"`) — exactly one file affected. Fixed
with a targeted `sed` in `%install` disambiguating that one file to
`python3` without touching anything else. Second build (`11001570`)
succeeded.

### Infra bug found while re-running the ISO build: backgrounded sudo loses its tty

Rebuilding the ISO with the new packages (`branded6`) needed a build
that took past the ~30-minute point (compressing ~110k rootfs files
into squashfs, more than prior builds due to the new content). The
first attempt (`ssh -tt ... sudo bash engine/build-iso.sh`, foreground
over a single pexpect session) was killed when that session's own
30-minute `pexpect.expect(EOF, timeout=1800)` wait expired — the build
was still running at 67% squashfs progress, not actually failed.

Re-launching it detached (`nohup ... & disown`) to survive past any
single SSH session's lifetime hit a **different**, real bug: `sudo:
a terminal is required to read the password`, even after running
`sudo -S -v` first to pre-validate the credential cache — a backgrounded
process loses its controlling tty entirely, and sudo's timestamp cache
is tty-scoped on this system (most sudoers configs are), so a fresh
`sudo` invocation with no tty at all refuses to proceed regardless of
a valid cached ticket. Fixed by using a **detached `tmux` session**
instead (`tmux new-session -d -s branded6 'sudo bash ...'`), which
provides its own real pty that survives independently of any SSH
session, then feeding the password in with `tmux send-keys -t branded6
'alexgalicea' Enter` right after launch. This let the build run to
completion (~1hr total) while being checked on periodically via
`tmux capture-pane`, with no SSH session needing to stay alive for the
duration.

### Verification: rebuilt, boot-tested, partially confirmed visually

Rebuilt the branded ISO (`branded6`) with the tmux approach above.
Verified in the rootfs before boot-testing (same discipline as every
fix this session): all 5 new packages installed at `2026.09.01-2`, and
`/etc/xdg/plasmarc`, `/etc/xdg/kdeglobals`, `/etc/xdg/kwinrc` all show
the expected new lines from `customize.sh` exactly as written.

Boot-tested on the install-test VM: `journalctl` shows the same single known-benign
`Main.qml:406:13: Unable to assign [undefined] to QUrl` warning (the
harmless `config.logo` property, unchanged from the prior SDDM fix) and
nothing new; the SDDM greeter screendump is visually identical to the
already-confirmed-working `branded5` capture — **no regression**.

**Not independently confirmed at the time**: the Aurorae window-decoration
wiring (`theme=__aurorae__svg__pearOS`) is a best-guess based on
standard KWin/Aurorae naming convention (`__aurorae__svg__<install-dir-name>`),
not the aurorae theme's own internal `Id` field (which is actually
`"pearOS-Light"`, a different string — deliberately not used, since
that field is unrelated to how kwin's own decoration KCM resolves an
Aurorae theme on disk). Attempted to reach an actual logged-in desktop
session via the live ISO's "Live System User" account to check this
visually, but a blank-password login attempt (VT-switch + Enter on the
empty password field) did not go through — this account wasn't
actually passwordless the way the root serial-console account is, and
no credential for it was known at the time.

## RESOLVED: live-user login was completely broken (root cause + fix in docs/phase1-findings.md)

Investigated *why* the live user needed a password at all instead of
Fedora's normal one-click live-session login, since that's not just a
testing inconvenience — it would affect every real person booting this
ISO. Root-caused to a missing `livesys_session="kde"` setting that
gates Fedora's own already-installed `livesys-scripts` first-boot
autologin setup; fixed in `engine/build-iso.sh`. Full story (this is a
baseline Phase 1-class bug, not branding) is in
`docs/phase1-findings.md`'s "Late addition" section.

### Aurorae decoration: now fully confirmed, with one live-testing-only wrinkle found

With autologin working, reached a real logged-in Plasma desktop for
the first time this project. Checked the live user's actual runtime
`~/.config/kwinrc` and found `[org.kde.kdecoration2]` only had
`library=org.kde.kwin.aurorae.v2` — **no `theme=` line at all**, and
the library name itself has a `.v2` suffix this project's `customize.sh`
didn't have. Root cause: `livesys-kde`'s own first-login script writes
a **fresh** `~/.config/kwinrc` for the live user via its own heredoc
(for layout/virtual-desktop defaults etc.), which completely overwrites
whatever `/etc/xdg/kwinrc` (this project's own system-wide default,
written by `customize.sh`) would otherwise provide via normal XDG
config cascading. This is a **live-ISO-testing-only** quirk — it's
gated by the same `rd.live.image` kernel-cmdline check as the rest of
`livesys`, so a real Calamares-installed system (Phase 4) won't hit it
at all; `/etc/xdg/kwinrc` will apply normally for a real user's fresh
home directory on an installed system.

To actually verify the decoration renders correctly (not just that the
config key is theoretically right), edited the live session's
`~/.config/kwinrc` directly via the root serial console to add the
`theme=__aurorae__svg__pearOS` line, triggered a live reconfigure
(`dbus-send --dest=org.kde.KWin /KWin org.kde.KWin.reconfigure`, run as
`liveuser` with the right `DBUS_SESSION_BUS_ADDRESS`/`XDG_RUNTIME_DIR`),
then spawned a real GUI window directly into the running Wayland
session (`sudo -u liveuser env XDG_RUNTIME_DIR=... WAYLAND_DISPLAY=wayland-0
dolphin &` — no mouse/keyboard simulation needed, same "drive it via
the real IPC surface instead of fighting simulated input" approach
Phase 0 used for `pearos-dock`).

**Confirmed via screendump**: Dolphin's window renders pearOS's
genuine macOS-style Aurorae decoration — yellow/green/red traffic-light
controls on the *left* side of the titlebar (not KDE's usual
right-side, minimize/maximize/close), rounded corners, a clean
centered title. This is definitively not stock Breeze; the
`__aurorae__svg__pearOS` naming guess was correct all along, and
`customize.sh` has been updated with the confirmed `library=org.kde.kwin.aurorae.v2`
value (previously the unversioned, incorrect `org.kde.kwin.aurorae`)
for real installed users going forward.

The same screendump also incidentally confirmed the rest of the
desktop is fully working and correctly branded: the liquid-gel-style
wallpaper, `PearCalendar`/`PearWeather` desktop widgets rendering with
real data (from the `pearos-plasmoids` package), a macOS-style top
menu bar, and `pearos-dock` at the bottom tracking the open Dolphin
window. This is the first time in the project's history that an actual
rendered pearOS desktop — not just the SDDM greeter — has been visually
confirmed.

Phase 3's "full desktop-session verification beyond just the greeter"
item is now done. The only remaining Phase 3 item is the "unclaimed
content" scope question, which is itself now resolved (see above) —
Phase 3 is effectively complete.
