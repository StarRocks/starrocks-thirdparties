import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('packages', Path(__file__).resolve().parents[1] / 'scripts/packages.py')
packages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packages)


class ReleaseDiscoveryTest(unittest.TestCase):
    def package(self, root, name):
        directory = root / name
        directory.mkdir()
        for f in ['README.md', 'build.sh']:
            (directory / f).touch()

    def test_longest_matching_name_and_version_are_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ['example', 'example-ffi']:
                self.package(root, name)
            metadata = json.dumps({'version': '1.2.3', 'platforms': ['rocky9-x86_64', 'rocky9-aarch64']})
            with patch.object(packages.subprocess, 'check_output', return_value=metadata):
                matrix = packages.discover(root, 'example-ffi-1.2.3')['include']
                self.assertEqual({'example-ffi'}, {m['name'] for m in matrix})
                self.assertEqual({'ubuntu-24.04', 'ubuntu-24.04-arm'}, {m['runner'] for m in matrix})
                for tag in ['example-ffi-1.2.4', 'unknown-1.2.3']:
                    with self.assertRaises(ValueError):
                        packages.discover(root, tag)

    def test_missing_entrypoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'example').mkdir()
            with self.assertRaisesRegex(ValueError, 'Missing'):
                packages.discover(Path(tmp))

    def test_bad_platform_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.package(root, 'example')
            with patch.object(packages.subprocess, 'check_output', return_value=json.dumps(
                    {'version': '1.0', 'platforms': ['ubuntu-x86_64']})):
                with self.assertRaisesRegex(ValueError, 'Invalid platform'):
                    packages.discover(root)
