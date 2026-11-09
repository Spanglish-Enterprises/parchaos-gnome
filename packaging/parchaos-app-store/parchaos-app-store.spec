Name:           parchaos-app-store
Version:        1.0.0
Release:        2%{?dist}
Summary:        ParchaOS App Store integrations and helpers

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-app-store-files.tar.gz
Source1:        es.po
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  gettext
BuildRequires:  systemd-rpm-macros
Requires:       bash
Requires:       flatpak
Requires:       gnome-software
# notify-send with actions, gio trash, gettext.sh.
Requires:       libnotify
Requires:       glib2
Requires:       gettext-runtime

%description
Helpers for Parcha Store (GNOME Software). After a Flatpak app is
uninstalled, from the Store, the launcher or a terminal, ParchaOS offers to
move the settings and data it left in ~/.var/app to the Trash, showing the
size first. Nothing is deleted without the user's choice.

%prep
%setup -q -c -n %{name}-%{version}
cp -p %{SOURCE90} .

%build
# Nothing to compile

%install
mkdir -p %{buildroot}
cp -a usr %{buildroot}/
chmod 0755 %{buildroot}%{_libexecdir}/parchaos-app-leftovers
# Enabled for every user by packaged links (a %%systemd_user_post preset only acts on first install).
mkdir -p %{buildroot}%{_userunitdir}/default.target.wants %{buildroot}%{_userunitdir}/timers.target.wants
ln -s ../parchaos-app-leftovers.path %{buildroot}%{_userunitdir}/default.target.wants/parchaos-app-leftovers.path
ln -s ../parchaos-app-leftovers.timer %{buildroot}%{_userunitdir}/timers.target.wants/parchaos-app-leftovers.timer
# Spanish (es_PR falls back to es). Another language: a Source line and one more msgfmt line.
install -d %{buildroot}%{_datadir}/locale/es/LC_MESSAGES
msgfmt --check -o %{buildroot}%{_datadir}/locale/es/LC_MESSAGES/parchaos-app-store.mo %{SOURCE1}

%files
%license LICENSE
%{_libexecdir}/parchaos-app-leftovers
%{_userunitdir}/parchaos-app-leftovers.service
%{_userunitdir}/parchaos-app-leftovers.path
%{_userunitdir}/parchaos-app-leftovers.timer
%{_userunitdir}/default.target.wants/parchaos-app-leftovers.path
%{_userunitdir}/timers.target.wants/parchaos-app-leftovers.timer
%{_datadir}/locale/es/LC_MESSAGES/parchaos-app-store.mo

%changelog
* Sun Nov 08 2026 ParchaOS packaging - 1.0.0-2
- Ticket #118: parchaos-app-leftovers. When a Flatpak app is uninstalled (from the Store, the
  launcher or a terminal), a notification shows the size of the data it left in ~/.var/app and
  offers Move to Trash or Keep; Keep is remembered, a dismissed banner asks again later. Started by
  a user path unit on the installed-apps folders and once after login. English and Spanish.
- Removed the uncalled uninstall helper, which deleted data with rm -rf without asking.

* Mon Sep 28 2026 ParchaOS Project <hello@parchaos.com> - 1.0.0-1
- Initial package with clean app uninstall helper (Ticket #125)
