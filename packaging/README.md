# Packaging (Phase 2 / Phase 3)

RPM `.spec` files for the pearOS-specific pieces that don't exist as Fedora
packages anywhere upstream. **Every spec here is untested** — drafted by
reading the actual upstream source trees (see
[`docs/phase0-findings.md`](../docs/phase0-findings.md) for what was found),
without a Fedora build root available to run `rpmbuild`/`mock` against. Each
file has a banner comment at the top calling out what's confident vs. what
needs verification on a real build.

| Spec | Risk | Notes |
|---|---|---|
| `pearos-liquidgel/` | **High** | KWin ABI drift — the single biggest fidelity risk, see Phase 0 findings |
| `pearos-dock/` | **High** | Links against plasma-workspace's private LibTaskManager/LibNotificationManager libs — sharper build risk than liquid-gel's |
| `pafari/` | Low | Meson/Ninja build, straightforward Fedora `-devel` package mapping |
| `pearos-settings/` | Low | Almost entirely static files |
| `pearos-branding/` | Low | Plain files (icons/GTK/SDDM/wallpapers), no build step |

## Build order

1. `pearos-settings`, `pearos-branding`, `pafari` — no reason these should
   fail; get them building and into the COPR first so `--local`/COPR
   testing of the engine isn't blocked on the two hard ones.
2. `pearos-liquidgel` and `pearos-dock` — the real Phase 0 work. Don't trust
   these specs' `BuildRequires` or `%cmake`/`%files` lines until they've
   actually been run through `mock` (or `dnf builddep` + `rpmbuild`) on a
   Fedora build host, per the open items in `docs/phase0-findings.md`.

## COPR

Once these build cleanly, they're meant to be published to a `pearos/pearos`
COPR repo (referenced as `PROFILE_COPR` in
`profiles/pearos/repo.sh`) — that repo doesn't exist yet. Until it does, use
`engine/build-iso.sh --local` with hand-built RPMs dropped in
`build/local-rpms/`.
