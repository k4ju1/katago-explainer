"""Build a verified Windows portable KaTrain + KataGo Explainer ZIP.

Only a fresh staging copy is patched. The supplied clean host must match the
official archive exactly; no user's settings, caches or logs are redistributed.
The ZIP does not require Python to run, using the upstream KaTrain executable.
"""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import sys
from tempfile import TemporaryDirectory
import zipfile


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import install_katrain_plugin as installer  # noqa: E402

SOURCE_URL = 'https://github.com/sanderland/katrain/releases/download/v1.20.0/KaTrain.zip'
SOURCE_SHA256 = '2f74b00790e3c5ef424c19db92f5a94cb95dd109322b7ad052394c9e80d2fb22'
MODEL = '_internal/katrain/models/b10c384h6nbttflrs.bin.gz'
ENGINE = '_internal/katrain/KataGo/katago.exe'
REQUIRED = ('KaTrain.exe', '_internal/katrain/gui.kv',
            '_internal/katrain/config.json', '_internal/katrain/KataGo/analysis_config.cfg',
            ENGINE, MODEL)
LAUNCHER = '''@echo off
setlocal
cd /d "%~dp0KaTrain"
if not exist "KaTrain.exe" (
  echo KaTrain.exe is missing. Extract the entire ZIP before starting.
  pause
  exit /b 1
)
start "" "KaTrain.exe" "%~dp0portable-config.json" %*
'''
QUICK_START = '''# KataGo Explainer {version}

## 中文

1. 将整个 ZIP 解压到普通可写目录，然后双击 `START_KATAGO_EXPLAINER.cmd`。
   请保留 `KaTrain` 文件夹的完整内容；无需安装 Python。
2. 首次启动会运行 KataGo 的 OpenCL 初始化，可能需要等待几分钟。
   需要支持 OpenCL 的显卡及驱动；不能保证每台 Windows 电脑都兼容。
3. 在 KaTrain 设置中选择语言；主界面讲解按钮跟随应用语言。
4. 打开 `examples` 中的 SGF，进入分析模式，定位一手棋后点击
   “解释刚才一手”或“解释 AI 一选”（不同语言下文字有所区别）。
5. 在讲解窗口查看依据、后续变化及胜率；点击变化步骤切换棋盘。
   讲解语言可在窗口内切换。胜率统一从标注的棋手视角读取。

定式样例：`kick-demo.sgf` 尖顶（第 3 手）、`shusaku-demo.sgf` 秀策尖（第 3 手）、
`attach-retreat-demo.sgf` 托退（第 5 手）、`mi-flying-dagger-demo.sgf` 芈氏飞刀外扳入口（第 17 手）。
定式名称是局部形状关联；讲解不是 KataGo 内部推理的直接读取。

## English

1. Extract the entire ZIP into a writable folder. Double-click
   `START_KATAGO_EXPLAINER.cmd`. Keep the complete `KaTrain` folder. Python is not required.
2. The first start may take several minutes for KataGo's OpenCL initialization.
   A compatible GPU and OpenCL driver are required; Windows hardware compatibility varies.
3. Select the application language in KaTrain settings. The explanation buttons follow it.
4. Open an SGF in `examples`, enter analysis mode, select a move, and use
   “Explain last move” or “Explain AI choice”. The dialog has its own language selector.
5. Read the evidence and win rate, then click continuation steps to replay them.
   Win rates share the named player's perspective.

Classic examples: kick (move 3), Shusaku kosumi (move 3), attach-and-retreat (move 5),
and Mi's Flying Dagger outside-hane entry (move 17). References describe local shapes;
explanations do not expose the neural network's internal reasoning.

## Included / 包含

KaTrain 1.20.0, its bundled KataGo engine and model, the installed explanation plugin,
seven sample SGFs, third-party notices, and a file-hash provenance manifest.
The launcher uses `portable-config.json` for preferences, so it does not load an
older KaTrain configuration from the current user's home folder. The host and
GPU driver may still create caches or logs in the Windows user profile.

项目 / Project: https://github.com/k4ju1/katago-explainer
许可证与来源 / Licenses and provenance: `licenses`, `build-manifest.json`.
'''


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _pe64(path):
    """Check the Windows executable architecture without executing it."""
    with path.open('rb') as stream:
        header = stream.read(64)
        if len(header) < 64 or header[:2] != b'MZ':
            raise ValueError(f'Invalid Windows executable: {path.name}')
        stream.seek(struct.unpack_from('<I', header, 60)[0])
        if stream.read(6) != b'PE\0\0\x64\x86':
            raise ValueError(f'Expected a Windows x64 executable: {path.name}')


def verify_source(source, archive, expected_sha256=SOURCE_SHA256):
    """Reject partial, modified, unsafe or personally configured distributions."""
    if not re.fullmatch(r'[0-9a-fA-F]{64}', expected_sha256):
        raise ValueError('Expected source SHA256 must contain 64 hexadecimal characters')
    archive_hash = sha256(archive)
    if archive_hash != expected_sha256.lower():
        raise ValueError('Source archive SHA256 does not match the pinned upstream release')
    if not source.is_dir():
        raise ValueError('Select the clean folder containing KaTrain.exe')
    actual = {}
    for path in source.rglob('*'):
        if path.is_symlink():
            raise ValueError('Source must not contain symbolic links')
        if path.is_file():
            actual[path.relative_to(source).as_posix()] = path
    with zipfile.ZipFile(archive) as upstream:
        expected = {}
        for entry in upstream.infolist():
            relative = PurePosixPath(entry.filename)
            if ('\\' in entry.filename or relative.is_absolute() or '..' in relative.parts
                    or len(relative.parts) < 2 or relative.parts[0] != 'KaTrain'):
                if entry.filename == 'KaTrain/' and entry.is_dir():
                    continue
                raise ValueError('Source archive contains an unsafe or unexpected path')
            if entry.is_dir():
                continue
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Source archive must not contain symbolic links')
            name = PurePosixPath(*relative.parts[1:]).as_posix()
            if name in expected:
                raise ValueError('Source archive contains duplicate filenames')
            expected[name] = entry
        if actual.keys() != expected.keys():
            raise ValueError('Clean source must match the archive exactly; remove extra settings, logs or plugins')
        if any(name not in expected for name in REQUIRED):
            raise ValueError('Source archive is missing required host, engine or model files')
        for name, entry in expected.items():
            with upstream.open(entry) as stream:
                expected_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
            if sha256(actual[name]) != expected_hash:
                raise ValueError(f'Source was modified: {name}')
    if sha256(source / '_internal/katrain/gui.kv') != installer.ORIGINAL_GUI_SHA256:
        raise ValueError('Only the unmodified KaTrain 1.20.0 interface is supported')
    configuration = json.loads((source / '_internal/katrain/config.json').read_text(encoding='utf-8'))
    if configuration.get('general', {}).get('version') != '1.20.0':
        raise ValueError('Only KaTrain 1.20.0 is supported')
    if any(configuration.get('contribute', {}).get(key) for key in ('username', 'password')):
        raise ValueError('Source configuration must not contain contribution credentials')
    for name in ('KaTrain.exe', ENGINE):
        _pe64(source / name)
    with (source / MODEL).open('rb') as stream:
        if stream.read(2) != b'\x1f\x8b':
            raise ValueError('Bundled KataGo model is not a gzip file')
    return archive_hash


def _write_zip(root, target):
    """Stable ordering, permissions and timestamps make repeated builds identical."""
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(root.rglob('*')):
            if not path.is_file():
                continue
            info = zipfile.ZipInfo(path.relative_to(root.parent).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            with path.open('rb') as source, archive.open(info, 'w', force_zip64=True) as destination:
                shutil.copyfileobj(source, destination)


def build_portable(katrain_dir, source_archive, version, output_dir, *,
                   licenses_dir=None, source_sha256=SOURCE_SHA256, source_url=SOURCE_URL,
                   commit='unknown', project_dir=PROJECT_DIR):
    """Return the finished ZIP and checksum; never patch or delete source files."""
    numeric = r'(?:0|[1-9][0-9]*)'
    valid_version = re.fullmatch(rf'{numeric}\.{numeric}\.{numeric}(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?', version)
    prerelease = version.partition('-')[2].split('.') if '-' in version else []
    if not valid_version or any(part.isdigit() and len(part) > 1 and part.startswith('0') for part in prerelease):
        raise ValueError('Version must be SemVer, for example 0.2.0-beta.1')
    source = Path(katrain_dir).resolve()
    archive = Path(source_archive).resolve()
    project = Path(project_dir).resolve()
    output = Path(output_dir).resolve()
    if output == source or source in output.parents:
        raise ValueError('Output must not be inside the clean source folder')
    archive_hash = verify_source(source, archive, source_sha256)
    licenses = Path(licenses_dir or project / 'docs' / 'distribution-licenses').resolve()
    for name in ('KaTrain-LICENSE.txt', 'KataGo-LICENSE.txt', 'KataGo-Network-LICENSE.txt'):
        if not (licenses / name).is_file():
            raise ValueError(f'Missing required redistribution notice: {name}')
    if not (project / 'THIRD_PARTY_NOTICES.md').is_file():
        raise ValueError('Missing project third-party notices')
    samples = sorted((project / 'examples').glob('*.sgf'))
    if not samples:
        raise ValueError('Project contains no SGF examples')
    name = f'KataGo-Explainer-v{version}-win64'
    output.mkdir(parents=True, exist_ok=True)
    target = output / f'{name}.zip'
    checksum = target.with_suffix('.zip.sha256')
    if target.exists() or checksum.exists():
        raise ValueError('Output artifact already exists; choose a new output directory or version')
    with TemporaryDirectory(prefix='.portable-build-', dir=output) as temporary:
        root = Path(temporary) / name
        host = root / 'KaTrain'
        shutil.copytree(source, host)
        installer.install(host, project_dir=project)
        # The installer records a staging absolute path for local uninstall;
        # releases store a relative path and never disclose builder machine paths.
        install_manifest = host / '_internal/katrain-explainer-install.json'
        installed = json.loads(install_manifest.read_text(encoding='utf-8'))
        installed['package'] = '_internal/katrain_explainer'
        install_manifest.write_text(json.dumps(installed, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (root / 'START_KATAGO_EXPLAINER.cmd').write_bytes(LAUNCHER.replace('\n', '\r\n').encode('ascii'))
        configuration = json.loads((source / '_internal/katrain/config.json').read_text(encoding='utf-8'))
        # Empty engine overrides use the bundled executable; model/config paths
        # resolve as KaTrain package resources, independent of a user's home config.
        configuration['engine'].update(backend='', katago='', altcommand='', remote_url='',
                                       model='katrain/models/b10c384h6nbttflrs.bin.gz',
                                       config='katrain/KataGo/analysis_config.cfg')
        configuration['contribute'].update(username='', password='')
        (root / 'portable-config.json').write_text(json.dumps(configuration, ensure_ascii=False, indent=2) + '\n',
                                                  encoding='utf-8', newline='\n')
        (root / 'QUICK_START.md').write_text(QUICK_START.format(version=version), encoding='utf-8', newline='\n')
        example_dir = root / 'examples'
        example_dir.mkdir()
        for sample in samples:
            shutil.copyfile(sample, example_dir / sample.name)
        shutil.copytree(licenses, root / 'licenses')
        shutil.copyfile(project / 'THIRD_PARTY_NOTICES.md', root / 'licenses/THIRD_PARTY_NOTICES.md')
        file_hashes = {path.relative_to(root).as_posix(): sha256(path)
                       for path in sorted(root.rglob('*')) if path.is_file()}
        manifest = {'schema_version': 1, 'product': 'KataGo Explainer', 'version': version,
                    'platform': 'windows-x64', 'source_commit': commit,
                    'upstream': {'host': 'KaTrain 1.20.0', 'archive_url': source_url,
                                 'archive_sha256': archive_hash,
                                 'engine_sha256': file_hashes[f'KaTrain/{ENGINE}'],
                                 'model_sha256': file_hashes[f'KaTrain/{MODEL}']},
                    'files_sha256': file_hashes}
        (root / 'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
                                                 encoding='utf-8', newline='\n')
        temporary_zip = Path(temporary) / target.name
        _write_zip(root, temporary_zip)
        artifact_hash = sha256(temporary_zip)
        temporary_checksum = Path(temporary) / checksum.name
        temporary_checksum.write_text(f'{artifact_hash}  {target.name}\n', encoding='ascii', newline='\n')
        temporary_zip.replace(target)
        try:
            temporary_checksum.replace(checksum)
        except OSError:
            target.unlink()  # Only this build's exact artifact; never a recursive delete.
            raise
    return {'archive': str(target), 'sha256_file': str(checksum), 'sha256': artifact_hash}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--katrain-dir', type=Path, required=True)
    parser.add_argument('--source-archive', type=Path, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output-dir', type=Path, default=PROJECT_DIR / 'dist')
    parser.add_argument('--licenses-dir', type=Path, default=PROJECT_DIR / 'docs/distribution-licenses')
    parser.add_argument('--source-sha256', default=SOURCE_SHA256)
    parser.add_argument('--source-url', default=SOURCE_URL)
    parser.add_argument('--commit', default='unknown')
    args = parser.parse_args()
    try:
        result = build_portable(args.katrain_dir, args.source_archive, args.version, args.output_dir,
                                licenses_dir=args.licenses_dir, source_sha256=args.source_sha256,
                                source_url=args.source_url, commit=args.commit)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(1, f'Portable build failed / 便携版打包失败: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
