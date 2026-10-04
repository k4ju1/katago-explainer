"""Launch the original KaTrain executable with the native explanation extension.
启动原始 KaTrain 程序与原生讲解扩展。
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from install_katrain_plugin import PROJECT_DIR, install


BACKEND_URL = 'http://127.0.0.1:8788'


def backend_ready():
    try:
        with urlopen(BACKEND_URL + '/api/state', timeout=2) as response:
            state = json.load(response)
        if state.get('application') != 'katago-explainer' or state.get('api_version') != 1:
            raise RuntimeError('8788 端口已有其他服务 / Port 8788 is used by a different service')
        return True
    except URLError:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--katrain-dir', type=Path,
                        default=PROJECT_DIR.parent / 'KaTrain-1.20.0' / 'KaTrain')
    parser.add_argument('--sgf', type=Path, help='启动时打开棋谱 / SGF to open at startup')
    args = parser.parse_args()
    backend = None
    log_file = None
    try:
        installation = install(args.katrain_dir, Path(sys.executable))
        print('原生讲解扩展已安装 / Native explanation extension installed', flush=True)
        if not backend_ready():
            runs = PROJECT_DIR / 'runs'
            runs.mkdir(exist_ok=True)
            log_file = (runs / 'plugin-backend.log').open('a', encoding='utf-8')
            backend = subprocess.Popen([sys.executable, '-m', 'explainer.server', '--port', '8788'],
                                       cwd=str(PROJECT_DIR), stdin=subprocess.DEVNULL,
                                       stdout=log_file, stderr=log_file,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            deadline = time.monotonic() + 12
            while not backend_ready():
                if backend.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('讲解后台未能启动，请查看 runs/plugin-backend.log / Backend startup failed; check its log')
                time.sleep(.25)
        command = [str(Path(installation['katrain_dir']) / 'KaTrain.exe')]
        if args.sgf:
            command.append(str(args.sgf.resolve(strict=True)))
        print('正在打开 KaTrain；讲解按钮在右侧。 / Opening KaTrain; explanation buttons are on the right.', flush=True)
        native = subprocess.Popen(command, cwd=installation['katrain_dir'])
        return native.wait()
    except (OSError, ValueError, RuntimeError) as error:
        print(f'无法启动 / Could not launch: {error}', file=sys.stderr)
        return 1
    finally:
        if backend is not None and backend.poll() is None:
            try:
                request = Request(BACKEND_URL + '/api/shutdown', data=b'{}',
                                  headers={'Content-Type': 'application/json'}, method='POST')
                with urlopen(request, timeout=3):
                    pass
                backend.wait(timeout=8)
            except (OSError, subprocess.TimeoutExpired):
                backend.terminate()
                try:
                    backend.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    backend.kill()
                    backend.wait(timeout=3)
        if log_file:
            log_file.close()


if __name__ == '__main__':
    raise SystemExit(main())
