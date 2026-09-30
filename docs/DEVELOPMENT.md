# Developing ParchaOS

Notes for contributors and coding agents. The project overview for users
is in the top-level [README](../README.md).

**Status as of 2026-09-26**: installs and runs on real hardware (an AM5
desktop) and in VMs with Secure Boot on. The profile
(`profiles/parchaos/`) ships ParchaOS's own packages on top of the
Fedora base: dock, global menu bar, app launcher, Parcha Controls,
Parcher (the file manager), ParchaOS Settings, session restore, live
Clock and Calendar icons, two visual styles (Glass and Classic),
GTK/icon/Plymouth/wallpaper theming with original ParchaOS icons, a
Chromium-based browser, a keyboard remap, scheduled Do Not Disturb, auto
light/dark, a hosts-file ad-blocker, a live wallpaper and Desktop Icons
NG.

Each package's spec starts with a banner comment explaining what it is,
why it exists and the bugs found building or shipping it; read it before
changing the package. Open work is tracked in the issue tracker.

## What this repo is

ParchaOS is a GNOME desktop built on Fedora Linux. This repository holds
the ISO build engine, the one build profile, and every package ParchaOS
adds on top of Fedora. Where a package is based on someone else's code,
its spec says so and credits the upstream project (see also
`docs/LEGAL.md`).

**Licensing of upstream components**: only package code with a real
LICENSE file behind it. Upstream components without one aren't
packaged; ParchaOS writes its own version instead. Don't rely on a license field in a
PKGBUILD or `DEBIAN/control` alone.

## Layout

```
engine/            Reusable Fedora ISO build engine (dracut, GRUB,
                    xorriso/El Torito, Secure Boot shim signing) —
                    desktop-environment-agnostic, shared with the KDE
                    repo's own history.
profiles/parchaos/  This variant's only profile. packages.list (stock
                    Fedora packages), packages.sh (this project's own
                    31 custom packages, PROFILE_REPO_PACKAGES),
                    customize.sh (branding + dconf defaults),
                    repo.sh, profile.conf.
packaging/          One directory per custom package, each with a
                    real .spec and (where the source isn't fetched
                    from a pinned upstream commit) a files/ tree.
                    Every package's own spec has a banner comment
                    explaining what it is, why it exists, and the
                    real bugs found building/shipping it — read the
                    spec before assuming what a package does.
docs/               LEGAL.md, SOURCES.md, the release notes template.
scripts/lint.sh     The static checks CI runs on every push.
```

## What's actually shipped

**Desktop shell**: `parchaos-dock` (Dash-to-Dock fork, magic-lamp minimize
effect via `parchaos-magic-lamp-effect`), `parchaos-global-menu` (global
menu bar with the About ParchaOS card and weather), `parchaos-launcher`
(full-screen app launcher with folders, search and uninstall),
`parchaos-controls` (Parcha Controls, the control center),
`parchaos-session` (reopens the last session's apps and windows),
`parchaos-live-icons` (live Clock and Calendar icons),
`parchaos-gtk-theme`/`parchaos-icon-theme` (MacTahoe, light and dark,
with original ParchaOS app icons),
`parchaos-gnome-wallpaper`, `parchaos-gnome-plymouth-theme`
(parcha-plymouth boot splash), `parchaos-gdm-logo`, `parchaos-desktop-icons`
(DING), `parchaos-hanabi` (real video wallpaper), plus 8 more
independently-licensed GNOME Shell extensions for polish
(`blur-my-shell`, Just Perfection, No Overview, AppIndicator,
`parchaos-notification-position`, `parchaos-wiggle`,
`parchaos-ui-tune`).

**Apps and settings**: `parcher` (Parcher, a Nautilus fork,
GPL-3.0), `parchaos-settings` (ParchaOS Settings: style, session
restore, Focus schedule, keyboard; also reachable from a ParchaOS panel
in GNOME Settings, `packaging/gnome-control-center/`, a patched Fedora
build the ParchaOS repository is preferred for), `parchaos-browser` ("Parcha Browser": thin Chromium
rebrand and the default web browser; it replaced and Obsoletes `pafari`, the
old WebKitGTK/Epiphany fork), `parchaos-app-renames` (Loupe → Image Viewer,
Clocks → Clock, Geary → Mail, Software → Parcha Store),
`parchaos-cloud` (rclone wrapper, **deprioritized**; being replaced
with ParchaOS's own implementation), `parchaos-focus-schedule`, `parchaos-yin-yang`
(auto light/dark), `parchaos-keyboard-remap` (Super↔Ctrl via xremap),
`parchaos-hblock` (real hosts-file ad-blocker).

**Installer**: `parchaos-gnome-calamares-config` — a real disk install
that boots, with the real partitioning/kernel-install/EFI fixes this
took (BIOS boot partitions,
kernel-install-on-target, EFI System Partition population, a Calamares
app-removal cascade-removal regression caught and fixed twice).

**System**: `parchaos-release` keeps the ParchaOS name, logo and links
in `/etc/os-release` across Fedora updates. `parchaos-welcome` is the
first-login assistant (style, light/dark, Super key, location consent,
a short tour).

**OTA mechanism**: `parchaos-desktop`, a meta-package whose `Requires:`
list names every package above (it also ships the desktop-wide dconf
defaults, the `org.parchaos.desktop` settings schema, the Flathub
remote and the per-user extension migration) — installing/updating it is
what makes a plain `sudo dnf update` on an already-installed system
pick up packages added to this profile after the user's own install,
not just upgrade ones already present. **Must be kept in sync by hand**
whenever `packages.sh`'s `PROFILE_REPO_PACKAGES` changes — bump its
`Release` and add the new `Requires:` line, or a real user's `dnf
update` silently won't pick up the new package. This has bitten this
project's own real hardware more than once.

## Still deferred (explicit user calls, not forgotten)

- Deeper Calamares installer skinning to match the desktop's look (real QML/UI work,
  not started; ParchaOS's own original work).
- Deeper glass effects (refraction, highlights) beyond the blur the
  Glass style uses today (a candidate source: `ryohsuke1231/liquid-glass`).
- `parchaos-cloud`'s replacement (see above).

## Release image gate

`engine/build-iso.sh` runs `scripts/check-image.sh` on the finished
rootfs, just before compressing it. The script writes every installed
package (name, license, vendor) to `build/<iso>.packages.tsv`, which is
published with the ISO, and fails the build if the image contains
something ParchaOS can't redistribute or no longer ships: `openh264`
(Cisco's license only covers downloads from Cisco), `fedora-logos`
(Fedora's logos are for official Fedora media), any package built by RPM
Fusion other than its repo definitions, or `pafari`, `pearos-*`,
`parchaos-finder`, `parchaos-macos-remap`, `parchaos-tmog`. It also fails
if `noopenh264` or `parchaos-logos` is missing. `--skip-branding` test
builds skip it.

The swap itself is in `profiles/parchaos/customize.sh`. Cisco's
`openh264` obsoletes `noopenh264`, and dnf honors that for the installed
package too, so the profile removes `openh264` with `rpm -e --nodeps`
and then installs `noopenh264` with the Cisco repo disabled, in a single
container call.

## Test rigs must never touch the real desktop's settings

A headless-shell test rig once wrote to a real desktop's settings (2026-09-29).
It set `HOME` and `XDG_CONFIG_HOME` inside the script that `dbus-run-session`
runs. The private bus daemon had already started with the real environment, so
the settings service it activated (`dconf-service`) inherited that real
environment and wrote to the real `~/.config/dconf/user`: `dconf reset -f /`,
extension lists and test values all landed on the live desktop.

Rules for any script that runs a shell or a settings tool in a private bus:
- Set the environment before `dbus-run-session`, for example
  `env -u DBUS_SESSION_BUS_ADDRESS HOME=... XDG_CONFIG_HOME=... XDG_RUNTIME_DIR=...
  dbus-run-session -- bash rig.sh`. `scripts/smoke-test.sh` does this.
- Before the first `dconf` or `gsettings` write, check that the private bus
  daemon carries the sandbox `XDG_CONFIG_HOME` (read `/proc/<pid>/environ`) and
  refuse to run if it does not.
- Prove it once for every new rig: `dconf dump / | md5sum` on the real desktop
  before and after a run must match.
- A write to the real settings that silently does nothing means the running
  `dconf-service` holds a stale copy of the file; restarting it (it restarts on
  demand) fixes that.

## Release size limit

GitHub rejects release assets of 2 GiB (2,147,483,648 bytes) or more, and
the ISO is published as one asset. The 2026.09.29 ISO is 1,983,823,872
bytes (1.85 GiB), about 160 MiB under the limit. Before building the ISO
for a release:

- Compare the size with the previous release's (`ls -l build/*.iso`) and
  find out what grew if it is more than about 50 MiB larger.
- `engine/build-iso.sh` prints a NOTE from 1.9 GiB (1946 MiB) and a
  WARNING at 2 GiB. Treat either as a stop: do not tag the release.
- Ways to get back under it: drop a package from `profiles/parchaos/
  packages.list`, keep a language pack or a large Flatpak runtime out of
  the image, or lower the squashfs cost by removing files the live session
  doesn't need. Do not split the ISO.
- The GPL source tarballs are already split under 1.9 GiB each
  (`scripts/collect-sources.py`).

## Release source code (GPL)

Every release publishes the complete corresponding source of its ISO as
GitHub release assets (owner decision, 2026-09-26). On the build host,
after the ISO build:

    scripts/collect-sources.py build/rootfs-parchaos-44 build/sources --prefix <iso-name>

It reads each installed package's source RPM from the rootfs, downloads
Fedora's from Koji (which keeps every build) and ParchaOS's from the
matching COPR build, and writes `<iso-name>-sources-NN.tar` archives
(under 2 GiB each) plus `<iso-name>-sources.sha256`. Upload those with
the ISO. `docs/SOURCES.md` (installed as /usr/share/doc/parchaos/SOURCES.md)
and `docs/release-notes-template.md` carry the written offer; source
requests come in through the parchaos.org/support form ("Question",
titled "Source code request").

## Public surface audit

`scripts/public-surface-audit.sh` (read-only) lists the COPR projects,
their packages and what the repo metadata actually serves, plus the
GitHub repositories, releases and release assets of the owner accounts.
It flags removed or third-party material (pearOS, Pafari, Finder,
macOS-remap, TMOG, pre-rewrite global-menu and cloud builds) and
ParchaOS-related repositories that are public by mistake. Run it before
every release.

## COPR publishing (terms check, account, descriptions) — ticket #105

Checked 2026-09-28 against COPR's own User Documentation / FAQ
(<https://docs.copr.fedorainfracloud.org/user_documentation.html#faq>) and
Fedora's licensing lists.

### What COPR actually requires

COPR states that packages there **do not need to follow the Fedora
Packaging Guidelines**, though they are recommended to. The stated
requirements are:

1. you have the right to upload the material (no third-party rights
   infringed);
2. every license involved is on Fedora's **allowed list**
   (<https://docs.fedoraproject.org/en-US/legal/allowed-licenses/>);
3. nothing involved is on Fedora's **not-allowed list**
   (<https://docs.fedoraproject.org/en-US/legal/not-allowed-licenses/>);
4. the package does not abuse the build system;
5. it breaks no Fedora rule — chiefly the Code of Conduct — and no law.

Plus: **you are responsible for the licenses and for the resulting
repository being legally public**, and COPR suggests naming the license in
the description.

### Compliance result: checked, passes

Every distinct identifier in all 37 `License:` fields in
`packaging/*/*.spec` was looked up in Fedora's allowed list **as a table
entry** (not a prose mention) and in the not-allowed list:

| Shipped | Allowed-list entry? | Not-allowed entry? |
|---|---|---|
| `GPL-3.0-or-later`, `GPL-3.0-only`, `GPL-2.0-only`, `GPL-2.0-or-later`, `LGPL-3.0-or-later` | yes | no |
| `MIT`, `Apache-2.0`, `BSD-3-Clause`, `BSL-1.0`, `Unicode-3.0`, `Unlicense` | yes | no |
| `CC-BY-SA-4.0`, `CC0-1.0` | yes | no |

The `AND`/`OR` combinations are built from those same identifiers. Three
strings do appear on the not-allowed page — but only **inside longer
identifiers or prose** (`LicenseRef-GPL-2.0-or-later-WITH-UPX`,
`LicenseRef-MIT-CRL-Xim`, `BSD-3-Clause-Clear`); none of them is a
not-allowed entry.

### Prebuilt binaries (the xremap question)

`parchaos-keyboard-remap` ships `xremap-linux-x86_64-full.zip` straight from
upstream's release — a prebuilt binary, `%build` compiles nothing. That is
**permitted by COPR's terms**: the guidelines exemption above means the
Fedora "no prebuilt binaries" packaging rule does not apply, and what
matters is requirement 2. The binary is MIT, its sibling `xremap-gnome`
component is GPL-2.0-or-later, and the statically linked Rust crates are
enumerated — all on the allowed list. The package already ships
`THIRD-PARTY-LICENSES.md`, `xremap-crate-licenses.txt` and upstream's own
`LICENSE` as sources, which covers COPR's "state the license" suggestion.

### Descriptions are neutral (done)

`%description` is what `rpm -qi` and `dnf info` show, and it is the field
COPR suggests reading for licensing. Ten specs had grown internal
build-diligence notes and lineage wording toward other distributions —
`parchaos-desktop-icons`, `parchaos-dock`,
`parchaos-gnome-calamares-config`, `parchaos-gtk-theme`,
`parchaos-hanabi`, `parchaos-hblock`, `parchaos-magic-lamp-effect`,
`parchaos-ui-tune`, `parchaos-wiggle`, `parcher`. All ten were rewritten to
describe the software for a user; upstream project credit (authors and
licenses) is retained, but no other distribution is named as an ancestor.
The same applies to the one user-facing extension description that named
another distribution — Parcha Dock's shipped `metadata.json` — where full
provenance stays in `original-author`, its dedicated credit field.

**Going forward:** `Summary:` and `%description` describe what the package
does and credit the *upstream project*; they do not narrate how the package
was built, where the diligence notes live, or which other distribution the
work resembles. Those belong in spec comments and `%changelog`.

### Account decision — owner call, still open

Item 2 (move the update COPR to a group/organization account, or self-host
a signed repo) is **not something this agent can decide or execute** — it
needs FAS account access and an owner decision. If it is decided, the
repoint is small and mechanical:

1. `profiles/parchaos/repo.sh` — `dnf copr enable -y "$PROFILE_COPR"`.
2. The shipped repo file `80-parchaos-copr.repo` (release package), which
   carries the baseurl and `metadata_expire`.
3. `scripts/public-surface-audit.sh`, which reads the project names to
   audit them.

Change all three together, keep the old name alive with a redirect for one
release, and rebuild `parchaos-release` last so installed systems pick up
the new baseurl.


## License

- **Code, packaging and docs** written for ParchaOS: **GPL-3.0-or-later**
  (`LICENSE`). Chosen to match the GPL code this project forks and ships
  (Nautilus/Parcher, Dash-to-Dock/Parcha Dock, several GNOME Shell
  extensions), so everything combines cleanly.
- **Original ParchaOS artwork** (e.g. the app icons in
  `packaging/parchaos-icon-theme/parchaos-icons/`): **CC BY-SA 4.0**
  (`LICENSE-ARTWORK`).
- **Third-party components keep their own licenses**, declared in each
  package's spec `License:` field (for example the MacTahoe-based themes
  and xremap). The ParchaOS logo is original artwork, generated by
  `branding/logo/make-brand.py` (see `branding/logo/CREDITS.md`).

## Naming policy (trademark caution)

ParchaOS is meant to ship publicly, so Apple's names stay out of anything
we name or write ourselves: package names, app/feature names, package
summaries/descriptions, and docs prose. Describe the feature instead (dock,
global menu bar, traffic-light window controls, hover magnification,
Super-as-Ctrl) or say "the reference desktop". Its key names and symbols
count too: the remapped key is Super, never "Cmd" or the command symbol.
Renamed so far:
`parchaos-macos-remap` -> `parchaos-keyboard-remap`, "Finder" -> "Parcher",
Software -> "Parcha Store" ("App Store" is itself a trademark). Approved names for
upcoming features: Parcha Time (backups), Parcha Controls (control center),
ParchaOS Recovery.

Approved display names for renamed stock apps (owner-picked, ticket #101):
**Parcha Preview** (Loupe), **Clock** (GNOME Clocks), **Parcha Mail** (Geary),
**Parcha Store** (GNOME Software); plain stock names kept as-is: **Terminal**,
**Text Editor**, **Weather**, **Screenshot**, **System Monitor**, **Disks**.
Rule: a renamed stock app either gets a **Parcha-prefixed brand name** or stays
a plain English word — never another vendor's app name (the bare "Preview" and
"Mail" were replaced on 2026-09-27 for this reason). Brand names also drop
their translated `Name[xx]=` lines so every language shows the same brand.
New renames must be added here when they are approved.

Still needing a ParchaOS name before it's built: system-wide search.

Deliberately kept: upstream project names and URLs (e.g. `MacTahoe` --
confirmed by the project owner 2026-09-25 to stay as-is, credited, not renamed;
`gnome-macos-remap-wayland`, Pulsar OS's own "Finder"), because renaming
them would misstate where the code came from; old names that
`Obsoletes:`/changelogs need; and direct quotes. This is risk reduction,
not legal clearance -- get a real legal review before a public launch.

## A note on working style, for any agent picking this up

**Verify against real hands-on results, not assumptions.** This
project's whole history is one long demonstration that "should work" claims
hide real bugs: a missing RPM `Release` bump silently no-op'ing a fix,
an RPM `Epoch` mismatch quietly defeating a `Provides`/`Obsoletes`
declaration, a build-time macro getting expanded inside what was meant
to be a plain shell comment, a package's own install script silently
skipping a step because a build sandbox lacked a binary it assumed was
present, a license field in a PKGBUILD with no real LICENSE file behind
it. Every one of these was caught by actually building it, installing
it on real hardware, and reading the real output — not by asking
whether it should work. Do the same. Check licenses against a real
LICENSE file, not a claim. Check real package/service state with real
commands, not memory. Build it, install it, run it, and look at a real
screenshot (or a real `dnf`/`systemctl`/`gsettings` result) before
calling something done.

## Recovery: the desktop won't start after an update

If an update leaves you without a working login screen or desktop (ticket
#115), start once in safe mode. It turns every GNOME Shell extension off for
that boot, so you get stock GNOME, can log in, and can fix or roll back the
update.

1. Restart the computer. At the GRUB menu, highlight the ParchaOS entry and
   press `e`.
2. Go to the line that starts with `linux`, move to its end, and add a space
   and `parchaos.safe-mode`.
3. Press `Ctrl-X` to boot.

Nothing needs to work for this, not the desktop, not a login. Safe mode lasts
one boot: the next normal start removes it again
(`/usr/libexec/parchaos-safe-mode`, run by `parchaos-safe-mode.service` before
the display manager on every boot). Check it took effect with
`journalctl -t parchaos-safe-mode -b`.

## Checking the next Fedora release without root

A GNOME Shell of the next Fedora release can be run headless from a plain
directory, so the smoke test (`scripts/smoke-test.sh`) can be tried against it
before the release is out. Nothing here touches the real desktop: the tree has
its own session bus and settings, and `bwrap` keeps it away from the host.

1. Download the packages with `dnf5 --releasever=NN download --alldeps
   --resolve gnome-shell mutter gjs dbus-daemon dconf python3 ...` (see the
   list in the ticket), plus the ParchaOS packages from the COPR repo for that
   release (`--repofrompath` with the `fedora-NN-x86_64` results URL).
2. Unpack every x86_64 and noarch RPM into one directory with
   `rpm2cpio | cpio -idmu`, making directories writable between packages
   (`find . -type d ! -perm -u+w -exec chmod u+w {} +`).
3. Run things with `bwrap --bind TREE / --dev /dev --proc /proc --tmpfs /tmp
   --tmpfs /run ...`, with a small `/etc/passwd` and `/etc/group` bound in, a
   second private D-Bus daemon on `/run/dbus/system_bus_socket` (exported as
   `DBUS_SYSTEM_BUS_ADDRESS`), and `glib-compile-schemas` run once inside.
4. Two things fail there for reasons of the sandbox, not ParchaOS: image
   loading (the release's loaders run in a sandbox of their own, which cannot
   start inside `bwrap`) and the document portal (no FUSE).

Findings for Fedora 45 (GNOME Shell 51) are in ticket #37.
