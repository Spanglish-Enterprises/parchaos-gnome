ParchaOS VERSION: a polished, familiar GNOME desktop on Fedora FEDORA_VERSION.

**Install:** write the ISO to a USB stick (8 GB or larger) with Fedora Media Writer, balenaEtcher or `dd`, boot from it, and click **Install ParchaOS** in the dock. Secure Boot can stay on.

**Which file?** `…-x86_64.iso` is for almost every PC and laptop (Intel or AMD) and Intel Macs; `…-aarch64.iso` is for UEFI ARM64 computers and virtual machines (for example on Apple Silicon Macs). If you're not sure, choose x86_64.

**You'll need:** a 64-bit PC (UEFI or legacy BIOS) or a UEFI ARM64 computer or virtual machine, 4 GB of RAM (8 GB recommended) and 25 GB of disk space.

**Verify the download:** `sha256sum -c SHA256SUMS --ignore-missing` in the folder with the downloaded files.

**What's in the ISO:** each ISO's `….iso.packages.tsv` lists every package with its license.

**Source code:** the `…-sources-*.tar` assets contain the source RPM of every package in this release's ISOs (`…-sources.sha256` lists them). ParchaOS's own code is in this repository at tag `TAG`. For at least three years after this release, Spanglish Enterprises LLC will provide the complete corresponding source on request, at no more than the cost of distribution: use the form at https://parchaos.org/support, choose **Question** and title it "Source code request". Details: `docs/SOURCES.md`.

**Legal:** ParchaOS is provided as is, without warranty; see `docs/LEGAL.md` (also installed at `/usr/share/doc/parchaos/LEGAL.md`). It contains cryptographic software and may be subject to U.S. export regulations. ParchaOS isn't affiliated with or endorsed by the Fedora Project, Red Hat, the GNOME Foundation or Apple. If you believe anything in ParchaOS infringes your copyright or trademark, tell us through https://parchaos.org/support and we'll review it promptly and in good faith, and change or remove the material where appropriate.

This is an early release. Back up your data before installing. Known issues: SECURITY.md.
