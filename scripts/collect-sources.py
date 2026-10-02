#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""collect-sources.py <rootfs> <outdir> [--prefix NAME] [--no-download]

Collects the complete corresponding source for an ISO: the exact source
RPM (SRPM) of every installed package, as recorded in the rootfs's RPM
database (%{SOURCERPM}).

- Fedora builds come from Koji (kojipkgs.fedoraproject.org), which keeps
  every build, so older releases stay available after mirrors move on.
- ParchaOS's own builds come from the matching COPR build's results.

Writes <outdir>/<prefix>-sources.sha256 (one line per SRPM) and packs the
SRPMs into <prefix>-sources-NN.tar archives under 1.9 GiB each (GitHub's
release asset limit is 2 GiB). Fails if any SRPM can't be found.

--no-download only lists the SRPMs and where each would come from.
"""
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import urllib.request

COPR_OWNER = "alexgalicea"
COPR_PROJECT = "parchaos-gnome"
COPR_CHROOT = "fedora-44-x86_64"   # set from the rootfs's own architecture in main()
COPR_API = "https://copr.fedorainfracloud.org/api_3"
KOJI = "https://kojipkgs.fedoraproject.org/packages"
PART_LIMIT = int(1.9 * 1024 ** 3)


def installed_sources(rootfs):
    out = subprocess.run(
        ["rpm", "--root", rootfs, "-qa", "--qf", "%{SOURCERPM}\t%{VENDOR}\n"],
        check=True, capture_output=True, text=True).stdout
    srpms = {}
    for line in out.splitlines():
        srpm, vendor = line.split("\t")
        if srpm in ("(none)", ""):
            continue  # gpg-pubkey pseudo-packages
        srpms[srpm] = vendor
    return srpms


def split_nvr(srpm):
    base = srpm[:-len(".src.rpm")]
    name, version, release = base.rsplit("-", 2)
    return name, version, release


def urlopen(url, tries=3):
    """urlopen with a timeout, retried: a stalled connection must not hang the run."""
    for attempt in range(tries):
        try:
            return urllib.request.urlopen(url, timeout=120)
        except OSError:
            if attempt == tries - 1:
                raise


def copr_url(name, version, release):
    query = (f"{COPR_API}/build/list?ownername={COPR_OWNER}&projectname={COPR_PROJECT}"
             f"&packagename={name}&limit=200")
    with urlopen(query) as r:
        builds = json.load(r)["items"]
    for b in builds:
        pkg = b.get("source_package") or {}
        if COPR_CHROOT not in (b.get("chroots") or [COPR_CHROOT]):
            continue
        if b["state"] == "succeeded" and pkg.get("version") == f"{version}-{release}".rsplit(".fc", 1)[0] \
                or pkg.get("version") == f"{version}-{release}":
            return (f"https://download.copr.fedorainfracloud.org/results/{COPR_OWNER}/{COPR_PROJECT}/"
                    f"{COPR_CHROOT}/{b['id']:08d}-{name}/{name}-{version}-{release}.src.rpm")
    return None


def source_url(srpm, vendor):
    name, version, release = split_nvr(srpm)
    if vendor.startswith("Fedora Copr"):
        return copr_url(name, version, release)
    return f"{KOJI}/{name}/{version}/{release}/src/{srpm}"


def download(url, dest):
    tmp = dest + ".part"
    with urlopen(url) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    os.replace(tmp, dest)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def main():
    argv = sys.argv[1:]
    prefix = "parchaos"
    if "--prefix" in argv:
        i = argv.index("--prefix")
        if i + 1 >= len(argv):
            sys.exit(__doc__)
        prefix = argv[i + 1]
        del argv[i:i + 2]
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    rootfs, outdir = args
    listing_only = "--no-download" in sys.argv

    # The image's architecture picks the COPR chroot (x86_64 or aarch64, ticket #167):
    # a build may exist in one chroot only.
    global COPR_CHROOT
    arch = subprocess.run(["rpm", "--root", rootfs, "-q", "--qf", "%{ARCH}\n", "kernel-core"],
                          capture_output=True, text=True).stdout.split()
    if arch:
        COPR_CHROOT = f"fedora-44-{arch[-1]}"
    print(f"COPR chroot: {COPR_CHROOT}")
    srpms = installed_sources(rootfs)
    print(f"{len(srpms)} source packages")
    srpm_dir = os.path.join(outdir, "srpms")
    os.makedirs(srpm_dir, exist_ok=True)

    missing = []
    for srpm, vendor in sorted(srpms.items()):
        url = source_url(srpm, vendor)
        if url is None:
            missing.append(f"{srpm} (no COPR build found)")
            continue
        if listing_only:
            print(f"{srpm}\t{url}")
            continue
        dest = os.path.join(srpm_dir, srpm)
        if os.path.exists(dest):
            continue
        try:
            download(url, dest)
        except Exception as e:  # noqa: BLE001 -- report every failure
            missing.append(f"{srpm} ({url}: {e})")
    if missing:
        sys.exit("collect-sources: missing:\n  " + "\n  ".join(missing))
    if listing_only:
        return

    files = sorted(os.listdir(srpm_dir))
    manifest = os.path.join(outdir, f"{prefix}-sources.sha256")
    with open(manifest, "w") as m:
        for f in files:
            m.write(f"{sha256(os.path.join(srpm_dir, f))}  {f}\n")

    part, size, tar = 0, 0, None
    for f in files:
        path = os.path.join(srpm_dir, f)
        fsize = os.path.getsize(path)
        if fsize > PART_LIMIT:
            sys.exit(f"collect-sources: {f} is larger than one release asset")
        if tar is None or size + fsize > PART_LIMIT:
            if tar:
                tar.close()
            part += 1
            size = 0
            tar = tarfile.open(os.path.join(outdir, f"{prefix}-sources-{part:02d}.tar"), "w")
        tar.add(path, arcname=f)
        size += fsize
    if tar:
        tar.close()
    print(f"{len(files)} SRPMs in {part} archive(s); manifest: {manifest}")


if __name__ == "__main__":
    main()
