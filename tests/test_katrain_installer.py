"""Exercise installer mutations in fake temporary distributions only.

The compact KV has the pinned insertion structure; its hash and the list of
replacements are patched for these isolated tests. The complete redesign is
checked against a copy of the real KaTrain v1.20.0 layout file.
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
            "                            id: controls\n"
            "        NavigationDrawer:\n").encode('utf-8')
REAL_GUI = PROJECT_DIR / 'tests' / 'fixtures' / 'katrain-1.20.0-gui.kv'
DOCK_ONLY = [installer.gui_patch.REPLACEMENTS[-1]]


class KaTrainInstallerTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        hash_override = patch.object(installer, 'ORIGINAL_GUI_SHA256', installer.digest(ORIGINAL))
        hash_override.start()
        self.addCleanup(hash_override.stop)
        dock_only = patch.object(installer.gui_patch, 'REPLACEMENTS', DOCK_ONLY)
        dock_only.start()
        self.addCleanup(dock_only.stop)
        # The installer resolves paths. Windows runners can return an 8.3 temp
        # alias (RUNNER~1), so mocks must use the same canonical path.
        self.base = Path(self.directory.name).resolve()
        self.katrain = self.base / 'FakeKaTrain'
        self.gui = self.katrain / '_internal' / 'katrain' / 'gui.kv'
        self.gui.parent.mkdir(parents=True)
        self.gui.write_bytes(ORIGINAL)
        self.exe = self.katrain / 'KaTrain.exe'
        self.exe.write_bytes(b'fake executable, never launched')
        self.project = self.base / 'FakeProject'
        self.source = self.project / 'plugins' / 'katrain'
        self.source.mkdir(parents=True)
        for name in installer.PLUGIN_FILES:
            (self.source / name).write_bytes(f'# fake {name}\n'.encode('utf-8'))
        (self.project / 'explainer').mkdir()
        for name in installer.CORE_FILES:
            (self.project / 'explainer' / name).write_bytes(f'# fake core {name}\n'.encode('utf-8'))
        self.backup = self.gui.with_name('gui.kv.explainer-original')
        self.manifest = self.katrain / '_internal' / 'katrain-explainer-install.json'
        self.package = self.katrain / '_internal' / 'katrain_explainer'
        self.assertEqual(installer.digest(ORIGINAL), installer.ORIGINAL_GUI_SHA256)

    def install(self):
        return installer.install(self.katrain, project_dir=self.project)

    def test_patch_adds_imports_and_one_dock(self):
        patched = installer.patch_gui(ORIGINAL)
        normalized = patched.decode('utf-8')
        old, new = DOCK_ONLY[0]
        header = installer.MARKER + '\n' + installer.gui_patch.IMPORTS
        self.assertEqual(normalized.count(installer.MARKER), 1)
        self.assertEqual(normalized.count('KaTrainExplainerPanel:\n'), 1)
        self.assertEqual(normalized.count('id: controls'), 1)
        self.assertLess(normalized.index(header), normalized.index('id: explainer_panel'))
        self.assertLess(normalized.index('id: explainer_panel'), normalized.index('id: controls'))
        self.assertEqual(normalized.replace(header, '').replace(new, old).encode('utf-8'), ORIGINAL)

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
        for name in ('__init__.py', 'bridge.py', 'panel.py'):
            self.assertFalse((self.package / name).exists())
        self.assertEqual(self.exe.read_bytes(), b'fake executable, never launched')

    def test_plugin_is_self_contained_and_needs_no_server_or_python(self):
        self.install()
        for name in installer.PLUGIN_FILES + installer.CORE_FILES:
            self.assertTrue((self.package / name).is_file(), name)
        self.assertEqual((self.package / 'service.py').read_bytes(), b'# fake core service.py\n')
        self.assertFalse((self.package / 'server.py').exists())
        self.assertFalse((self.package / 'settings.json').exists())
        manifest = json.loads(self.manifest.read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], 4)
        installer.uninstall(self.katrain)
        for name in installer.PLUGIN_FILES + installer.CORE_FILES:
            self.assertFalse((self.package / name).exists(), name)

    def test_update_removes_files_an_older_version_installed(self):
        self.install()
        manifest = json.loads(self.manifest.read_text(encoding='utf-8'))
        manifest['files'].extend(['retired_module.py', 'settings.json'])
        self.manifest.write_text(json.dumps(manifest), encoding='utf-8')
        (self.package / 'retired_module.py').write_bytes(b'# old\n')
        (self.package / 'settings.json').write_bytes(b'{"engine":"katrain"}')
        self.install()
        self.assertFalse((self.package / 'retired_module.py').exists())
        self.assertFalse((self.package / 'settings.json').exists())
        self.assertTrue((self.package / 'bridge.py').is_file())

    def test_failed_stale_deletion_restores_deleted_files_and_previous_install(self):
        self.install()
        manifest = json.loads(self.manifest.read_text(encoding='utf-8'))
        manifest['files'].extend(['old_first.py', 'old_second.py'])
        self.manifest.write_text(json.dumps(manifest), encoding='utf-8')
        first, second = self.package / 'old_first.py', self.package / 'old_second.py'
        first.write_bytes(b'# earlier version first\n')
        second.write_bytes(b'# earlier version second\n')
        gui_before, manifest_before = self.gui.read_bytes(), self.manifest.read_bytes()
        bridge_before = (self.package / 'bridge.py').read_bytes()
        (self.source / 'bridge.py').write_bytes(b'# new plugin version\n')
        original_unlink = Path.unlink

        def fail_second(path, *args, **kwargs):
            if path == second:
                raise OSError('simulated stale deletion failure')
            return original_unlink(path, *args, **kwargs)

        with patch.object(Path, 'unlink', fail_second):
            with self.assertRaisesRegex(OSError, 'stale deletion'):
                self.install()
        self.assertEqual(first.read_bytes(), b'# earlier version first\n')
        self.assertEqual(second.read_bytes(), b'# earlier version second\n')
        self.assertEqual(self.gui.read_bytes(), gui_before)
        self.assertEqual(self.manifest.read_bytes(), manifest_before)
        self.assertEqual((self.package / 'bridge.py').read_bytes(), bridge_before)
        self.assertEqual(self.install()['status'], 'installed')
        self.assertFalse(first.exists())
        self.assertFalse(second.exists())

    def test_missing_core_module_is_refused_before_touching_katrain(self):
        (self.project / 'explainer' / 'joseki.py').unlink()
        with self.assertRaisesRegex(ValueError, 'joseki.py'):
            self.install()
        self.assertEqual(self.gui.read_bytes(), ORIGINAL)
        self.assertFalse(self.manifest.exists())

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
        for name in ('__init__.py', 'bridge.py', 'panel.py'):
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


class RealLayoutTests(unittest.TestCase):
    """The redesign against KaTrain v1.20.0's actual layout file."""

    def setUp(self):
        self.lf = REAL_GUI.read_bytes().replace(b'\r\n', b'\n')
        self.crlf = self.lf.replace(b'\n', b'\r\n')

    def test_fixture_is_the_pinned_release_file(self):
        self.assertEqual(installer.digest(self.crlf), installer.ORIGINAL_GUI_SHA256)

    def test_every_replacement_applies_once_and_line_endings_are_kept(self):
        patched = installer.patch_gui(self.crlf).decode('utf-8')
        self.assertNotIn('\n', patched.replace('\r\n', ''))
        text = patched.replace('\r\n', '\n')
        for old, new in installer.gui_patch.REPLACEMENTS:
            self.assertEqual(text.count(new), 1, new.splitlines()[0])
        self.assertEqual(text.count('id: explainer_panel'), 1)
        self.assertEqual(text.count('#:import kx katrain_explainer.skin'), 1)
        self.assertEqual(installer.gui_patch.apply(self.lf.decode('utf-8')), text)

    def test_widget_ids_katrain_relies_on_are_all_kept(self):
        import re
        ids = lambda source: sorted(re.findall(r'^\s+id: (\w+)', source, re.M))
        original = self.lf.decode('utf-8')
        patched = installer.gui_patch.apply(original)
        self.assertEqual(ids(patched), sorted(ids(original) + ['explainer_panel']))

    def test_a_changed_layout_is_refused_rather_than_half_styled(self):
        changed = self.lf.decode('utf-8').replace('<StatsBox>', '<StatsBoxRenamed>')
        with self.assertRaises(ValueError):
            installer.gui_patch.apply(changed)

    def test_skin_assets_named_by_the_installer_exist(self):
        for name in installer.PLUGIN_FILES:
            self.assertTrue((PROJECT_DIR / 'plugins' / 'katrain' / name).is_file(), name)


if __name__ == '__main__':
    unittest.main()
