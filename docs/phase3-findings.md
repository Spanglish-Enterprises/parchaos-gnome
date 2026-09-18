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
