# ==============================================================================
# Photo search (ticket #123): find pictures by what is in them, on this
# computer. A small image model (CLIP ViT-B/32 by OpenAI, MIT licence, in ONNX
# form) run by ONNX Runtime turns pictures and search phrases into numbers;
# close numbers are matches. The model (about 150 MB) is downloaded once, after
# the user turns the feature on, with its size and SHA-256 checked. Nothing
# leaves the computer. Original ParchaOS code around independent projects.
# ==============================================================================

Name:           parchaos-image-search
Version:        1.0.0
Release:        1%{?dist}
Summary:        Find your pictures by what is in them

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        clipsearch.py
Source1:        parchaos-image-search
Source2:        parchaos-image-search-provider
Source3:        parchaos-image-search-install-engine
Source4:        org.parchaos.imagesearch.policy
Source5:        org.parchaos.ImageSearch.search-provider.ini
Source6:        org.parchaos.ImageSearch.desktop
Source7:        org.parchaos.ImageSearch.SearchProvider.service
Source8:        parchaos-image-search-index.service
Source9:        parchaos-image-search-index.timer
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  desktop-file-utils
BuildRequires:  python3
BuildRequires:  systemd-rpm-macros

Requires:       python3
Requires:       python3-gobject
Requires:       polkit
Requires:       dnf5

%description
Type a few words, like "sunset over water", and see the pictures that match
in the search of the Overview or with parchaos-image-search. Off until it is
turned on in ParchaOS Settings; then it fetches a small image model once and
keeps an index of your Pictures folder up to date. It all stays on this
computer.

%prep
cp -p %{SOURCE90} .
python3 -m py_compile %{SOURCE0} %{SOURCE1} %{SOURCE2}

%build

%install
install -Dm0644 %{SOURCE0} %{buildroot}%{_libexecdir}/parchaos-image-search/clipsearch.py
install -Dm0755 %{SOURCE2} %{buildroot}%{_libexecdir}/parchaos-image-search/parchaos-image-search-provider
install -Dm0755 %{SOURCE3} %{buildroot}%{_libexecdir}/parchaos-image-search/parchaos-image-search-install-engine
install -Dm0755 %{SOURCE1} %{buildroot}%{_bindir}/parchaos-image-search
install -Dm0644 %{SOURCE4} %{buildroot}%{_datadir}/polkit-1/actions/org.parchaos.imagesearch.policy
install -Dm0644 %{SOURCE5} %{buildroot}%{_datadir}/gnome-shell/search-providers/org.parchaos.ImageSearch.search-provider.ini
desktop-file-validate %{SOURCE6}
install -Dm0644 %{SOURCE6} %{buildroot}%{_datadir}/applications/org.parchaos.ImageSearch.desktop
install -Dm0644 %{SOURCE7} %{buildroot}%{_datadir}/dbus-1/services/org.parchaos.ImageSearch.SearchProvider.service
install -Dm0644 %{SOURCE8} %{buildroot}%{_userunitdir}/parchaos-image-search-index.service
install -Dm0644 %{SOURCE9} %{buildroot}%{_userunitdir}/parchaos-image-search-index.timer

%files
%license LICENSE
%{_bindir}/parchaos-image-search
%{_libexecdir}/parchaos-image-search/
%{_datadir}/polkit-1/actions/org.parchaos.imagesearch.policy
%{_datadir}/gnome-shell/search-providers/org.parchaos.ImageSearch.search-provider.ini
%{_datadir}/applications/org.parchaos.ImageSearch.desktop
%{_datadir}/dbus-1/services/org.parchaos.ImageSearch.SearchProvider.service
%{_userunitdir}/parchaos-image-search-index.service
%{_userunitdir}/parchaos-image-search-index.timer

%changelog
* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-1
- Initial package (ticket #123). Checked with the real model: 23 pictures
  indexed in under a second, and phrases like "a sea and a stone tower" and
  "passion fruit" ranked the right pictures first. The search-provider service
  answers over D-Bus. Off until turned on in ParchaOS Settings.
