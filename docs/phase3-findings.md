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

## Not yet done: an actual branded ISO build

Every ISO build attempted this session used `--skip-branding`, since
that was Phase 1's deliverable (the plain unbranded baseline). **A real
branded build (`engine/build-iso.sh` without `--skip-branding`) has
never been attempted.** Now that the COPR-slug bug above is fixed, this
is the natural next real test — Phase 2/3's packages need to actually
survive a real `dnf copr enable` + `dnf install` inside the engine's
`dnf --installroot` bootstrap and a real boot to prove the wiring
works end-to-end, the same "verify on real hardware" bar used for
everything else in this project.

**Next step for whoever continues**: once build `11000859` is confirmed
green, run `engine/build-iso.sh --profile pearos --branch 44` (no
`--skip-branding`) on the build VM, boot it the same way Phase 1 verified the
unbranded ISO (serial console + QMP screendump), and check for a real
pearOS-branded SDDM greeter and desktop instead of stock Breeze. This
will very likely surface new, real bugs — the same "manual verification
missed something rpmbuild caught" pattern from Phase 2 should be
expected here too (e.g. a package name mismatch between
`PROFILE_REPO_PACKAGES` and what COPR actually publishes, a `dnf
--installroot` GPG-signing hiccup enabling an external COPR, etc.) —
don't assume it'll boot clean on the first try.
