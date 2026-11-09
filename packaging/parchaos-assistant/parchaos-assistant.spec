Name:           parchaos-assistant
Version:        1.0.0
Release:        1%{?dist}
Summary:        Parcha Assistant: a chat window backed by a local model or Claude
License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-assistant
Source1:        org.parchaos.Assistant.desktop
Source2:        org.parchaos.Assistant.metainfo.xml
Source3:        05-parchaos-assistant
Source4:        es.po
Source90:       LICENSE
BuildArch:      noarch

BuildRequires:  desktop-file-utils
BuildRequires:  gettext
BuildRequires:  libappstream-glib
BuildRequires:  python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
# The API key lives in GNOME Keyring.
Requires:       libsecret
# Local backend: the client library; the ollama service and models are the user's choice.
Requires:       python3-ollama
# Claude backend: the official SDK is not in Fedora, so it is installed for the user with pip
# the first time Claude is chosen.
Requires:       python3-pip
Requires(post): dconf
Requires(postun): dconf

%description
Parcha Assistant is a small chat window opened with Ctrl+Alt+Space. Answers
come from a model running on this computer through Ollama, or from Claude by
Anthropic with the user's own API key, whichever the user picks; nothing is
sent anywhere before that choice. The key is stored in GNOME Keyring. English
and Spanish. Original ParchaOS work (docs/assistant-spec.md).

%prep
cp -p %{SOURCE90} .

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-assistant
install -Dm0644 %{SOURCE1} %{buildroot}%{_datadir}/applications/org.parchaos.Assistant.desktop
install -Dm0644 %{SOURCE2} %{buildroot}%{_metainfodir}/org.parchaos.Assistant.metainfo.xml
install -Dm0644 %{SOURCE3} %{buildroot}%{_sysconfdir}/dconf/db/local.d/05-parchaos-assistant
# Spanish (es_PR falls back to es). Another language: a Source line and one more msgfmt line.
install -d %{buildroot}%{_datadir}/locale/es/LC_MESSAGES
msgfmt --check -o %{buildroot}%{_datadir}/locale/es/LC_MESSAGES/parchaos-assistant.mo %{SOURCE4}

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/org.parchaos.Assistant.desktop
appstream-util validate-relax --nonet %{buildroot}%{_metainfodir}/org.parchaos.Assistant.metainfo.xml
python3 -m py_compile %{SOURCE0}

%post
dconf update >/dev/null 2>&1 || :

%postun
dconf update >/dev/null 2>&1 || :

%files
%license LICENSE
%{_bindir}/parchaos-assistant
%{_datadir}/applications/org.parchaos.Assistant.desktop
%{_metainfodir}/org.parchaos.Assistant.metainfo.xml
%config(noreplace) %{_sysconfdir}/dconf/db/local.d/05-parchaos-assistant
%{_datadir}/locale/es/LC_MESSAGES/parchaos-assistant.mo

%changelog
* Sun Nov 08 2026 ParchaOS packaging - 1.0.0-1
- Ticket #122: first version. Chat window (Ctrl+Alt+Space) with two backends the user picks: a local model through Ollama, or Claude (claude-opus-5-5, low effort, streamed, server-side refusal fallback) with the user's own key in GNOME Keyring; the Anthropic SDK is pip-installed per user on first use. Nothing is sent before a backend is chosen. Fake-server tests for both backends. English and Spanish.
