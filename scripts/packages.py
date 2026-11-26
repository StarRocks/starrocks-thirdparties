#!/usr/bin/env python3
"""Discover isolated build entrypoints and validate per-package release tags."""
import json
from pathlib import Path
import re
import subprocess
import sys

RESERVED = {'scripts', 'checks', '.github', '.git'}
ROOT = Path(__file__).resolve().parents[1]
RUNNERS = {'x86_64': 'ubuntu-24.04', 'aarch64': 'ubuntu-24.04-arm'}


def discover(root=ROOT, tag=None):
    packages = {}
    for path in sorted(root.iterdir()):
        if not path.is_dir() or path.name in RESERVED or path.name.startswith('.'):
            continue
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', path.name):
            raise ValueError('Invalid thirdparty directory: ' + path.name)
        for required in ['README.md', 'build.sh']:
            if not (path / required).is_file():
                raise ValueError('Missing ' + str(path / required))
        metadata = json.loads(subprocess.check_output(['bash', str(path / 'build.sh'), '--metadata'], text=True))
        if not re.fullmatch(r'[0-9][A-Za-z0-9.+-]*', metadata['version']):
            raise ValueError('Invalid version for ' + path.name)
        packages[path.name] = metadata
    if not packages:
        raise ValueError('No thirdparties found')
    if tag:
        candidates = [name for name in packages if tag.startswith(name + '-')]
        if not candidates:
            raise ValueError('Unknown release tag: ' + tag)
        name = max(candidates, key=len)
        if tag != name + '-' + packages[name]['version']:
            raise ValueError('Release tag does not match declared version: ' + tag)
        packages = {name: packages[name]}
    matrix = []
    for name, metadata in packages.items():
        if not metadata['platforms'] or len(set(metadata['platforms'])) != len(metadata['platforms']):
            raise ValueError('Empty or repeated platform list: ' + name)
        for platform in metadata['platforms']:
            match = re.fullmatch(r'(centos7|rocky9|ubuntu24)-(x86_64|aarch64)', platform)
            if not match:
                raise ValueError('Invalid platform: ' + platform)
            matrix.append(dict(name=name, version=metadata['version'], platform=platform,
                               runner=RUNNERS[match[2]]))
    return {'include': matrix}


if __name__ == '__main__':
    print(json.dumps(discover(tag=sys.argv[1] if len(sys.argv) > 1 else None)))
