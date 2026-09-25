# Phase 2 findings — Pulsar OS packaging licensing audit

Date: 2026-09-24. Follows on from `gnome-phase1-findings.md` (real-hardware
boot/network/clock crisis, now closed). This phase's task list item was
"is `pulsaros-timemachine` safe to package next" — checking turned into a
full licensing audit of every remaining "real, substantial from-scratch
port" in the README's roadmap, because the first check (Time Machine)
turned up the same missing-LICENSE pattern already found for Sayri, and it
was worth confirming how far that pattern actually extends before writing
any more packaging code.

## The check, and why it matters

This project's own stated convention (README.md, "A note on working
style") is "verify against real hands-on results, not assumptions." The
specific assumption that needed checking here: a PKGBUILD's `license=(...)`
field, or a Debian `control` file's absence of one, is not itself proof of
what license actually covers a piece of code. GitHub (and any real legal
reading) looks for an actual LICENSE/COPYING file in the repository; absent
one, the default is full copyright with no permissions granted, no matter
what a build script's metadata comment claims. This is exactly the gap that
already blocked Sayri (documented in `gnome-phase0-findings.md`): its
PKGBUILD/README implied a license, but `Inled-Pulsar-OS/sayri`'s own GitHub
API record shows `license: null` — no LICENSE file exists.

The question for this phase: is Sayri a one-off gap, or does it extend to
the other components on the from-scratch-ports list? Checked each one the
same way — via direct `curl` against the GitHub API and raw file content
(not `WebFetch`, which gave two contradictory license summaries for the
same underlying Time Machine PKGBUILD in one back-to-back pair of calls
during this session — a live demonstration of why this project doesn't
trust secondhand summaries for facts like this).

## Results

| Component | Repo location | PKGBUILD/control claims | Real LICENSE file? | Status |
|---|---|---|---|---|
| **Finder** (Nautilus fork) | standalone repo `Inled-Pulsar-OS/finder` | (fork of GPL-3.0 Nautilus) | **Yes** — GitHub API confirms `license: gpl-3.0`, real `LICENSE` file present at repo root | **Clear to port** |
| **Sayri** | standalone repo `Inled-Pulsar-OS/sayri` | implied, unclear | **No** — `license: null` | **Blocked**, already known (Phase 0) |
| **pulsaros-timemachine** | monorepo `Inled-Pulsar-OS/PKG`, path `pulsaros-timemachine/` | PKGBUILD: `license=('GPL3')`; `DEBIAN/control` doesn't mention license at all | **No** — no LICENSE file at repo root or in the `pulsaros-timemachine/` subdirectory; repo-wide GitHub API license is `null` | **Blocked** |
| **pulsaros-welcome** | monorepo `Inled-Pulsar-OS/PKG`, path `pulsaros-welcome/` | PKGBUILD: `license=(custom)` — no custom license text exists anywhere to say what that means | **No** | **Blocked** |
| **pulsaros-cloud** | monorepo `Inled-Pulsar-OS/PKG`, path `arch/pkgbuilds/pulsaros-cloud/` (source lives alongside the PKGBUILD itself here, not in a sibling top-level dir) | PKGBUILD: `license=(GPL-3.0-or-later)` | **No** — same repo-wide `license: null` | **Blocked** |
| **gnome-macos-remap-wayland** | standalone repo `Inled-Pulsar-OS/gnome-macos-remap-wayland` (PKGBUILD also present in the monorepo, references this external repo as its real source) | PKGBUILD: `license=(custom)` | **No** — `license: null` on the standalone repo itself | **Blocked** |

Five of six checked components are blocked. The pattern: **anything that is
a fork of an established, clearly-licensed upstream project (Nautilus)
carries a real license forward and is fine.** Anything that is Inled's own
original work — regardless of what a PKGBUILD comment claims, regardless of
whether it lives in the shared monorepo or has its own standalone repo —
has no actual license file anywhere. This isn't a per-package oversight;
it's consistent across five separate directories/repos with three
different claimed licenses (GPL3, GPL-3.0-or-later, custom), which points
to it being a real gap in Inled's own release process rather than
random chance.

## What this means for this project's roadmap

None of these five can be legally repackaged and redistributed as part of
ParchaOS GNOME without Inled's explicit permission — a PKGBUILD saying
`license=('GPL3')` is a statement of intent, not a grant, absent a real
LICENSE file or other written permission to back it up. This is not a
technical blocker (the code itself, where inspected, looks straightforward
to port) — it's purely a "we don't have the right to redistribute this"
gap, same as Sayri's already-documented status.

**Not blocked, no change**: `Finder` (real GPL-3.0, confirmed, matches the
README's existing "approved, in-progress" status — that call was correct).
DE-agnostic carryovers from the KDE repo (`engine/build-iso.sh`,
`packaging/pearos-calamares-config`, `parchaos-focus-schedule`,
`parchaos-yin-yang`) are this project's own original work or already-cleared
Calamares upstream, unaffected by any of this.

**Recommendation, not yet acted on** (this needs the user, not me — it's
outreach to a third party, same as Sayri): a single message to Inled
(`info@inled.es`, the maintainer contact listed in every PKGBUILD checked
here) covering all five components at once, since they're all the same
ask ("can we get a real LICENSE file or written permission to redistribute
X, Y, Z as part of a derivative Fedora spin") rather than five separate
emails. Until that's answered, this project's remaining porting work should
focus on Finder (genuinely unblocked) and the DE-agnostic carryovers that
don't touch any of this.

**Retroactive compliance flag, 2026-09-24**: `parchaos-cloud` (this
profile's rclone/cloud-drives wrapper) was already packaged and shipped
-- installed and process-verified on real hardware -- *before* this
licensing audit existed. It's built from `pulsaros-cloud`, one of the
five components in the table above, which has the exact same
no-LICENSE-file gap. This wasn't caught at the time because the license
audit habit only started with Sayri, after `parchaos-cloud` had already
shipped. **Decision (2026-09-24, user directed)**: leave it installed
for now rather than pull it, but it's deprioritized -- no further work
goes into Pulsar's version, and ParchaOS's own from-scratch replacement
is the intended long-term path once there's time to build one, not
something contingent on Inled's answer either way.

## What's verified vs. what still needs a human

- Verified via direct `curl` against GitHub's REST API and raw file
  content (not `WebFetch` summaries) for every row in the table above.
- Not yet done: actually emailing Inled — that's the user's call to make
  and send, not something to draft or send unprompted.
- Not yet done: re-checking `pulsaros-global-menu`, `pulsaros-theme`,
  `pulsaros-dock` (the "needs full replacement" theme/dock components) for
  the same gap — those weren't in scope for this pass (the "from-scratch
  ports" list specifically), but given how consistent this pattern turned
  out to be, they're worth the same check before any packaging work starts
  on them either.
