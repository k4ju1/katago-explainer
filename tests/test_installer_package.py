"""Validate installer payloads without launching Setup or the bundled host."""

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import struct
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('installer_package_under_test', PROJECT / 'scripts/build_installer.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
VERSION = '0.2.0-beta.2'
ROOT = f'KataGo-Explainer-v{VERSION}-win64'


class InstallerPackageTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name).resolve()
        self.archive = self.base / 'portable.zip'
        self.compiler = self.base / 'compiler' / 'ISCC.exe'
        self.compiler.parent.mkdir()
        self.compiler.write_bytes(b'Compiler fixture; never executed')
        language = self.compiler.parent / 'Languages/ChineseSimplified.isl'
        language.parent.mkdir()
        language.write_text('[LangOptions]\nLanguageName=Chinese\n', encoding='utf-8')
        pe = bytearray(70)
        pe[:2] = b'MZ'
        struct.pack_into('<I', pe, 60, 64)
        pe[64:70] = b'PE\0\0\x64\x86'
        self.pe = bytes(pe)
        configuration = {'general': {'lang': 'en'}, 'contribute': {'username': '', 'password': ''},
                         'engine': {'backend': '', 'katago': '', 'altcommand': '', 'remote_url': '',
                                    'model': 'katrain/models/b10c384h6nbttflrs.bin.gz',
                                    'config': 'katrain/KataGo/analysis_config.cfg'}}
        self.files = {name: b'Fixture application resource' for name in builder.REQUIRED}
        self.files.update({'KaTrain/KaTrain.exe': self.pe, 'KaTrain/' + builder.portable.ENGINE: self.pe,
                           'KaTrain/' + builder.portable.MODEL: b'\x1f\x8btest model',
                           'portable-config.json': json.dumps(configuration).encode('utf-8')})
        self.manifest = {'schema_version': 1, 'product': 'KataGo Explainer', 'version': VERSION,
                         'platform': 'windows-x64', 'source_commit': '0123456789abcdef'}
        self.refresh_archive()

    def refresh_archive(self, extra=None, hashes=True):
        if hashes:
            self.manifest['files_sha256'] = {name: hashlib.sha256(content).hexdigest()
                                              for name, content in self.files.items()}
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for name, content in self.files.items():
                archive.writestr(ROOT + '/' + name, content)
            archive.writestr(ROOT + '/build-manifest.json', json.dumps(self.manifest))
            if extra:
                archive.writestr(*extra)

    def fake_compile(self, arguments, **kwargs):
        self.arguments = arguments
        definitions = dict(arg[2:].split('=', 1) for arg in arguments if arg.startswith('/D'))
        self.assertEqual(definitions['AppVersion'], VERSION)
        self.assertEqual(definitions['AppNumericVersion'], '0.2.0.0')
        config = json.loads(Path(definitions['ChineseConfigFile']).read_text(encoding='utf-8'))
        self.assertEqual(config['general']['lang'], 'cn')
        self.assertFalse(config['general']['load_sgf_rewind'])
        english = json.loads(Path(definitions['EnglishConfigFile']).read_text(encoding='utf-8'))
        self.assertEqual(english['general']['lang'], 'en')
        self.assertFalse(english['general']['load_sgf_rewind'])
        original = json.loads((Path(definitions['PayloadDir']) / 'portable-config.json').read_text(encoding='utf-8'))
        self.assertEqual(original['general']['lang'], 'en')
        output = Path(definitions['OutputDirPath']) / f'KataGo-Explainer-Setup-v{VERSION}-win64.exe'
        output.write_bytes(self.pe)
        return SimpleNamespace(returncode=0, stdout='', stderr='')

    def build(self):
        return builder.build_installer(self.archive, VERSION, self.base / 'dist', self.compiler)

    def test_complete_payload_is_verified_before_extraction(self):
        destination = self.base / 'extracted'
        manifest = builder.extract_verified_release(self.archive, destination, VERSION)
        self.assertEqual(manifest['source_commit'], '0123456789abcdef')
        for name, content in self.files.items():
            self.assertEqual((destination / name).read_bytes(), content)

    def test_installer_build_metadata_and_config_variants_are_verified(self):
        original_archive = self.archive.read_bytes()
        with patch.object(builder.subprocess, 'run', side_effect=self.fake_compile) as compiler:
            result = self.build()
        compiler.assert_called_once()
        self.assertEqual(Path(result['installer']).read_bytes(), self.pe)
        self.assertEqual(Path(result['sha256_file']).read_text().split()[0], result['sha256'])
        metadata = json.loads(Path(result['build_manifest']).read_text(encoding='utf-8'))
        self.assertEqual(metadata['portable_archive_sha256'], builder.portable.sha256(self.archive))
        self.assertEqual(metadata['installation_scope'], 'current-user')
        self.assertNotEqual(metadata['initial_configurations_sha256']['english'],
                            metadata['initial_configurations_sha256']['chinesesimplified'])
        self.assertNotIn(str(self.base), Path(result['build_manifest']).read_text(encoding='utf-8'))
        self.assertEqual(self.archive.read_bytes(), original_archive)
        self.assertFalse(list((self.base / 'dist').glob('.installer-build-*')))

    def test_corrupt_hash_is_rejected_before_any_extraction_or_compile(self):
        self.files['QUICK_START.md'] = b'Changed after hashing'
        self.refresh_archive(hashes=False)
        destination = self.base / 'extracted'
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
            builder.extract_verified_release(self.archive, destination, VERSION)
        self.assertFalse(destination.exists())

    def test_unrecorded_file_and_wrong_version_are_rejected(self):
        self.refresh_archive(extra=(ROOT + '/unrecorded.txt', b'Untracked'))
        with self.assertRaisesRegex(ValueError, 'cover every payload'):
            builder.extract_verified_release(self.archive, self.base / 'extract', VERSION)
        self.manifest['version'] = '0.1.0'
        self.refresh_archive()
        with self.assertRaisesRegex(ValueError, 'version or platform'):
            builder.extract_verified_release(self.archive, self.base / 'extract', VERSION)

    def test_unsafe_windows_paths_are_rejected(self):
        for name in ('../outside.txt', ROOT + '/../outside.txt', ROOT + '/evil:stream',
                     ROOT + '/CON.txt', ROOT + '/trailing.'):
            with self.subTest(name=name):
                self.refresh_archive(extra=(name, b'Unsafe'))
                with self.assertRaisesRegex(ValueError, 'unsafe or unexpected'):
                    builder.extract_verified_release(self.archive, self.base / 'extract', VERSION)
        self.assertFalse((self.base / 'outside.txt').exists())
        backslash = zipfile.ZipInfo(ROOT + '/evil.txt')
        backslash.filename = ROOT + '\\evil.txt'
        self.refresh_archive(extra=(backslash, b'Unsafe Windows separator'))
        with self.assertRaisesRegex(ValueError, 'unsafe or unexpected'):
            builder.extract_verified_release(self.archive, self.base / 'extract', VERSION)

    def test_symlink_and_case_collision_are_rejected(self):
        link = zipfile.ZipInfo(ROOT + '/link')
        link.external_attr = 0o120777 << 16
        self.refresh_archive(extra=(link, b'../outside'))
        with self.assertRaisesRegex(ValueError, 'symbolic links'):
            builder.extract_verified_release(self.archive, self.base / 'extract', VERSION)
        self.refresh_archive(extra=(ROOT + '/quick_START.md', b'Duplicate'))
        with self.assertRaisesRegex(ValueError, 'case-colliding'):
            builder.extract_verified_release(self.archive, self.base / 'extract', VERSION)

    def test_bad_architecture_or_nonportable_config_is_rejected(self):
        self.files['KaTrain/KaTrain.exe'] = b'not an executable'
        self.refresh_archive()
        with self.assertRaisesRegex(ValueError, 'Invalid Windows executable'):
            builder.extract_verified_release(self.archive, self.base / 'extract', VERSION)
        self.files['KaTrain/KaTrain.exe'] = self.pe
        configuration = json.loads(self.files['portable-config.json'])
        configuration['engine']['katago'] = r'C:\personal\katago.exe'
        self.files['portable-config.json'] = json.dumps(configuration).encode()
        self.refresh_archive()
        with self.assertRaisesRegex(ValueError, 'included engine and model'):
            builder.extract_verified_release(self.archive, self.base / 'second', VERSION)

    def test_compiler_failure_leaves_no_artifact_or_staging(self):
        with patch.object(builder.subprocess, 'run', return_value=SimpleNamespace(
                returncode=2, stdout='', stderr='simulated compiler failure')):
            with self.assertRaisesRegex(ValueError, 'simulated compiler failure'):
                self.build()
        self.assertEqual(list((self.base / 'dist').iterdir()), [])

    def test_missing_chinese_language_and_existing_output_are_rejected(self):
        shutil.rmtree(self.compiler.parent / 'Languages')
        with self.assertRaisesRegex(ValueError, 'language not found'):
            builder.build_installer(self.archive, VERSION, self.base / 'dist', self.compiler,
                                     chinese_isl=self.base / 'missing.isl')
        language = self.compiler.parent / 'Languages/ChineseSimplified.isl'
        language.parent.mkdir()
        language.write_text('fixture', encoding='utf-8')
        with patch.object(builder.subprocess, 'run', side_effect=self.fake_compile):
            result = self.build()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.build()
        self.assertEqual(Path(result['installer']).read_bytes(), self.pe)

    def test_setup_contract_preserves_user_settings_and_launches_native_host(self):
        script = (PROJECT / 'packaging/windows/setup.iss').read_text(encoding='utf-8')
        self.assertIn('PrivilegesRequired=lowest', script)
        self.assertIn('DefaultDirName={localappdata}\\Programs\\KataGo Explainer', script)
        self.assertIn('AppId={{5ED213A9-D9EC-47D8-A41C-7646A2F46843}', script)
        self.assertEqual(script.count('Flags: onlyifdoesntexist uninsneveruninstall'), 2)
        self.assertEqual(script.count('Parameters: """{app}\\portable-config.json"""'), 2)
        self.assertIn('""{app}\\examples\\shusaku-demo.sgf"""', script)
        self.assertIn('skipifsilent runasoriginaluser', script)
        self.assertNotIn('[UninstallDelete]', script)
        self.assertNotIn('Filename: "{app}\\START_KATAGO_EXPLAINER.cmd"', script)


if __name__ == '__main__':
    unittest.main()
