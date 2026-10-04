"""Install or update the explanation plugin, then open the original KaTrain.
安装或更新着法讲解插件，然后打开原始 KaTrain 程序。

The plugin runs inside KaTrain and uses KaTrain's own KataGo engine, so no
background service is started. After one install KaTrain can also be opened
directly; run this launcher again to pick up plugin updates.
"""

import argparse
from pathlib import Path
import subprocess
import sys

from install_katrain_plugin import PROJECT_DIR, install


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--katrain-dir', type=Path,
                        default=PROJECT_DIR.parent / 'KaTrain-1.20.0' / 'KaTrain')
    parser.add_argument('--sgf', type=Path, help='启动时打开棋谱 / SGF to open at startup')
    args = parser.parse_args()
    try:
        installation = install(args.katrain_dir)
        print('着法讲解插件已安装 / Move explanation plugin installed', flush=True)
        command = [str(Path(installation['katrain_dir']) / 'KaTrain.exe')]
        if args.sgf:
            command.append(str(args.sgf.resolve(strict=True)))
        print('正在打开 KaTrain；讲解按钮在右侧。 / Opening KaTrain; explanation buttons are on the right.', flush=True)
        return subprocess.Popen(command, cwd=installation['katrain_dir']).wait()
    except (OSError, ValueError, RuntimeError) as error:
        print(f'无法启动 / Could not launch: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
