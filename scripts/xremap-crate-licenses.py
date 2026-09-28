#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Build the license bundle for the Rust crates statically linked into the
# prebuilt xremap binary that parchaos-keyboard-remap ships.
#
#   scripts/xremap-crate-licenses.py VERSION > \
#       packaging/parchaos-keyboard-remap/xremap-crate-licenses.txt
#
# Reads xremap's Cargo.lock at tag vVERSION, downloads each crates.io
# package listed there, and prints every license, copyright and notice
# file it contains, with the crate's declared license. Cargo.lock lists
# every crate for every platform and feature, so the bundle is a superset
# of what the Linux binary links. Rerun it whenever xremap_version changes.
#
# Original code for ParchaOS, GPL-3.0-or-later.

import io
import re
import sys
import tarfile
import tomllib
import urllib.request
from concurrent.futures import ThreadPoolExecutor

NOTICE = re.compile(r'^(licen[cs]e|copying|notice|copyright|authors)([-._].*)?$', re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'parchaos-license-bundle'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def crate_notices(pkg):
    name, version = pkg['name'], pkg['version']
    data = fetch(f'https://static.crates.io/crates/{name}/{name}-{version}.crate')
    declared, files = None, []
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
        for member in tar.getmembers():
            parts = member.name.split('/')
            if not member.isfile() or len(parts) != 2:
                continue
            if parts[1] == 'Cargo.toml':
                meta = tomllib.loads(tar.extractfile(member).read().decode('utf-8', 'replace'))
                package = meta.get('package', {})
                declared = package.get('license') or (
                    f"see {package['license-file']}" if package.get('license-file') else None)
            elif NOTICE.match(parts[1]):
                text = tar.extractfile(member).read().decode('utf-8', 'replace')
                files.append((parts[1], text))
    return name, version, declared, sorted(files)


def main(version):
    lock = tomllib.loads(fetch(
        f'https://raw.githubusercontent.com/xremap/xremap/v{version}/Cargo.lock').decode())
    pkgs = [p for p in lock['package']
            if p.get('source', '').startswith('registry+https://github.com/rust-lang/crates.io-index')]
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(crate_notices, pkgs))

    out = sys.stdout
    out.write(f'Third-party Rust crates in xremap {version}\n')
    out.write('=' * 60 + '\n\n')
    out.write('The xremap binary in parchaos-keyboard-remap is statically linked\n'
              'with the crates below. Each entry gives the license the crate\n'
              'declares and the license, copyright and notice files it ships.\n'
              f'Generated from xremap v{version} Cargo.lock by\n'
              'scripts/xremap-crate-licenses.py in the ParchaOS repository.\n\n')
    missing = []
    for name, ver, declared, files in sorted(results):
        out.write('-' * 60 + '\n')
        out.write(f'{name} {ver}\nLicense: {declared or "(not declared)"}\n\n')
        if not files:
            missing.append(f'{name} {ver}')
            out.write('(The crate ships no license file; its declared license applies.)\n\n')
        for fname, text in files:
            out.write(f'--- {fname} ---\n{text.rstrip()}\n\n')
    print(f'{len(results)} crates, {len(missing)} without a license file', file=sys.stderr)
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__ or 'usage: xremap-crate-licenses.py VERSION', file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
