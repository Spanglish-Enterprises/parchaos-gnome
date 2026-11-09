Name:           parchaos-android
Version:        1.0.0
Release:        1%{?dist}
Summary:        Android Apps: set up Waydroid and manage Android apps
License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-android
Source1:        parchaos-android-setup
Source2:        org.parchaos.android.policy
Source3:        org.parchaos.Android.desktop
Source4:        org.parchaos.Android.metainfo.xml
Source5:        es.po
Source90:       LICENSE
BuildArch:      noarch

BuildRequires:  desktop-file-utils
BuildRequires:  gettext
BuildRequires:  libappstream-glib
BuildRequires:  python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       polkit
# Waydroid itself is not required: it and the Android image (about 800 MB) are only fetched when
# the user chooses Set Up, through parchaos-android-setup.

%description
Android Apps runs Android apps on ParchaOS through Waydroid. Android support is
opt-in: Set Up installs Waydroid from Fedora's repositories and downloads the
Android system image from the Waydroid project (ParchaOS does not redistribute
it). After that the window installs APK files, lists the Android apps with Open
and Remove, and starts or stops Android. English and Spanish.

%prep
cp -p %{SOURCE90} .

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-android
install -Dm0755 %{SOURCE1} %{buildroot}%{_libexecdir}/parchaos-android-setup
install -Dm0644 %{SOURCE2} %{buildroot}%{_datadir}/polkit-1/actions/org.parchaos.android.policy
install -Dm0644 %{SOURCE3} %{buildroot}%{_datadir}/applications/org.parchaos.Android.desktop
install -Dm0644 %{SOURCE4} %{buildroot}%{_metainfodir}/org.parchaos.Android.metainfo.xml
# Spanish (es_PR falls back to es). Another language: a Source line and one more msgfmt line.
install -d %{buildroot}%{_datadir}/locale/es/LC_MESSAGES
msgfmt --check -o %{buildroot}%{_datadir}/locale/es/LC_MESSAGES/parchaos-android.mo %{SOURCE5}

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/org.parchaos.Android.desktop
appstream-util validate-relax --nonet %{buildroot}%{_metainfodir}/org.parchaos.Android.metainfo.xml
python3 -m py_compile %{SOURCE0}

%files
%license LICENSE
%{_bindir}/parchaos-android
%{_libexecdir}/parchaos-android-setup
%{_datadir}/polkit-1/actions/org.parchaos.android.policy
%{_datadir}/applications/org.parchaos.Android.desktop
%{_metainfodir}/org.parchaos.Android.metainfo.xml
%{_datadir}/locale/es/LC_MESSAGES/parchaos-android.mo

%changelog
* Sun Nov 08 2026 ParchaOS packaging - 1.0.0-1
- Ticket #117: first version. Opt-in Android app support through Waydroid (Fedora's package; the Android image comes from the Waydroid project on Set Up), an Android Apps window to install APK files, open and remove apps, and start or stop Android. Listed in Parcha Store. English and Spanish.
