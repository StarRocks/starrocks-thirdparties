"""Reject nonportable, leaking or nonrelocatable ELF packages before release."""
import json
from pathlib import Path
import re
import subprocess
import sys


def check(root):
    library = root / 'lib/libstarrocks_lance.so'
    manifest = json.loads((root / 'share/lance/manifest.json').read_text())
    dynamic = subprocess.check_output(['readelf', '-d', str(library)], text=True)
    needed = re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic)
    allowed = {'libc.so.6', 'libm.so.6', 'libpthread.so.0', 'libdl.so.2',
               'librt.so.1', 'libgcc_s.so.1', 'ld-linux-x86-64.so.2', 'ld-linux-aarch64.so.1'}
    if set(needed) - allowed:
        raise RuntimeError('Unexpected shared dependencies: ' + str(needed))
    if re.search(r'\((?:RPATH|RUNPATH)\)', dynamic):
        raise RuntimeError('Release library must not contain a build RPATH/RUNPATH')
    versions = subprocess.check_output(['readelf', '--version-info', str(library)], text=True)
    required = [tuple(map(int, v.split('.'))) for v in re.findall(r'GLIBC_(\d+\.\d+)', versions)]
    if not required or max(required) > (2, 34):
        raise RuntimeError('Portable package exceeds glibc 2.34 floor')
    symbols = subprocess.check_output(['nm', '-D', '--defined-only', str(library)], text=True)
    public = {line.split()[-1] for line in symbols.splitlines() if line.strip()}
    expected = {'sr_lance_reader_open', 'sr_lance_reader_next', 'sr_lance_reader_close',
                'sr_lance_reader_version', 'sr_lance_free_error'}
    if public != expected:
        raise RuntimeError('Unexpected ABI exports: ' + str(public ^ expected))
    manifest.update(needed=needed, glibc_floor='2.34', build_os='rocky9')
    (root / 'share/lance/manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    check(Path(sys.argv[1]))
