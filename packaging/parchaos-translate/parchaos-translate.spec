# ==============================================================================
# Translate Selection (ticket #152): select text in any app, press Ctrl+Alt+T,
# and a small popup shows it in English or Spanish, translated on this computer.
# The engine (Fedora's onnxruntime, numpy, sentencepiece) and the Opus-MT
# models are added on first use, after asking: one password prompt for the
# engine, then a checked download of about 230 MB into ~/.local/share.
# Screen Lookup also gets a Translate action (parchaos-lookup 1.0.0-3).
#
# Model licence: Opus-MT by Helsinki-NLP (University of Helsinki), Apache-2.0
# on its model cards (the OPUS-MT project also publishes its models under
# CC-BY 4.0); trained on the OPUS corpora. We download the ONNX conversions
# published as Xenova/opus-mt-en-es and Xenova/opus-mt-es-en, pinned to one
# revision with a SHA-256 for each file. Nothing of the models is shipped in
# this package. See README.md.
# ==============================================================================

Name:           parchaos-translate
Version:        1.0.0
Release:        1%{?dist}
Summary:        Translate selected text between English and Spanish on this computer

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-translate
Source1:        extension.js
Source2:        metadata.json
Source3:        org.parchaos.translate.gschema.xml
Source4:        stylesheet.css
Source5:        es.po
Source6:        parchaos-translate-install-engine
Source7:        org.parchaos.translate.policy
Source8:        README.md
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  glib2
BuildRequires:  python3
BuildRequires:  gettext

Requires:       gnome-shell >= 48
Requires:       python3
Requires:       polkit
# The engine itself (python3-onnxruntime, python3-numpy, python3-sentencepiece)
# is installed on first use, after asking, by parchaos-translate-install-engine.

%description
Select text in any app and press Ctrl+Alt+T: a small popup shows it in
Spanish if it is English, or in English if it is Spanish, with a Copy button.
The translation is made on this computer with the Opus-MT models, so nothing
is sent anywhere. The first time, it offers to add the engine and download the
models (about 230 MB).

%prep
cp -p %{SOURCE90} %{SOURCE8} .
python3 -m py_compile %{SOURCE0}

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-translate
install -Dm0755 %{SOURCE6} %{buildroot}%{_libexecdir}/parchaos-translate/parchaos-translate-install-engine
install -Dm0644 %{SOURCE7} %{buildroot}%{_datadir}/polkit-1/actions/org.parchaos.translate.policy
UUID=parchaos-translate@parchaos.org
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST/schemas"
install -m 0644 %{SOURCE1} %{SOURCE2} %{SOURCE4} "$DEST/"
install -m 0644 %{SOURCE3} "$DEST/schemas/"
glib-compile-schemas "$DEST/schemas"
install -d %{buildroot}%{_datadir}/locale/es/LC_MESSAGES
msgfmt --check -o %{buildroot}%{_datadir}/locale/es/LC_MESSAGES/parchaos-translate.mo %{SOURCE5}

%files
%license LICENSE
%doc README.md
%{_bindir}/parchaos-translate
%{_libexecdir}/parchaos-translate/
%{_datadir}/polkit-1/actions/org.parchaos.translate.policy
%{_datadir}/gnome-shell/extensions/parchaos-translate@parchaos.org/
%{_datadir}/locale/es/LC_MESSAGES/parchaos-translate.mo

%changelog
* Sat Nov 14 2026 ParchaOS packaging - 1.0.0-1
- Initial package (ticket #152): Ctrl+Alt+T translates the selection between
  English and Spanish in a glass popup, on this computer (Opus-MT through
  onnxruntime, beam search, sentence by sentence so the layout is kept);
  first-use set-up with one password prompt and a checked download; Copy and
  "translate from the other language". English and Spanish.
