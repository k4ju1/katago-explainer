"""Compile a Windows installer from a fully verified portable release ZIP.

Inno Setup supplies the GUI wizard, native shortcuts and per-user uninstall.
No application executable or user installation is run during this build.
"""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import zipfile


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_portable as portable  # noqa: E402

VERSION_PATTERN = r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?'
REQUIRED = ('KaTrain/KaTrain.exe', 'KaTrain/_internal/katrain_explainer/panel.py',
            'KaTrain/' + portable.ENGINE, 'KaTrain/' + portable.MODEL,
            'portable-config.json', 'QUICK_START.md', 'licenses/KaTrain-LICENSE.txt',
            'licenses/KataGo-LICENSE.txt', 'licenses/KataGo-Network-LICENSE.txt')


def _validate_version(version):
    parts = version.partition('-')[2].split('.') if '-' in version else []
    if (not re.fullmatch(VERSION_PATTERN, version)
            or any(part.isdigit() and len(part) > 1 and part.startswith('0') for part in parts)):
        raise ValueError('Version must be SemVer, for example 0.2.0-beta.2')


def extract_verified_release(archive_path, destination, version):
    """Validate every path and recorded hash before extracting any file."""
    _validate_version(version)
    root_name = f'KataGo-Explainer-v{version}-win64'
    destination = Path(destination).resolve()
    with zipfile.ZipFile(archive_path) as archive:
        entries = {}
        folded_names = set()
        for entry in archive.infolist():
            path = PurePosixPath(entry.filename)
            if ('\\' in entry.orig_filename or path.is_absolute() or '..' in path.parts
                    or not path.parts or path.parts[0] != root_name
                    or any(':' in part or part.endswith(('.', ' '))
                           or any(ord(character) < 32 for character in part)
                           or part.split('.')[0].upper() in {
                               'CON', 'PRN', 'AUX', 'NUL',
                               *(f'COM{number}' for number in range(1, 10)),
                               *(f'LPT{number}' for number in range(1, 10))}
                           for part in path.parts)):
                raise ValueError('Portable ZIP contains an unsafe or unexpected path')
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Portable ZIP must not contain symbolic links')
            if entry.is_dir():
                continue
            if len(path.parts) < 2:
                raise ValueError('Portable ZIP has an invalid root layout')
            relative = PurePosixPath(*path.parts[1:]).as_posix()
            if relative.casefold() in folded_names:
                raise ValueError('Portable ZIP contains duplicate or case-colliding filenames')
            folded_names.add(relative.casefold())
            entries[relative] = entry
        if 'build-manifest.json' not in entries or any(name not in entries for name in REQUIRED):
            raise ValueError('Portable ZIP is missing the manifest or required application files')
        manifest = json.loads(archive.read(entries['build-manifest.json']))
        if (manifest.get('schema_version') != 1 or manifest.get('product') != 'KataGo Explainer'
                or manifest.get('version') != version or manifest.get('platform') != 'windows-x64'):
            raise ValueError('Portable manifest version or platform does not match this installer')
        recorded = manifest.get('files_sha256')
        if not isinstance(recorded, dict) or set(recorded) != set(entries) - {'build-manifest.json'}:
            raise ValueError('Portable manifest must cover every payload file exactly')
        for name, expected_hash in recorded.items():
            if not isinstance(expected_hash, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_hash):
                raise ValueError(f'Invalid file SHA256: {name}')
            with archive.open(entries[name]) as stream:
                actual_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual_hash != expected_hash:
                raise ValueError(f'Portable file SHA256 mismatch: {name}')
        if destination.exists() and any(destination.iterdir()):
            raise ValueError('Extraction destination must be empty')
        destination.mkdir(parents=True, exist_ok=True)
        for relative, entry in entries.items():
            path = destination / relative
            # Validate the resolved path as well, in case the destination has
            # unexpectedly acquired a symlink while validation was in progress.
            if destination not in path.resolve().parents:
                raise ValueError('Extraction path escaped its staging directory')
            path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, path.open('xb') as target:
                shutil.copyfileobj(source, target)
    for executable in ('KaTrain/KaTrain.exe', 'KaTrain/' + portable.ENGINE):
        portable._pe64(destination / executable)
    with (destination / ('KaTrain/' + portable.MODEL)).open('rb') as stream:
        if stream.read(2) != b'\x1f\x8b':
            raise ValueError('Portable model is not a gzip file')
    configuration = json.loads((destination / 'portable-config.json').read_text(encoding='utf-8'))
    engine = configuration.get('engine', {})
    if (any(engine.get(key) for key in ('backend', 'katago', 'altcommand', 'remote_url'))
            or engine.get('model') != 'katrain/models/b10c384h6nbttflrs.bin.gz'
            or engine.get('config') != 'katrain/KataGo/analysis_config.cfg'):
        raise ValueError('Portable configuration must use the included engine and model')
    if any(configuration.get('contribute', {}).get(key) for key in ('username', 'password')):
        raise ValueError('Portable configuration must not contain contribution credentials')
    return manifest


def build_installer(portable_zip, version, output_dir, iscc, *, chinese_isl=None, project_dir=PROJECT_DIR):
    _validate_version(version)
    project = Path(project_dir).resolve()
    compiler = Path(iscc).resolve()
    archive = Path(portable_zip).resolve()
    output = Path(output_dir).resolve()
    script = project / 'packaging/windows/setup.iss'
    if not compiler.is_file():
        raise ValueError('Inno Setup compiler not found; pass --iscc pointing to ISCC.exe')
    if not script.is_file():
        raise ValueError('Missing packaging/windows/setup.iss')
    candidates = ([Path(chinese_isl).resolve()] if chinese_isl else
                  [compiler.parent / 'Languages/ChineseSimplified.isl',
                   project / 'packaging/windows/ChineseSimplified.isl'])
    language = next((candidate for candidate in candidates if candidate.is_file()), None)
    if language is None:
        raise ValueError('Chinese Simplified wizard language not found; pass --chinese-isl')
    output.mkdir(parents=True, exist_ok=True)
    basename = f'KataGo-Explainer-Setup-v{version}-win64.exe'
    target = output / basename
    checksum = target.with_suffix('.exe.sha256')
    metadata_path = target.with_suffix('.exe.build.json')
    if any(path.exists() for path in (target, checksum, metadata_path)):
        raise ValueError('Output artifact already exists; choose a new output directory or version')
    with TemporaryDirectory(prefix='.installer-build-', dir=output) as temporary:
        staging = Path(temporary)
        payload = staging / 'payload'
        manifest = extract_verified_release(archive, payload, version)
        configuration = json.loads((payload / 'portable-config.json').read_text(encoding='utf-8'))
        configuration.setdefault('general', {}).update(lang='en', load_sgf_rewind=False)
        english_config = staging / 'english-config.json'
        english_config.write_text(json.dumps(configuration, ensure_ascii=False, indent=2) + '\n',
                                  encoding='utf-8', newline='\n')
        configuration['general']['lang'] = 'cn'
        chinese_config = staging / 'chinese-config.json'
        chinese_config.write_text(json.dumps(configuration, ensure_ascii=False, indent=2) + '\n',
                                  encoding='utf-8', newline='\n')
        definitions = {'PayloadDir': str(payload), 'AppVersion': version,
                       'AppNumericVersion': version.partition('-')[0] + '.0',
                       'OutputDirPath': str(staging), 'ChineseLanguageFile': str(language),
                       'ChineseConfigFile': str(chinese_config), 'EnglishConfigFile': str(english_config)}
        arguments = [str(compiler), '/Qp', *(f'/D{name}={value}' for name, value in definitions.items()), str(script)]
        compiled = subprocess.run(arguments, capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
        if compiled.returncode:
            detail = (compiled.stderr or compiled.stdout).strip()[-6000:]
            raise ValueError(f'Inno Setup compilation failed ({compiled.returncode}): {detail}')
        built = staging / basename
        if not built.is_file() or built.stat().st_size < 64:
            raise ValueError('Compiler did not produce the expected installer executable')
        # Setup itself can be 32-bit while it installs an x64 application. Check
        # its executable signature, not the host-specific x64 PE machine value.
        with built.open('rb') as stream:
            header = stream.read(64)
            if len(header) < 64 or header[:2] != b'MZ':
                raise ValueError('Compiler output is not a Windows installer executable')
            stream.seek(struct.unpack_from('<I', header, 60)[0])
            signature = stream.read(6)
            if signature[:4] != b'PE\0\0' or signature[4:] not in (b'\x4c\x01', b'\x64\x86'):
                raise ValueError('Compiler output has an invalid Windows PE signature')
        artifact_hash = portable.sha256(built)
        metadata = {'schema_version': 1, 'product': 'KataGo Explainer', 'version': version,
                    'format': 'windows-inno-setup', 'installation_scope': 'current-user',
                    'portable_archive_sha256': portable.sha256(archive),
                    'source_commit': manifest.get('source_commit', 'unknown'),
                    'installer_sha256': artifact_hash,
                    'setup_script_sha256': portable.sha256(script),
                    'compiler_sha256': portable.sha256(compiler),
                    'chinese_language_sha256': portable.sha256(language),
                    'initial_configurations_sha256': {
                        'english': portable.sha256(english_config),
                        'chinesesimplified': portable.sha256(chinese_config)}}
        staged_checksum = staging / checksum.name
        staged_checksum.write_text(f'{artifact_hash}  {basename}\n', encoding='ascii', newline='\n')
        staged_metadata = staging / metadata_path.name
        staged_metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        emitted = []
        try:
            for source, destination in ((built, target), (staged_checksum, checksum), (staged_metadata, metadata_path)):
                source.replace(destination)
                emitted.append(destination)
        except OSError:
            for path in emitted:
                path.unlink()  # Only files this invocation just created.
            raise
    return {'installer': str(target), 'sha256_file': str(checksum),
            'build_manifest': str(metadata_path), 'sha256': artifact_hash}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--portable-zip', type=Path, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output-dir', type=Path, default=PROJECT_DIR / 'dist')
    parser.add_argument('--iscc', type=Path, required=True)
    parser.add_argument('--chinese-isl', type=Path)
    args = parser.parse_args()
    try:
        result = build_installer(args.portable_zip, args.version, args.output_dir, args.iscc,
                                 chinese_isl=args.chinese_isl)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(1, f'Installer build failed / 安装包打包失败: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
