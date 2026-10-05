"""Run the actual explanation pipeline, retaining protocol logs for review.

Example: python scripts/validate_demo.py examples/mi-flying-dagger-demo.sgf --move 17 --repeat 2
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from explainer.engine import EnginePool, discover_settings  # noqa: E402
from explainer.service import explain_move  # noqa: E402
from explainer.sgf import parse_sgf  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sgf', type=Path, help='SGF 棋谱 / SGF file')
    parser.add_argument('--move', type=int, required=True, help='从 1 开始的手数 / One-based move number')
    parser.add_argument('--choice', choices=('actual', 'ai'), default='actual')
    parser.add_argument('--repeat', type=int, choices=range(1, 11), default=1)
    parser.add_argument('--output-dir', type=Path,
                        default=PROJECT_DIR / 'runs' / ('validation-' + datetime.now().strftime('%Y%m%d-%H%M%S')))
    for name in ('engine', 'model', 'config', 'tuner'):
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args()
    pool = None
    try:
        game = parse_sgf(args.sgf.read_text(encoding='utf-8'))
        if not 1 <= args.move <= len(game.moves) + (args.choice == 'ai'):
            raise ValueError('手数超出棋谱 / Move number outside the game')
        settings = discover_settings(PROJECT_DIR, {name: getattr(args, name)
                                                  for name in ('engine', 'model', 'config', 'tuner')})
        settings.validate()
        pool = EnginePool(settings)
        records = []
        for number in range(1, args.repeat + 1):
            result = explain_move(game, 'validation', args.move - 1, args.choice, settings,
                                  args.output_dir / f'run-{number}', lambda *_: None, pool=pool)
            records.append({
                'run': number, 'elapsed_seconds': result['elapsed_seconds'],
                'selected_move': result['selected_move'], 'ai_move': result['ai_move'],
                'winrate': result['selected']['winrate'], 'score_lead': result['selected']['score_lead'],
                'verdict': result['explanation']['verdict'],
                'joseki': [entry['id'] for entry in result['explanation']['joseki']],
                'variation_plies': [len(branch['steps']) - 1 for branch in result['branches']],
                'engine': result['engine'], 'budgets': result['budgets'],
                'kept_alive': result['cleanup'].get('kept_alive', False),
            })
            print(f"Run {number}: {result['selected_move']} · {result['elapsed_seconds']:.3f}s", flush=True)
        pool.close()
        cleanup = result['cleanup']
        if not cleanup.get('process_stopped') or not cleanup.get('reader_threads_stopped'):
            raise RuntimeError('引擎清理未完成 / Engine cleanup did not complete')
        report = {'sample': args.sgf.name, 'move': args.move, 'choice': args.choice,
                  'runs': records, 'cleanup': cleanup}
        args.output_dir.mkdir(parents=True, exist_ok=True)
        summary = args.output_dir / 'summary.json'
        summary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Report / 报告: {summary}')
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f'验证失败 / Validation failed: {error}\n')
    finally:
        if pool is not None:
            pool.close()


if __name__ == '__main__':
    main()
