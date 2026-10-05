"""Portable-release checks use tiny fake binaries; no executable is launched."""

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('portable_under_test', PROJECT / 'scripts/build_portable.py')
portable = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(portable)


class PortableReleaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name).resolve()
        self.host = self.base / 'clean' / 'KaTrain'
        self.host.mkdir(parents=True)
        self.archive = self.base / 'KaTrain.zip'
        pe = bytearray(70)
        pe[:2] = b'MZ'
        struct.pack_into('<I', pe, 60, 64)
        pe[64:70] = b'PE\0\0\x64\x86'
        fixture = PROJECT / 'tests/fixtures/katrain-1.20.0-gui.kv'
        configuration = {'general': {'version': '1.20.0', 'lang': 'en'},
                         'engine': {}, 'contribute': {'username': '', 'password': ''}}
        files = {'KaTrain.exe': bytes(pe), portable.ENGINE: bytes(pe),
                 portable.MODEL: b'\x1f\x8btest model',
                 '_internal/katrain/gui.kv': fixture.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'),
                 '_internal/katrain/config.json': json.dumps(configuration).encode(),
                 '_internal/katrain/KataGo/analysis_config.cfg': b'# original config\n',
                 '_internal/LICENSE.dependency.txt': b'Upstream dependency notice'}
        for name, data in files.items():
            path = self.host / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.licenses = self.base / 'licenses'
        self.licenses.mkdir()
        for name in ('KaTrain-LICENSE.txt', 'KataGo-LICENSE.txt', 'KataGo-Network-LICENSE.txt'):
            (self.licenses / name).write_text(f'Fixture notice: {name}', encoding='utf-8')
        self.refresh_archive()

    def refresh_archive(self):
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for path in sorted(self.host.rglob('*')):
                if path.is_file():
                    archive.write(path, 'KaTrain/' + path.relative_to(self.host).as_posix())
        self.source_hash = portable.sha256(self.archive)

    def build(self, output='dist', **kwargs):
        return portable.build_portable(self.host, self.archive, '0.2.0-beta.1', self.base / output,
                                       licenses_dir=self.licenses, source_sha256=self.source_hash,
                                       commit='0123456789abcdef', **kwargs)

    def test_release_contains_runnable_host_samples_and_verified_provenance(self):
        original = {path.relative_to(self.host): path.read_bytes()
                    for path in self.host.rglob('*') if path.is_file()}
        result = self.build()
        root = 'KataGo-Explainer-v0.2.0-beta.1-win64/'
        with zipfile.ZipFile(result['archive']) as archive:
            names = archive.namelist()
            self.assertTrue(all(name.startswith(root) for name in names))
            self.assertIn(root + 'KaTrain/KaTrain.exe', names)
            self.assertIn(root + 'KaTrain/' + portable.MODEL, names)
            self.assertIn(root + 'KaTrain/_internal/katrain_explainer/service.py', names)
            self.assertIn(root + 'examples/mi-flying-dagger-demo.sgf', names)
            self.assertIn(root + 'licenses/KaTrain-LICENSE.txt', names)
            self.assertIn(root + 'KaTrain/_internal/LICENSE.dependency.txt', names)
            launcher = archive.read(root + 'START_KATAGO_EXPLAINER.cmd').decode('ascii')
            self.assertIn('"%~dp0portable-config.json" %*', launcher)
            self.assertNotIn('python', launcher.lower())
            configuration = json.loads(archive.read(root + 'portable-config.json'))
            for setting in ('backend', 'katago', 'altcommand', 'remote_url'):
                self.assertEqual(configuration['engine'][setting], '')
            self.assertEqual(configuration['engine']['model'], 'katrain/models/b10c384h6nbttflrs.bin.gz')
            self.assertEqual(configuration['engine']['config'], 'katrain/KataGo/analysis_config.cfg')
            manifest = json.loads(archive.read(root + 'build-manifest.json'))
            self.assertEqual(manifest['upstream']['archive_sha256'], self.source_hash)
            self.assertEqual(set(manifest['files_sha256']),
                             {name[len(root):] for name in names if name != root + 'build-manifest.json'})
            for name, expected in manifest['files_sha256'].items():
                self.assertEqual(hashlib.sha256(archive.read(root + name)).hexdigest(), expected, name)
            installed = json.loads(archive.read(root + 'KaTrain/_internal/katrain-explainer-install.json'))
            self.assertEqual(installed['package'], '_internal/katrain_explainer')
            self.assertNotIn(str(self.base), archive.read(root + 'build-manifest.json').decode())
            self.assertNotIn(str(self.base), archive.read(root + 'KaTrain/_internal/katrain-explainer-install.json').decode())
        self.assertEqual({path.relative_to(self.host): path.read_bytes()
                          for path in self.host.rglob('*') if path.is_file()}, original)
        self.assertEqual(Path(result['sha256_file']).read_text().split()[0], portable.sha256(result['archive']))
        self.assertEqual(list((self.base / 'dist').glob('.portable-build-*')), [])

    def test_identical_inputs_produce_identical_zip_bytes(self):
        first = self.build('first')
        second = self.build('second')
        self.assertEqual(first['sha256'], second['sha256'])

    def test_extra_personal_files_are_rejected_before_output(self):
        (self.host / 'personal.log').write_text('private', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'match the archive exactly'):
            self.build()
        self.assertFalse((self.base / 'dist').exists())

    def test_modified_gui_is_rejected_without_mutation(self):
        gui = self.host / '_internal/katrain/gui.kv'
        gui.write_bytes(b'# modified')
        with self.assertRaisesRegex(ValueError, 'Source was modified'):
            self.build()
        self.assertEqual(gui.read_bytes(), b'# modified')

    def test_archive_checksum_failure_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SHA256 does not match'):
            portable.verify_source(self.host, self.archive, '0' * 64)

    def test_bad_host_layout_or_architecture_is_rejected(self):
        engine = self.host / portable.ENGINE
        engine.unlink()
        self.refresh_archive()
        with self.assertRaisesRegex(ValueError, 'missing required'):
            self.build()
        engine.write_bytes(b'not an executable')
        self.refresh_archive()
        with self.assertRaisesRegex(ValueError, 'Invalid Windows executable'):
            self.build()

    def test_path_like_version_and_nested_output_are_rejected(self):
        for version in ('../../escape', '01.2.3', '0.2.0-beta..1', '0.2.0-beta.01'):
            with self.subTest(version=version), self.assertRaisesRegex(ValueError, 'Version must'):
                portable.build_portable(self.host, self.archive, version, self.base / 'dist')
        with self.assertRaisesRegex(ValueError, 'inside the clean source'):
            portable.build_portable(self.host, self.archive, '0.2.0', self.host / 'dist')

    def test_missing_license_never_emits_artifact(self):
        (self.licenses / 'KataGo-Network-LICENSE.txt').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing required redistribution'):
            self.build()
        self.assertFalse((self.base / 'dist').exists())

    def test_installer_failure_cleans_staging_and_leaves_source_intact(self):
        gui = (self.host / '_internal/katrain/gui.kv').read_bytes()
        with patch.object(portable.installer, 'install', side_effect=ValueError('simulated install failure')):
            with self.assertRaisesRegex(ValueError, 'simulated install failure'):
                self.build()
        self.assertEqual((self.host / '_internal/katrain/gui.kv').read_bytes(), gui)
        self.assertEqual(list((self.base / 'dist').iterdir()), [])

    def test_existing_artifact_is_not_overwritten(self):
        result = self.build()
        artifact = Path(result['archive']).read_bytes()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.build()
        self.assertEqual(Path(result['archive']).read_bytes(), artifact)


if __name__ == '__main__':
    unittest.main()
