"""Exercise installer mutations in fake temporary distributions only.

The compact KV has the pinned insertion structure; its hash is patched for
these isolated tests. The actual release hash is verified separately.
No installed executable, UI resource, or Python runtime is changed or launched.
"""

import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'katrain_installer_under_test', PROJECT_DIR / 'scripts' / 'install_katrain_plugin.py')
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)
ORIGINAL = ("#:kivy 2.3.0\n<KaTrainGui>:\n"
            "    BoxLayout:\n        BoxLayout:\n            BoxLayout:\n"
            "                BoxLayout:\n                    BoxLayout:\n"
            "                        ControlsPanel:\n"
            "                            id: controls\n").encode('utf-8')


class KaTrainInstallerTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        hash_override = patch.object(installer, 'ORIGINAL_GUI_SHA256', installer.digest(ORIGINAL))
        hash_override.start()
        self.addCleanup(hash_override.stop)
        self.base = Path(self.directory.name)
        self.katrain = self.base / 'FakeKaTrain'
        self.gui = self.katrain / '_internal' / 'katrain' / 'gui.kv'
        self.gui.parent.mkdir(parents=True)
        self.gui.write_bytes(ORIGINAL)
        self.exe = self.katrain / 'KaTrain.exe'
        self.exe.write_bytes(b'fake executable, never launched')
        self.project = self.base / 'FakeProject'
        self.source = self.project / 'plugins' / 'katrain'
        self.source.mkdir(parents=True)
        for name in ('__init__.py', 'bridge.py', 'panel.py'):
            (self.source / name).write_bytes(f'# fake {name}\n'.encode('utf-8'))
        (self.project / 'explainer').mkdir()
        (self.project / 'explainer' / 'server.py').write_bytes(b'# fake server\n')
        self.python = self.base / 'fake-python.exe'
        self.python.write_bytes(b'fake Python, never launched')
        self.backup = self.gui.with_name('gui.kv.explainer-original')
        self.manifest = self.katrain / '_internal' / 'katrain-explainer-install.json'
        self.package = self.katrain / '_internal' / 'katrain_explainer'
        self.assertEqual(installer.digest(ORIGINAL), installer.ORIGINAL_GUI_SHA256)

    def install(self):
        return installer.install(self.katrain, python_path=self.python, project_dir=self.project)

    def test_patch_adds_one_import_and_one_dock(self):
        patched = installer.patch_gui(ORIGINAL)
        normalized = patched.decode('utf-8').replace('\r\n', '\n')
        self.assertEqual(normalized.count(installer.MARKER), 1)
        self.assertEqual(normalized.count(installer.IMPORT), 1)
        self.assertEqual(normalized.count(installer.DOCK), 1)
        self.assertEqual(normalized.count(installer.ANCHOR), 1)
        self.assertLess(normalized.index(installer.IMPORT), normalized.index(installer.DOCK))
        self.assertLess(normalized.index(installer.DOCK), normalized.index(installer.ANCHOR))
        restored = normalized.replace(installer.MARKER + '\n' + installer.IMPORT + '\n', '')
        restored = restored.replace(installer.DOCK, '')
        self.assertEqual(restored.encode('utf-8'), ORIGINAL)

    def test_reinstall_is_idempotent_and_original_backup_stays_intact(self):
        first = self.install()
        first_gui = self.gui.read_bytes()
        first_manifest = self.manifest.read_bytes()
        second = self.install()
        self.assertEqual(first['gui_sha256'], second['gui_sha256'])
        self.assertEqual(self.gui.read_bytes(), first_gui)
        self.assertEqual(self.manifest.read_bytes(), first_manifest)
        self.assertEqual(self.backup.read_bytes(), ORIGINAL)
        for name in ('__init__.py', 'bridge.py', 'panel.py'):
            self.assertEqual((self.package / name).read_bytes(), (self.source / name).read_bytes())
        self.assertEqual(self.exe.read_bytes(), b'fake executable, never launched')

    def test_uninstall_restores_original_sha_and_removes_owned_files(self):
        self.install()
        result = installer.uninstall(self.katrain)
        self.assertEqual(result['status'], 'uninstalled')
        self.assertEqual(result['gui_sha256'], installer.ORIGINAL_GUI_SHA256)
        self.assertEqual(self.gui.read_bytes(), ORIGINAL)
        self.assertFalse(self.manifest.exists())
        self.assertFalse(self.backup.exists())
        for name in ('__init__.py', 'bridge.py', 'panel.py', 'settings.json'):
            self.assertFalse((self.package / name).exists())
        self.assertEqual(self.exe.read_bytes(), b'fake executable, never launched')

    def test_unknown_original_gui_is_refused_without_creating_install_artifacts(self):
        unknown = ORIGINAL + b'\n# local UI modification\n'
        self.gui.write_bytes(unknown)
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(self.gui.read_bytes(), unknown)
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.manifest.exists())
        self.assertFalse(self.package.exists())

    def test_uninstall_refuses_edited_installed_gui_without_touching_backup_or_package(self):
        self.install()
        changed = self.gui.read_bytes() + b'\n# later UI edit\n'
        self.gui.write_bytes(changed)
        manifest_before = self.manifest.read_bytes()
        with self.assertRaises(ValueError):
            installer.uninstall(self.katrain)
        self.assertEqual(self.gui.read_bytes(), changed)
        self.assertEqual(self.backup.read_bytes(), ORIGINAL)
        self.assertEqual(self.manifest.read_bytes(), manifest_before)
        self.assertTrue((self.package / 'panel.py').is_file())

    def test_invalid_manifest_filename_is_refused_before_restoring_gui(self):
        self.install()
        patched = self.gui.read_bytes()
        manifest = json.loads(self.manifest.read_text(encoding='utf-8'))
        manifest['files'].append('../unexpected.py')
        self.manifest.write_text(json.dumps(manifest), encoding='utf-8')
        with self.assertRaises(ValueError):
            installer.uninstall(self.katrain)
        self.assertEqual(self.gui.read_bytes(), patched)
        self.assertEqual(self.backup.read_bytes(), ORIGINAL)
        self.assertTrue((self.package / 'panel.py').is_file())

    def test_uninstall_then_reinstall_accepts_empty_or_cache_only_package(self):
        for with_cache in (False, True):
            with self.subTest(with_cache=with_cache):
                self.install()
                if with_cache:
                    cache = self.package / '__pycache__'
                    cache.mkdir(exist_ok=True)
                    (cache / 'panel.cpython-311.pyc').write_bytes(b'fake cache')
                installer.uninstall(self.katrain)
                self.assertEqual(self.gui.read_bytes(), ORIGINAL)
                result = self.install()
                self.assertEqual(result['status'], 'installed')
                self.assertEqual(self.backup.read_bytes(), ORIGINAL)
                installer.uninstall(self.katrain)

    def manifest_failure(self):
        original_write = Path.write_text
        def fail_manifest(path, *args, **kwargs):
            if path == self.manifest:
                raise OSError('simulated manifest write failure')
            return original_write(path, *args, **kwargs)
        return patch.object(Path, 'write_text', fail_manifest)

    def test_failed_first_install_rolls_back_gui_and_new_owned_files(self):
        with self.manifest_failure():
            with self.assertRaisesRegex(OSError, 'simulated manifest'):
                self.install()
        self.assertEqual(self.gui.read_bytes(), ORIGINAL)
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.manifest.exists())
        self.assertFalse(self.gui.with_name('gui.kv.explainer-tmp').exists())
        for name in ('__init__.py', 'bridge.py', 'panel.py', 'settings.json'):
            self.assertFalse((self.package / name).exists())
        # The rollback must leave a distribution that can be installed again.
        self.assertEqual(self.install()['status'], 'installed')

    def test_failed_reinstall_restores_previous_plugin_and_manifest(self):
        self.install()
        gui_before = self.gui.read_bytes()
        manifest_before = self.manifest.read_bytes()
        bridge_before = (self.package / 'bridge.py').read_bytes()
        (self.source / 'bridge.py').write_bytes(b'# changed plugin version\n')
        with self.manifest_failure():
            with self.assertRaisesRegex(OSError, 'simulated manifest'):
                self.install()
        self.assertEqual(self.gui.read_bytes(), gui_before)
        self.assertEqual(self.manifest.read_bytes(), manifest_before)
        self.assertEqual((self.package / 'bridge.py').read_bytes(), bridge_before)
        self.assertEqual(self.backup.read_bytes(), ORIGINAL)
        self.assertEqual(installer.uninstall(self.katrain)['status'], 'uninstalled')


if __name__ == '__main__':
    unittest.main()
