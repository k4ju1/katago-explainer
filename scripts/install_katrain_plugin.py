"""Install or remove the reversible KaTrain v1.20.0 explanation UI extension.
安装或卸载可恢复的 KaTrain v1.20.0 原生讲解扩展。
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys


PROJECT_DIR = Path(__file__).resolve().parents[1]
ORIGINAL_GUI_SHA256 = '0c015263cd52305c9d64812c1d013173e69a4e4a131f40847d9bbe455936e9df'
MARKER = '# KataGo Explainer native integration v1'
IMPORT = '#:import KaTrainExplainerPanel katrain_explainer.panel.KaTrainExplainerPanel'
ANCHOR = '                        ControlsPanel:\n                            id: controls'
DOCK = ('                        KaTrainExplainerPanel:\n'
        '                            id: explainer_panel\n'
        '                            katrain: root\n'
        '                            size_hint_y: None\n'
        '                            height: dp(76)\n')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def patch_gui(original):
    if digest(original) != ORIGINAL_GUI_SHA256:
        raise ValueError('此界面文件与支持的 KaTrain 1.20.0 不符，未修改。 / Unsupported KaTrain UI file; no changes made.')
    source = original.decode('utf-8')
    newline = '\r\n' if '\r\n' in source else '\n'
    normalized = source.replace('\r\n', '\n')
    if normalized.count(ANCHOR) != 1:
        raise ValueError('未找到唯一的界面挂载点 / A unique UI insertion point was not found')
    first_line, rest = normalized.split('\n', 1)
    patched = first_line + '\n' + MARKER + '\n' + IMPORT + '\n' + rest
    patched = patched.replace(ANCHOR, DOCK + ANCHOR)
    return patched.replace('\n', newline).encode('utf-8')


def install(katrain_dir, python_path=None, project_dir=PROJECT_DIR):
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
    source_package = project_dir / 'plugins' / 'katrain'
    names = ('__init__.py', 'bridge.py', 'panel.py')
    contents = {name: (source_package / name).read_bytes() for name in names}
    runtime = Path(python_path or sys.executable).resolve()
    if not runtime.is_file() or not (project_dir / 'explainer' / 'server.py').is_file():
        raise ValueError('Python 或项目路径缺失 / Missing Python runtime or project path')
    settings = {'backend_url': 'http://127.0.0.1:8788',
                'project_path': str(project_dir), 'python_path': str(runtime)}
    previous_files = {path: path.read_bytes() if path.is_file() else None
                      for path in [*(package / name for name in names), package / 'settings.json', backup, manifest_path]}
    package.mkdir(parents=True, exist_ok=True)
    try:
        for name, content in contents.items():
            (package / name).write_bytes(content)
        (package / 'settings.json').write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding='utf-8')
        if not backup.exists():
            backup.write_bytes(original)
        temporary = gui_path.with_name('gui.kv.explainer-tmp')
        temporary.write_bytes(patched)
        temporary.replace(gui_path)
        manifest = {'version': 1, 'target': 'KaTrain v1.20.0',
                    'original_sha256': digest(original), 'patched_sha256': digest(patched),
                    'files': list(names) + ['settings.json'], 'package': str(package)}
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
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
    if not all(isinstance(name, str) and Path(name).name == name for name in manifest['files']):
        raise ValueError('扩展文件名无效 / Invalid plugin filename')
    gui_path.write_bytes(original)
    # Only remove this install's named files, without recursive folder deletion.
    for name in manifest['files']:
        if Path(name).name != name:
            raise ValueError('扩展文件名无效 / Invalid plugin filename')
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
    parser.add_argument('--python', type=Path, default=Path(sys.executable))
    parser.add_argument('--uninstall', action='store_true', help='恢复原始界面 / Restore the original UI')
    args = parser.parse_args()
    try:
        result = uninstall(args.katrain_dir) if args.uninstall else install(args.katrain_dir, args.python)
    except (OSError, ValueError) as error:
        parser.exit(1, f'扩展操作失败 / Plugin operation failed: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
