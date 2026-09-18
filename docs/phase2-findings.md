# Phase 2 findings — COPR package repo prep

Phase 2 (per `README.md`) is: "COPR repo for anything not in Fedora's
official repos; `.spec` files for `liquid-gel`, `pafari`,
`pearos-settings`, `pearos-dock` (drafted in `packaging/`, untested
against a real Fedora build root — see the banner in each spec)."

Two things are bundled under that one line: (1) the specs actually being
correct, and (2) a COPR project existing to build them in. This session
made real progress on (1) but could not touch (2) — creating a COPR
project needs the *user's own* Fedora account and API token, which this
environment doesn't have and shouldn't try to obtain or work around. See
"What the user needs to do" at the bottom.

## Spec verification — real bugs found and fixed

Every "verified" claim in the existing spec banners (`pearos-dock`,
`pearos-liquidgel`) turned out to describe a **manual** compile
verification (checking out source by hand, running `cmake`/`meson`
directly) — none of the five specs had ever actually been round-tripped
through `rpmbuild` itself. That gap is exactly where packaging-specific
bugs (`Source0`, `%prep` directory naming, `%files` completeness) hide,
since they're invisible to a manual build. Checked all five for real
this session by downloading the actual upstream tarballs and comparing
against what each spec assumes — no VM needed for this part, just `curl`
+ `tar t` + `gh api` against the real GitHub repos.

| Spec | Issue found | Fix |
|---|---|---|
| `pafari.spec` | **Missing `Source0` entirely** despite `%prep` using `%autosetup` — would fail immediately. Also `%autosetup -n pafari-%{version}` wouldn't match the real extracted dir. | Added `Source0` (GitHub `main` branch archive, confirmed real default branch via `gh api`). Fixed `%autosetup -n pafari-main` (verified real tarball extracts to `pafari-main`, not `pafari-26.8`). |
| `pearos-settings.spec` | **Missing `Source0` entirely**, same `%autosetup` dir-mismatch. **Also**: `%install` blanket-copied the *entire* upstream `usr/` tree into the buildroot while `%files` only declared two paths (plymouth theme + Kvantum) — upstream's real tree also ships kwin effects (55 files), a full Plasma desktop theme (1392 files!), aurorae window decorations, sounds, color-schemes, and an "extras" dir, none of which any spec in this project currently claims. Would have failed as "installed but unpackaged files." | Added `Source0`, fixed `%autosetup -n pearos-settings-main`. Narrowed `%install` to only copy what `%files` actually declares (skel, scripts, plymouth theme, Kvantum) instead of the whole tree. **Left the big open question below rather than guessing at package ownership.** |
| `pearos-liquidgel.spec` | Had `Source0`, but `%autosetup -n liquid-gel-%{version}` (expects `liquid-gel-26.7`) doesn't match what a GitHub branch-archive tarball actually extracts to (`liquid-gel-main`) — confirmed by downloading the real tarball. This was invisible to the earlier manual-compile verification since that never went through `rpmbuild`'s `%prep` at all. | Fixed `%autosetup -n liquid-gel-main`. |
| `pearos-dock.spec` | Checked — correct already. Its Source0/`%autosetup -n pkgbuilds-main` was written to match the monorepo's real extraction name (`pkgbuilds-main`, since the upstream repo is literally named `pkgbuilds`), and that's exactly what the real tarball produces. | None needed. |
| `pearos-branding.spec` | Checked its manual four-source `%setup -q -T -c` pattern — correct in general (uses an explicit container dir + individual extraction rather than relying on tarball-name matching, so it doesn't have the `-main`-vs-`-version` bug the others had). **But**: `Source1` (`pearOS-Default-GTK-Theme`) pointed at `archive/refs/heads/main.tar.gz` — that repo's real default branch is **`master`**, not `main` (confirmed via `gh api repos/.../pearOS-Default-GTK-Theme --jq .default_branch`, and by downloading the "main" URL directly: it returns a 14-byte GitHub error page, not a tarball). | Fixed `Source1` to `master.tar.gz` and every `pearOS-Default-GTK-Theme-main` reference in `%install`/`%files` to `-master`. Confirmed the other three sources (Icons, SDDM, Wallpapers) really do use `main` and really do extract to `-main` — no change needed there. |

All five specs now have a `Source0`/extraction-dir pair that's been
confirmed against a real download, not assumed. **Not yet confirmed via
an actual `rpmbuild -bp`/`-bb` run** — see the blocker below.

## Blocker: the build VM's `rpm-build` install is blocked by a real system issue

Wanted to close the loop by actually running `rpmbuild -bp` (prep-only:
source extraction + patch application) for all five specs on the build VM, the
same real-hardware-verification discipline used for every other claim
this session. Couldn't get there:

- `sudo dnf install -y rpm-build` fails immediately: `Problem: The
  operation would result in removing the following protected packages:
  systemd, systemd-udev`.
- Root cause, confirmed via `rpm -q systemd systemd-udev`: **the build VM's
  host OS has two versions of `systemd`, `systemd-udev`, and
  `systemd-networkd` installed simultaneously** (`259.5-1.fc44` and
  `259.9-1.fc44` of each) — a genuinely broken/inconsistent package
  database, unrelated to anything this session's `rpm-build` request
  did. This is the same *class* of problem as the `kmime`/`kf6-kmime`
  duplicate-version conflict documented in `docs/phase0-findings.md`
  earlier this session, just hitting `systemd` this time instead.
- The correct, standard fix is `dnf distro-sync` (designed exactly for
  "installed packages don't match a consistent repo state"), and
  `sudo dnf distro-sync --exclude=systemd-udev --assumeno` previewed a
  **clean, resolvable** transaction (34 upgrades, 37 replacements, one
  package — `systemd-networkd` — safely skipped rather than forced).
  This is not a guess; it's a verified-clean dnf plan.
- **But this session's tooling declined to run it**: applying it is a
  ~522MB download that touches 71 packages on the live dev/test VM, and
  the auto-mode safety classifier blocked executing it unattended. That
  judgment seems right — this isn't a one-line fix, it's a real system
  update to a box that's actively relied on for future compile testing,
  and it deserves a human's explicit go-ahead rather than being run
  silently in the background. I did not attempt to route around this
  via a narrower dnf invocation beyond one reasonable-to-try smaller
  option (`dnf install rpm-build --exclude=systemd-udev`, previewed
  only, also fails cleanly for the same underlying reason) — see below
  for what the user needs to do.

**What the user needs to do** (only remaining step to unblock real
`rpmbuild` verification on the build VM): SSH into the build VM (`<vm-address>`,
user `<user>`) and run:

```
sudo dnf distro-sync --exclude=systemd-udev -y
```

This was already previewed clean (see above) — it upgrades ~34
packages (mostly firmware + wireplumber) and safely skips the one
conflicting package (`systemd-networkd`) rather than forcing anything.
Once that's done, `sudo dnf install -y rpm-build` should succeed, and
whoever continues this work can run `rpmbuild -bp`/`-bb` for real
against all five fixed specs.

## Open design question: unclaimed pearOS-settings content

Noted in the `pearos-settings.spec` banner too, repeating here since
it's a real Phase 3 scoping question, not just a packaging detail:
upstream's `pearos-settings` repo ships a lot of visual-identity content
that **no spec in this project currently packages**:

- `usr/share/kwin/effects/` — 55 files, custom KWin window-manager
  effects (separate from `liquid-gel`, which is just the blur effect).
- `usr/share/plasma/desktoptheme/` — **1392 files**, a full Plasma
  desktop theme (icons, dialog chrome, etc. for both light and dark
  variants).
- `usr/share/aurorae/themes/` — window-decoration (titlebar) theme.
- `usr/share/sounds/`, `usr/share/color-schemes/`, `usr/share/extras/`
  — sound theme, KDE color schemes, and misc assets (wallpapers, boot
  sound, icons).

None of this overlaps `pearos-branding.spec`, which only covers
icons/GTK-theme/SDDM-theme/wallpapers from its own four *separate*
dedicated upstream repos. Whether this belongs folded into
`pearos-settings`, split into new packages (e.g. `pearos-kwin-effects`,
`pearos-plasma-theme`), or is intentionally left out is a real scope
decision — I didn't invent an answer and narrowed `%install` to avoid
accidentally shipping it half-packaged. Worth deciding explicitly before
or during Phase 3 (branding layer), since it directly affects that
phase's scope.

## COPR project: created and authenticated (2026-09-18)

Done — no longer blocked:

- Project created: `alexgalicea/plumos` (numeric ID 259140), chroot
  `fedora-44-x86_64` enabled.
- API token generated and placed at `~/.config/copr` on the build VM (not
  committed anywhere in this repo — treat it as a live secret).
- `copr-cli` installed on the build VM (`sudo dnf install -y copr-cli` — pure
  Python package, did **not** hit the systemd/systemd-udev protected-
  package conflict below). Auth confirmed: `copr-cli whoami` →
  `alexgalicea`.

**One remaining blocker before the first real build**: submitting a
build normally means handing `copr-cli build alexgalicea/plumos
<srpm>` a locally-built SRPM (`spectool -g` to fetch each `Source0`,
then `rpmbuild -bs`) — and `rpmbuild`/`rpm-build` is still blocked by
the exact same the build VM systemd/systemd-udev duplicate-version issue
described above. So the **only remaining step** for Phase 2 is the
`sudo dnf distro-sync --exclude=systemd-udev -y` command already
previewed clean above — once that's run, `sudo dnf install -y
rpm-build` will succeed, and building + submitting real SRPMs for the
5 fixed specs is the very next thing to do.

## Summary

- 4 real, concrete spec bugs found and fixed via real-upstream-tarball
  verification (no VM needed for this part): 2 missing `Source0`s, 2
  `%autosetup` directory-name mismatches (one of them in a spec
  previously marked "verified"), 1 wrong branch name, and a `%files`
  gap in `pearos-settings` that would have failed the build outright.
- Full `rpmbuild -bp`/`-bb` confirmation is blocked on a real the build VM
  system issue (duplicate systemd package versions) that needs the
  user's explicit approval to fix (`sudo dnf distro-sync
  --exclude=systemd-udev -y`, already previewed clean).
- COPR project creation needs the user's own Fedora/COPR account and
  API token — not something this environment can do or fake.
- One real open design question (unclaimed `pearos-settings` visual
  content) flagged for a human decision before Phase 3 rather than
  guessed at.
