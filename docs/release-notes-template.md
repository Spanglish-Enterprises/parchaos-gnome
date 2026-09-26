ParchaOS VERSION: a polished, familiar GNOME desktop on Fedora FEDORA_VERSION.

**Install:** write the ISO to a USB stick (8 GB or larger) with Fedora Media Writer, balenaEtcher or `dd`, boot from it, and click **Install ParchaOS** in the dock. Secure Boot can stay on.

**You'll need:** a 64-bit PC (UEFI or legacy BIOS), 4 GB of RAM (8 GB recommended) and 25 GB of disk space.

**Verify the download:** `sha256sum -c SHA256SUMS` in the folder with the downloaded files.

**What's in the ISO:** `ISO_NAME.packages.tsv` lists every package with its license.

**Source code:** the `…-sources-*.tar` assets contain the source RPM of every package in this ISO (`…-sources.sha256` lists them). ParchaOS's own code is in this repository at tag `TAG`. For at least three years after this release, Spanglish Enterprises LLC will provide the complete corresponding source on request, at no more than the cost of distribution: use the form at https://parchaos.org/support, choose **Question** and title it "Source code request". Details: `docs/SOURCES.md`.

**Legal:** ParchaOS is provided as is, without warranty; see `docs/LEGAL.md` (also installed at `/usr/share/doc/parchaos/LEGAL.md`). It contains cryptographic software and may be subject to U.S. export regulations. ParchaOS isn't affiliated with or endorsed by the Fedora Project, Red Hat, the GNOME Foundation or Apple.

This is an early release. Back up your data before installing. Known issues: SECURITY.md.
