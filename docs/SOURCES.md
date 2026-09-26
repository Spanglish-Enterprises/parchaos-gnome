# ParchaOS source code

ParchaOS is published by Spanglish Enterprises LLC. Many of its
components are licensed under the GNU GPL and similar licenses, which
give you the right to the complete corresponding source code. This file
is installed on every ParchaOS system at
`/usr/share/doc/parchaos/SOURCES.md`.

## Where the source is

- **The complete source of every package in a release** is published as
  assets of that release on GitHub, next to the ISO:
  https://github.com/Spanglish-Enterprises/parchaos-gnome/releases
  The `…-sources-*.tar` archives contain one source RPM (SRPM) per
  package, exactly as installed in that ISO, and `…-sources.sha256`
  lists them with their checksums. Unpack an SRPM with
  `rpm2cpio <file>.src.rpm | cpio -idm`.
- **ParchaOS's own packages** are developed in the repository above
  (`packaging/`), and their source RPMs are also built and published on
  Fedora COPR: https://copr.fedorainfracloud.org/coprs/alexgalicea/parchaos-gnome/
- **Fedora's packages** are unmodified Fedora builds. Their sources are
  also at https://src.fedoraproject.org/ and on Fedora's mirrors
  (`dnf download --source <package>`).
- **How the ISO is built:** check out the repository at the release's
  tag and run `sudo ./engine/build-iso.sh --profile parchaos`. The list
  of packages in each ISO is published with it (`….iso.packages.tsv`).

## Written offer

For at least three years after each ParchaOS release, and for as long
as we distribute that release, Spanglish Enterprises LLC will give anyone
who asks a complete machine-readable copy of the corresponding source
code for the software in it, for no more than our cost of physically
performing the distribution (downloads are free).

To ask, use the form at https://parchaos.org/support: choose
**Question**, title it "Source code request", and name the release (for
example 2026.09.26) and the package(s) you need. Leave an email address
so we can reply.
