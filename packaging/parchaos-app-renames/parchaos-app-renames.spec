# ==============================================================================
# Cosmetic display-name overrides for stock GNOME apps whose icons are
# already covered by the ParchaOS icon theme this profile ships (the
# original artwork replaces the MacTahoe theme's Apple-look icons), but
# whose GNOME-project display NAME doesn't match the short, familiar app
# name this desktop should show. Calculator/Calendar/Weather/Contacts
# already have short names as-is -- only Loupe, GNOME Clocks, and Geary
# needed a rename here.
#
# Mechanism: %post sed on the real installed .desktop file, not a
# replacement file shipped in %files -- shipping a file at the exact same
# path as one already owned by loupe/gnome-clocks/geary would be an RPM
# file conflict. Requires(post) on each target package guarantees dnf
# orders this package's %post after that file actually exists in the
# transaction. %postun intentionally does NOT revert the rename on
# removal of this package -- if this package is removed but
# loupe/gnome-clocks/geary stay installed, leaving the friendlier name in
# place is harmless, and reverting it would need to distinguish "user
# never touched it" from "user customized it further," which isn't worth
# the complexity for a cosmetic rename.
#
# Amberol (Music.app equivalent) deliberately NOT included here --
# confirmed via `dnf list --available amberol` on real hardware that it
# has no native Fedora RPM at all (GNOME Circle apps are often
# Flatpak-only). Renaming it would need a different mechanism (a Flatpak
# override, not an RPM %post), and this profile's ISO build doesn't
# currently pre-seed any Flatpak apps at build time -- flagged as a
# separate, not-yet-started piece of work, not silently skipped.
# ==============================================================================

Name:           parchaos-app-renames
Version:        1.0.0
Release:        11%{?dist}
Summary:        ParchaOS display-name overrides for stock GNOME apps (Parcha Preview, Clock, Parcha Mail, Parcha Backup)

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source90:       LICENSE
BuildArch:      noarch

Requires(post): loupe
Requires(post): gnome-clocks
Requires(post): geary
Requires(post): deja-dup
Requires(post): seahorse
# Deja Dup uses restic by default, and Fedora's package does not require it.
Requires:       restic
# Backups to a network share (SMB/Windows share, NAS) go through GVFS.
Requires:       gvfs-smb
Requires:       gvfs-nfs
Requires(post): sed

%description
Renames a handful of stock GNOME apps' launcher display names to their
short, familiar names (Loupe -> Parcha Preview, GNOME Clocks -> Clock, Geary ->
Mail), via a %post sed on the real installed .desktop file. Their icons
already come from the ParchaOS icon theme with no changes needed -- see
this spec's own banner comment for the full reasoning and what was
deliberately left out (Amberol/Music, no native Fedora RPM).

%prep
cp -p %{SOURCE90} .

%build

%install
mkdir -p %{buildroot}%{_libexecdir}
cat > %{buildroot}%{_libexecdir}/parchaos-app-renames <<'RENAMES'
#!/bin/sh
# Re-applies ParchaOS display names to stock apps' .desktop files. Each
# sed is limited to the main [Desktop Entry] section (before the first
# "[Desktop Action"), so action names like "New Window" stay untouched.
apps=/usr/share/applications
rename() { # file name generic
    [ -f "$apps/$1" ] || return 0
    sed -i "0,/^\[Desktop Action/{s/^Name=.*/Name=$2/;s/^GenericName=.*/GenericName=$3/}" "$apps/$1"
}
rename org.gnome.Loupe.desktop 'Parcha Preview' 'Image Viewer'
rename org.gnome.clocks.desktop 'Clock' 'Clock'
rename org.gnome.Geary.desktop 'Parcha Mail' 'Mail Client'
rename org.gnome.Software.desktop 'Parcha Store' 'Software Store'
rename org.gnome.DejaDup.desktop 'Parcha Backup' 'Backup Tool'
rename org.gnome.seahorse.Application.desktop 'Parcha Keys' 'Passwords and Keys'
# The Parcha-prefixed names are brand names: drop the translated Name[xx]=
# lines in the main section so every language shows them, not a translated
# "Preview"/"Mail" (the same rule this package already applied to
# "Parcha Store"). Plain words like "Clock" keep their translations.
for brand in org.gnome.Loupe org.gnome.Geary org.gnome.Software org.gnome.DejaDup org.gnome.seahorse.Application; do
    [ -f "$apps/$brand.desktop" ] && \
        sed -i '0,/^\[Desktop Action/{/^Name\[[^]]*\]=/d}' "$apps/$brand.desktop"
done
exit 0
RENAMES
chmod 0755 %{buildroot}%{_libexecdir}/parchaos-app-renames

%files
%license LICENSE
%{_libexecdir}/parchaos-app-renames

%post
# Real bug found 2026-09-24, fixed here: an earlier version of this sed
# had no line-range restriction, so on org.gnome.Geary.desktop (which,
# unlike Loupe/Clocks, has [Desktop Action ...] blocks for "Compose
# Message" and "New Window") it clobbered THOSE actions' own Name= lines
# too, turning them into "Mail" as well. Restricting each sed to the
# range before the first "[Desktop Action" line (GNU sed's `0,/re/`
# range form) keeps it scoped to just the main [Desktop Entry] section's
# Name=/GenericName=, matching what actually shipped correctly for
# Loupe/Clocks (which have no action blocks at all, so the unrestricted
# version happened to be harmless for them).
# Every rename lives in one script, run at install and again whenever the
# renamed app's own package is updated (an update replaces its .desktop
# file and silently drops the rename -- %%triggerin re-applies it).
%{_libexecdir}/parchaos-app-renames
update-desktop-database %{_datadir}/applications &>/dev/null || true

%triggerin -- loupe, gnome-clocks, geary, gnome-software, deja-dup, seahorse
%{_libexecdir}/parchaos-app-renames
update-desktop-database %{_datadir}/applications &>/dev/null || true

%changelog
* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-11
- Ticket #161: Seahorse (GNOME's Passwords and Keys app: the login keyring, saved
  passwords, SSH and PGP keys) is shown as "Parcha Keys" and is on the ISO.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-10
- Ticket #116: depend on gvfs-smb and gvfs-nfs so Parcha Backup can back up
  to a network share ("install a gvfs backend that can connect to smb").

* Tue Sep 29 2026 ParchaOS packaging - 1.0.0-9
- Ticket #116: depend on restic. Deja Dup uses it by default since 47 but
  Fedora's package only requires duplicity, so backups had no engine on a
  plain install.
* Tue Sep 29 2026 ParchaOS packaging - 1.0.0-8
- Ticket #116: Deja Dup (GNOME's Backups app, which uses restic) is shown
  as "Parcha Backup", with its translated names dropped like the other
  Parcha-prefixed brand names. The package depends on deja-dup so it is
  on the ISO. The About window keeps upstream's credits.
* Sun Sep 27 2026 ParchaOS packaging - 1.0.0-7
- Owner-picked display names (ticket #101): Loupe -> "Parcha Preview",
  Geary -> "Parcha Mail"; "Clock" stays as it was. The Parcha-prefixed
  names now also drop their translated Name[xx]= lines, the rule this
  package already used for "Parcha Store", so the brand shows in every
  language. GenericName= keeps GNOME's own generic wording
  ("Image Viewer" / "Mail Client") for file-type and search contexts.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-6
- Ship the license text (%license) with an accurate SPDX License tag.
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-5
- Rename Software to "Parcha Store" so users recognize the app store
  (translated Name[xx]= lines dropped: it's a brand name).
- Renames now live in one script run at install and from %%triggerin on
  loupe/gnome-clocks/geary/gnome-software: an update of those packages
  replaced their .desktop files and silently dropped the renames.
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-4
- Reworded comments and changelog to describe user-reported issues
  instead of quoting them.
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-3
- Reworded summary/description/comments to describe features instead of
  naming macOS, per the project's trademark-caution naming policy.
* Thu Sep 24 2026 ParchaOS packaging - 1.0.0-2
- Real bug found live on real hardware immediately after Release 1
  shipped: the unrestricted sed clobbered Geary's own Desktop Action
  labels ("Compose Message", "New Window" both became "Mail" too).
  Restricted each sed to the range before the first [Desktop Action
  line. See the updated %post comment for the full explanation.
* Thu Sep 24 2026 ParchaOS packaging - 1.0.0-1
- Initial package. Real user request (more app rebrands like the
  browser's) plus a real theming audit
  finding: the icon theme already covers these apps for free, only
  the display name needed fixing. See banner comment for full
  reasoning, including why Amberol was left out.
