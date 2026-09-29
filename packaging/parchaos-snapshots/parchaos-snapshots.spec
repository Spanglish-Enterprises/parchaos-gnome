# ==============================================================================
# Snapshots and their top-bar menu (ticket #116, layer 1).
#
# Snapper takes hourly Btrfs snapshots of the system and home folders and a
# pair around every package update. Wisp (wisp@epogonii.github.io, by
# epogonii, GPL-2.0-or-later, confirmed from its LICENSE and file headers)
# lists them in the top bar: browse, compare, restore single files. Wisp is
# packaged unmodified at a pinned commit. This package adds only the snapper
# configuration (first boot, once) and the dnf hook.
#
# Snapshots live on the same disk as the data, so they are history for undoing
# mistakes, not a backup; the backup app (layer 2) covers disk loss.
# ==============================================================================

Name:           parchaos-snapshots
Version:        1
Release:        1%{?dist}
Summary:        Snapshots of your system and files, in the top bar

License:        GPL-2.0-or-later
URL:            https://github.com/epogonii/wisp
%global commit  9543d86d9ba7595c49e8804fed8aa467e891e832
%global shortcommit %(c=%{commit}; echo ${c:0:7})
Source0:        %{url}/archive/%{commit}/wisp-%{shortcommit}.tar.gz
Source1:        parchaos-snapper-setup
Source2:        parchaos-snapper-setup.service
Source3:        parchaos-snapper-dnf
Source4:        parchaos-snapper.actions

BuildArch:      noarch
BuildRequires:  glib2
BuildRequires:  systemd-rpm-macros

Requires:       gnome-shell >= 46
Requires:       snapper
Requires:       btrfs-progs
Requires:       util-linux
Requires:       polkit
# Runs the before/after snapshots around package updates.
Requires:       libdnf5-plugin-actions
Requires(post): systemd

%description
Keeps a short history of your system and your files. Every hour, and
before and after each software update, ParchaOS takes a snapshot of the
system and home folders. Open the snapshot menu in the top bar to see
what changed, look inside an older state and put single files back.
Snapshots live on the same disk as your files, so they help you undo
mistakes but are not a backup. Wraps Wisp, a GNOME Shell extension for
snapper (GPL-2.0-or-later).

%prep
%autosetup -n wisp-%{commit}

%build
glib-compile-schemas schemas

%install
UUID=wisp@epogonii.github.io
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST/lib" "$DEST/icons" "$DEST/schemas"
install -m 0644 extension.js prefs.js metadata.json stylesheet.css stylesheet-dark.css stylesheet-light.css "$DEST/"
install -m 0644 lib/*.js "$DEST/lib/"
cp -a icons/. "$DEST/icons/"
install -m 0644 schemas/*.gschema.xml schemas/gschemas.compiled "$DEST/schemas/"

install -Dm0755 %{SOURCE1} %{buildroot}%{_libexecdir}/parchaos-snapper-setup
install -Dm0755 %{SOURCE3} %{buildroot}%{_libexecdir}/parchaos-snapper-dnf
install -Dm0644 %{SOURCE2} %{buildroot}%{_unitdir}/parchaos-snapper-setup.service
# Enabled by a packaged link: %%systemd_post does not enable a unit that is
# new on an upgrade.
install -d %{buildroot}%{_unitdir}/multi-user.target.wants
ln -s ../parchaos-snapper-setup.service %{buildroot}%{_unitdir}/multi-user.target.wants/parchaos-snapper-setup.service
install -Dm0644 %{SOURCE4} %{buildroot}%{_sysconfdir}/dnf/libdnf5-plugins/actions.d/parchaos-snapper.actions

%post
# Set snapshots up now, so an existing install has them without a reboot.
systemctl start parchaos-snapper-setup.service >/dev/null 2>&1 || :

%files
%license LICENSE
%doc README.md
%{_datadir}/gnome-shell/extensions/wisp@epogonii.github.io/
%{_libexecdir}/parchaos-snapper-setup
%{_libexecdir}/parchaos-snapper-dnf
%{_unitdir}/parchaos-snapper-setup.service
%{_unitdir}/multi-user.target.wants/parchaos-snapper-setup.service
%config(noreplace) %{_sysconfdir}/dnf/libdnf5-plugins/actions.d/parchaos-snapper.actions

%changelog
* Tue Sep 29 2026 ParchaOS packaging - 1-1
- Initial package (ticket #116, layer 1): Wisp at commit 9543d86 (1.0.13),
  first-boot snapper configs for / and /home on Btrfs (wheel can read them),
  and a dnf hook taking a snapshot before and after each transaction.
