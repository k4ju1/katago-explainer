"""Install or remove the reversible KaTrain v1.20.0 explanation plugin.
安装或卸载可恢复的 KaTrain v1.20.0 着法讲解插件。

The plugin is self-contained once installed: its panel, bridge, interface
skin and the explanation pipeline are copied into KaTrain and run inside
KaTrain, using KaTrain's own KataGo engine. KaTrain's ``gui.kv`` is replaced
by a restyled copy; the original is kept beside it and restored on uninstall. This script is only needed to install, update
or remove it.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import katrain_gui_patch as gui_patch  # noqa: E402

ORIGINAL_GUI_SHA256 = '0c015263cd52305c9d64812c1d013173e69a4e4a131f40847d9bbe455936e9df'
MARKER = gui_patch.MARKER
# The panel, the bridge to KaTrain's engine, and the look of the whole window.
PLUGIN_FILES = ('__init__.py', 'bridge.py', 'panel.py', 'skin.py', 'chat.py', 'chat_context.py', 'llm.py',
                'kx_board.png', 'kx_stone_b.png', 'kx_stone_w.png', 'kx_shadow.png')
# The explanation pipeline, copied beside the plugin so KaTrain needs nothing else.
CORE_FILES = ('board.py', 'engine.py', 'explanation.py', 'joseki.py', 'service.py', 'sgf.py', 'terms.py')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def patch_gui(original):
    if digest(original) != ORIGINAL_GUI_SHA256:
        raise ValueError('此界面文件与支持的 KaTrain 1.20.0 不符，未修改。 / Unsupported KaTrain UI file; no changes made.')
    return gui_patch.apply(original.decode('utf-8')).encode('utf-8')


def install(katrain_dir, project_dir=PROJECT_DIR):
    katrain_dir = Path(katrain_dir).resolve()
    project_dir = Path(project_dir).resolve()
    internal = katrain_dir / '_internal'
    gui_path = internal / 'katrain' / 'gui.kv'
    backup = gui_path.with_name('gui.kv.explainer-original')
    manifest_path = internal / 'katrain-explainer-install.json'
    package = internal / 'katrain_explainer'
    if not (katrain_dir / 'KaTrain.exe').is_file() or not gui_path.is_file():
        raise ValueError('请选择包含 KaTrain.exe 的目录 / Select the folder containing KaTrain.exe')
    current = gui_path.read_bytes()
    manifest = None
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if digest(current) != manifest['patched_sha256']:
            raise ValueError('安装后的界面文件被修改，未覆盖。 / The installed UI file was changed; it was not overwritten.')
        if not backup.is_file() or digest(backup.read_bytes()) != manifest['original_sha256']:
            raise ValueError('原始备份缺失或不匹配 / Original backup missing or mismatched')
        original = backup.read_bytes()
    else:
        occupied_package = package.exists() and any(item.name != '__pycache__' for item in package.iterdir())
        if backup.exists() or occupied_package:
            raise ValueError('存在未登记的同名扩展或备份，未覆盖。 / Unregistered plugin or backup already exists.')
        original = current
    patched = patch_gui(original)
    sources = [project_dir / 'plugins' / 'katrain' / name for name in PLUGIN_FILES]
    sources += [project_dir / 'explainer' / name for name in CORE_FILES]
    missing = [str(path) for path in sources if not path.is_file()]
    if missing:
        raise ValueError('项目文件缺失 / Missing project files: ' + ', '.join(missing))
    names = PLUGIN_FILES + CORE_FILES
    contents = {path.name: path.read_bytes() for path in sources}
    # Files of an earlier version that this version no longer ships are removed on success.
    previous_names = manifest.get('files', []) if manifest else []
    if not isinstance(previous_names, list) or not all(
            isinstance(name, str) and Path(name).name == name and name not in ('', '.', '..')
            for name in previous_names):
        raise ValueError('扩展文件名无效 / Invalid plugin filename')
    stale = [package / name for name in previous_names if name not in names]
    previous_files = {path: path.read_bytes() if path.is_file() else None
                      for path in [*(package / name for name in names), *stale, backup, manifest_path]}
    package.mkdir(parents=True, exist_ok=True)
    try:
        for name, content in contents.items():
            (package / name).write_bytes(content)
        if not backup.exists():
            backup.write_bytes(original)
        temporary = gui_path.with_name('gui.kv.explainer-tmp')
        temporary.write_bytes(patched)
        temporary.replace(gui_path)
        manifest = {'version': 4, 'target': 'KaTrain v1.20.0',
                    'original_sha256': digest(original), 'patched_sha256': digest(patched),
                    'files': list(names), 'package': str(package)}
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        for path in stale:
            if path.is_file():
                path.unlink()
    except Exception:
        # A failed install must leave the original UI loadable.
        gui_path.write_bytes(current)
        for path, previous in previous_files.items():
            if previous is None:
                if path.is_file():
                    path.unlink()
            else:
                path.write_bytes(previous)
        temporary = gui_path.with_name('gui.kv.explainer-tmp')
        if temporary.is_file():
            temporary.unlink()
        raise
    return {'status': 'installed', 'katrain_dir': str(katrain_dir),
            'backup': str(backup), 'gui_sha256': digest(patched)}


def uninstall(katrain_dir):
    katrain_dir = Path(katrain_dir).resolve()
    internal = katrain_dir / '_internal'
    gui_path = internal / 'katrain' / 'gui.kv'
    backup = gui_path.with_name('gui.kv.explainer-original')
    manifest_path = internal / 'katrain-explainer-install.json'
    if not manifest_path.is_file():
        return {'status': 'not_installed'}
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if digest(gui_path.read_bytes()) != manifest['patched_sha256']:
        raise ValueError('当前界面文件有其他修改，未自动恢复。 / UI has other changes; automatic restore was refused.')
    original = backup.read_bytes()
    if digest(original) != manifest['original_sha256']:
        raise ValueError('备份校验失败 / Backup verification failed')
    package = internal / 'katrain_explainer'
    if not isinstance(manifest['files'], list) or not all(
            isinstance(name, str) and Path(name).name == name and name not in ('', '.', '..')
            for name in manifest['files']):
        raise ValueError('扩展文件名无效 / Invalid plugin filename')
    gui_path.write_bytes(original)
    # Only remove this install's named files, without recursive folder deletion.
    for name in manifest['files']:
        candidate = package / name
        if candidate.is_file():
            candidate.unlink()
    backup.unlink()
    manifest_path.unlink()
    return {'status': 'uninstalled', 'gui_sha256': digest(original)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--katrain-dir', type=Path,
                        default=PROJECT_DIR.parent / 'KaTrain-1.20.0' / 'KaTrain')
    parser.add_argument('--uninstall', action='store_true', help='恢复原始界面 / Restore the original UI')
    args = parser.parse_args()
    try:
        result = uninstall(args.katrain_dir) if args.uninstall else install(args.katrain_dir)
    except (OSError, ValueError) as error:
        parser.exit(1, f'扩展操作失败 / Plugin operation failed: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
