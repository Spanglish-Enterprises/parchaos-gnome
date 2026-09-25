# ==============================================================================
# Hosts-file ad-blocker -- one of the "bigger, unscoped" features scoped
# in docs/gnome-phase3-findings.md. Pulsar OS's own `pulsaros-hblock` is
# blocked (lives inside the license-less Inled-Pulsar-OS/PKG monorepo,
# same as everything else in that bucket), but it's itself almost
# certainly built on the same real, independent upstream used here:
# hectorm/hblock, real MIT LICENSE.md confirmed via GitHub API. This
# profile depends on the real upstream directly rather than trying to
# adapt Pulsar's own (blocked) copy of it.
#
# Adapted directly from hectorm/hblock's own real, working RPM spec
# (resources/packaging/rpm/SPECS/hblock.spec.m4, fetched and read
# before writing this, not guessed) -- same "use the real upstream
# packaging as a reference" approach already used for xremap/PKGBUILDs
# elsewhere in this project. Their own Makefile's `install` target
# already does everything needed: installs the hblock script, man page,
# and a real systemd .service + .timer pair for periodic list refresh
# (resources/systemd/) -- no need to write our own timer unit from
# scratch. The `install` target itself has no dependency on their
# version.sh's git-describe-based version detection (that's only used
# by the `hosts`/`package-*` targets, confirmed by reading the real
# Makefile), so a plain pinned-commit tarball (this project's usual
# Source0 pattern, not a git clone) works fine here without special
# handling.
# ==============================================================================

Name:           parchaos-hblock
Version:        3.5.1
Release:        2%{?dist}
Summary:        Adblocker that creates a hosts file from multiple sources

License:        MIT
URL:            https://github.com/hectorm/hblock
%global commit  8bce7f687ff9c29739dce10bbeb59ab1e71d6ff3
%global shortcommit %(c=%{commit}; echo ${c:0:7})
Source0:        %{url}/archive/%{commit}/hblock-%{shortcommit}.tar.gz

BuildArch:      noarch
BuildRequires:  make
# Not for the %post/%preun scriptlet macros (replaced with plain shell
# below, see that comment) -- needed for the plain %%_unitdir path
# macro used in %files. Real COPR build failure caught this: without
# it, %%{_unitdir} is simply undefined text, and %files' path check
# rejects it outright ("File must begin with /").
BuildRequires:  systemd-rpm-macros

Requires:       curl
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

%description
hBlock is a POSIX-compliant shell script that fetches a list of domains
serving ads, tracking scripts, and malware from multiple public sources
and merges them into /etc/hosts, refreshed on a systemd timer. Real,
independently-maintained upstream (not Inled-original) -- Pulsar OS's
own equivalent is blocked on the same missing-LICENSE gap as most of
their original work; this depends on the real upstream directly
instead. See this spec's own banner comment for the full reasoning.

%prep
%autosetup -n hblock-%{commit}

%build

%install
%make_install prefix="%{_prefix}" bindir="%{_bindir}" mandir="%{_mandir}" unitdir="%{_unitdir}"
# Real COPR build failure caught this: their Makefile's own install
# target only installs the systemd unit files if `command -v systemctl`
# succeeds, which it doesn't in COPR's minimal mock chroot (no systemd
# package there at all, by design -- mock chroots build packages, they
# don't run services). %make_install above silently skipped both unit
# files as a result. Installing them directly instead of depending on
# that runtime check.
mkdir -p %{buildroot}%{_unitdir}
install -m 0644 resources/systemd/hblock.service resources/systemd/hblock.timer %{buildroot}%{_unitdir}/

%post
# Real bug caught before shipping, twice over: (1) RPM macro-expands
# the ENTIRE scriptlet section text, including shell comments -- an
# earlier version of this comment that just mentioned the macro names
# by their real spelling triggered the exact same broken expansion
# described below, since RPM doesn't know a "#" starts a shell comment
# until after macro expansion already ran. Written with a literal
# double-percent below to actually show up as a comment.  (2) This
# build host's systemd-rpm-macros (259.9) changed the
# systemd-post/preun macros' calling convention -- they now require a
# scriptlet-arity declaration this project's other specs don't use
# anywhere else, and hectorm's own upstream spec template predates the
# change: `rpm --eval` reproduced "The %%systemd_post macro requires
# some arguments" even with a real unit name passed. Rather than
# couple this package to one specific systemd-rpm-macros version,
# write the plain shell these macros actually expand to on stable
# Fedora releases -- also avoids %{name} resolving to this RPM's own
# name (parchaos-hblock) instead of the literal unit name their real
# Makefile installs (hblock.timer/hblock.service, unaffected by
# whatever this spec is called), a second real bug the macro form
# would have hit anyway.
if [ $1 -eq 1 ]; then
    # Initial installation. Real bug found live on real hardware:
    # `systemctl preset` (what the plain-shell equivalent of
    # %%systemd_post is normally supposed to use) only enables a unit
    # if a real .preset policy file says to -- this project doesn't
    # ship one, so Fedora's own default preset policy left the timer
    # disabled, meaning the ad-blocker refresh never actually ran.
    # Enabling directly instead, since there's no reason a user would
    # want this installed-but-inert.
    systemctl enable --now hblock.timer >/dev/null 2>&1 || :
fi

%preun
if [ $1 -eq 0 ]; then
    # Package removal, not upgrade
    systemctl --no-reload disable --now hblock.timer >/dev/null 2>&1 || :
fi

%postun
systemctl daemon-reload >/dev/null 2>&1 || :

%files
%{_bindir}/hblock
%{_unitdir}/hblock.timer
%{_unitdir}/hblock.service
%{_mandir}/man1/hblock.1*
%license LICENSE.md
%doc README.md

%changelog
* Thu Sep 24 2026 ParchaOS packaging - 3.5.1-2
- Real bug found live: `systemctl preset` left the timer disabled
  since this project ships no .preset policy file. Switched to
  `systemctl enable --now` so the ad-blocker is actually active after
  install, not just present.
* Thu Sep 24 2026 ParchaOS packaging - 3.5.1-1
- Initial package, one of the three "bigger feature" gaps scoped in
  docs/gnome-phase3-findings.md that don't depend on Inled's licensing
  answer. Adapted from the real upstream's own working RPM spec.
