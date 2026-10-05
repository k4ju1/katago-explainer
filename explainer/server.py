"""Local bilingual Go explanation application. Run: python -m explainer.server."""

import argparse
from collections import OrderedDict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import shutil
import threading
from urllib.parse import urlsplit
import uuid
import webbrowser

from .board import Board
from .engine import EnginePool, discover_settings, stop_active_engines
from .service import (CANDIDATE_VISITS, PHASES, PV_PLIES, ROOT_VISITS, TENUKI_VISITS, TRACE_VISITS,
                      explain_move, text)
from .sgf import parse_sgf


PROJECT_DIR = Path(__file__).resolve().parents[1]
WEB_FILES = {
    '/': ('index.html', 'text/html'),
    '/index.html': ('index.html', 'text/html'),
    '/styles.css': ('styles.css', 'text/css'),
    '/app.js': ('app.js', 'text/javascript'),
}
JOSEKI_EXAMPLES = {
    'basic': ('joseki-demo.sgf', 4),
    'kick': ('kick-demo.sgf', 2),
    'mi': ('mi-flying-dagger-demo.sgf', 16),
    'attach-retreat': ('attach-retreat-demo.sgf', 4),
    'shusaku': ('shusaku-demo.sgf', 2),
}


RUN_DIRECTORY = re.compile(r'\d{8}-\d{6}-[0-9a-f]{8}')
KEPT_RUNS = 30


def prune_runs(runs_dir, keep=KEPT_RUNS):
    """Delete the oldest per-explanation run folders beyond `keep`.

    Only folders this server names itself (timestamp plus job id) are touched;
    research notes, screenshots and logs kept beside them are left alone.
    """
    runs_dir = Path(runs_dir)
    if not runs_dir.is_dir():
        return []
    folders = sorted(path for path in runs_dir.iterdir()
                     if path.is_dir() and RUN_DIRECTORY.fullmatch(path.name))
    removed = []
    for folder in folders[:max(0, len(folders) - keep)]:
        try:
            shutil.rmtree(folder)
            removed.append(folder.name)
        except OSError:
            pass  # e.g. still the working directory of the warm engine
    return removed


def public_game(game, game_id):
    board = Board(game.board_size, game.initial_stones, game.initial_player, game.rules)
    positions = [board.snapshot()]
    for player, move in game.moves:
        board.play(player, move)
        positions.append(board.snapshot())
    return {'id': game_id, 'name': game.metadata.get('GN') or 'SGF',
            **game.to_dict(), 'positions': positions}


class Application:
    def __init__(self, settings):
        self.settings = settings
        self.games = OrderedDict()
        self.jobs = OrderedDict()
        self.lock = threading.RLock()
        self.active = False
        self.pool = EnginePool(settings)
        self.default_game = self.add_game((PROJECT_DIR / 'examples' / 'demo.sgf').read_text(encoding='utf-8'))

    def add_game(self, sgf):
        record = parse_sgf(sgf)
        if len(record.moves) > 1000:
            raise ValueError('最多导入 1000 手棋谱 / Maximum 1000 moves per game')
        game_id = uuid.uuid4().hex
        public = public_game(record, game_id)
        with self.lock:
            self.games[game_id] = (record, public)
            while len(self.games) > 12:
                oldest = next(key for key in self.games if key != self.default_game['id'])
                self.games.pop(oldest)
        return public

    def state(self, game=None, uploaded=False):
        game = game or self.default_game
        return {'application': 'katago-explainer', 'api_version': 1,
                'game': game, 'defaults': {'choice': 'actual' if uploaded and game['moves'] else 'ai',
                'move_index': 0 if uploaded else min(8, len(game['moves'])),
                'root_visits': ROOT_VISITS, 'candidate_visits': CANDIDATE_VISITS,
                'trace_visits': TRACE_VISITS, 'tenuki_visits': TENUKI_VISITS, 'pv_plies': PV_PLIES}}

    def start_job(self, payload):
        game_id = payload.get('game_id')
        move_index = payload.get('move_index')
        choice = payload.get('choice', 'ai')
        custom_move = payload.get('move')
        if not isinstance(game_id, str) or not game_id:
            raise ValueError('棋谱标识必须是字符串 / Game ID must be a non-empty string')
        if type(move_index) is not int:
            raise ValueError('手数必须是整数 / Move index must be an integer')
        if choice not in ('actual', 'ai'):
            raise ValueError('请选择实战手或 AI 推荐 / Choose the recorded or AI move')
        if custom_move is not None and (not isinstance(custom_move, str) or len(custom_move) > 6):
            raise ValueError('自选坐标无效 / Invalid custom move')
        with self.lock:
            if game_id not in self.games:
                raise ValueError('棋谱已过期，请重新导入 / Game expired; import it again')
            if self.active:
                raise RuntimeError('已有分析正在进行，请等待 / An analysis is already running; please wait')
            record = self.games[game_id][0]
            if not 0 <= move_index <= len(record.moves):
                raise ValueError('手数超出棋谱 / Move index outside the game')
            self.settings.validate()
            if choice == 'actual' and not custom_move and move_index == len(record.moves):
                raise ValueError('这里没有实战手，请选择 AI 推荐 / No recorded move here; choose AI')
            job_id = uuid.uuid4().hex
            job = {'id': job_id, 'status': 'queued',
                   'progress': {'message': text('准备分析…', 'Preparing the analysis…'), 'completed': 0, 'total': PHASES}}
            self.jobs[job_id] = job
            while len(self.jobs) > 20:
                self.jobs.popitem(last=False)
            self.active = True

        def worker():
            run_dir = PROJECT_DIR / 'runs' / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + job_id[:8])

            def progress(message, completed, total):
                with self.lock:
                    job['progress'] = {'message': message, 'completed': completed, 'total': total}

            try:
                with self.lock:
                    job['status'] = 'running'
                result = explain_move(record, game_id, move_index, choice, self.settings, run_dir, progress,
                                      custom_move, pool=self.pool)
                with self.lock:
                    job['result'] = result
                    job['status'] = 'complete'
            except Exception as error:
                with self.lock:
                    job['status'] = 'error'
                    job['error'] = text(f'讲解生成失败：{error}', f'Explanation failed: {error}')
                run_dir.mkdir(parents=True, exist_ok=True)
                (run_dir / 'error.json').write_text(json.dumps(job['error'], ensure_ascii=False, indent=2), encoding='utf-8')
            finally:
                with self.lock:
                    self.active = False
                prune_runs(PROJECT_DIR / 'runs')

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()
        return job_id

    def job(self, job_id):
        with self.lock:
            if job_id not in self.jobs:
                return None
            # Serialize while locked so the HTTP worker cannot race dictionary changes.
            return json.loads(json.dumps(self.jobs[job_id], ensure_ascii=False))


def handler_for(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_bytes(self, encoded, content_type, status=200):
            self.send_response(status)
            self.send_header('Content-Type', content_type + '; charset=utf-8')
            self.send_header('Content-Length', str(len(encoded)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(encoded)

        def json_response(self, payload, status=200):
            encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_bytes(encoded, 'application/json', status)

        def permitted(self):
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            host = self.headers.get('Host', '')
            origin = self.headers.get('Origin')
            return host in allowed and (not origin or origin in {'http://' + name for name in allowed})

        def do_GET(self):
            if not self.permitted():
                self.json_response({'error': text('只允许本机访问', 'Local access only')}, 403)
                return
            path = urlsplit(self.path).path
            if path == '/api/state':
                self.json_response(app.state())
            elif path.startswith('/api/jobs/'):
                job = app.job(path.rsplit('/', 1)[-1])
                self.json_response(job if job else {'error': text('未找到分析', 'Analysis not found')}, 200 if job else 404)
            elif path == '/api/examples/capture':
                self.json_response({'sgf': (PROJECT_DIR / 'examples' / 'capture-demo.sgf').read_text(encoding='utf-8')})
            elif path == '/api/example/joseki' or path.startswith('/api/example/joseki/'):
                key = path.rsplit('/', 1)[-1] if path.startswith('/api/example/joseki/') else 'basic'
                if key not in JOSEKI_EXAMPLES:
                    self.json_response({'error': text('没有这个经典棋形示例', 'Classic pattern example not found')}, 404)
                    return
                filename, move_index = JOSEKI_EXAMPLES[key]
                self.json_response({'sgf': (PROJECT_DIR / 'examples' / filename).read_text(encoding='utf-8'),
                                    'move_index': move_index})
            elif path in WEB_FILES:
                filename, content_type = WEB_FILES[path]
                self.send_bytes((PROJECT_DIR / 'web' / filename).read_bytes(), content_type)
            elif path == '/favicon.ico':
                self.send_response(204)
                self.end_headers()
            else:
                self.json_response({'error': text('页面不存在', 'Page not found')}, 404)

        def do_POST(self):
            if not self.permitted():
                self.json_response({'error': text('只允许本机访问', 'Local access only')}, 403)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 2_100_000:
                    raise ValueError('请求为空或过大 / Empty or oversized request')
                payload = json.loads(self.rfile.read(length).decode('utf-8'))
                if not isinstance(payload, dict):
                    raise ValueError('请求须为对象 / Request must be an object')
                path = urlsplit(self.path).path
                if path == '/api/game':
                    if not isinstance(payload.get('sgf'), str):
                        raise ValueError('请选择 SGF 文件 / Select an SGF file')
                    self.json_response(app.state(app.add_game(payload['sgf']), uploaded=True))
                elif path == '/api/analyze':
                    self.json_response({'job_id': app.start_job(payload)}, 202)
                elif path == '/api/shutdown':
                    self.json_response({'status': 'stopping'})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                else:
                    self.json_response({'error': text('接口不存在', 'Endpoint not found')}, 404)
            except (ValueError, UnicodeError) as error:
                self.json_response({'error': text(str(error), str(error))}, 400)
            except RuntimeError as error:
                self.json_response({'error': text(str(error), str(error))}, 409)

    return Handler


def main():
    parser = argparse.ArgumentParser(description='KataGo 着法讲解 / KataGo move explainer')
    parser.add_argument('--port', type=int, default=8788, help='本机端口 / Local port')
    parser.add_argument('--open-browser', action='store_true', help='打开浏览器 / Open browser')
    for name in ('engine', 'model', 'config', 'tuner'):
        parser.add_argument('--' + name, type=Path,
                            help=f'{name} 文件路径；默认自动查找 / {name} file path; discovered automatically by default')
    args = parser.parse_args()
    settings = discover_settings(PROJECT_DIR, {name: getattr(args, name) for name in ('engine', 'model', 'config', 'tuner')})
    try:
        settings.validate()
        app = Application(settings)
        server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(app))
    except (ValueError, OSError) as error:
        parser.exit(1, f'无法启动 / Could not start: {error}\n')
    print(f'KataGo 讲解页面 / Move explanation page: http://127.0.0.1:{args.port}', flush=True)
    print('关闭此窗口或按 Ctrl+C 停止。 / Close this window or press Ctrl+C to stop.', flush=True)
    if args.open_browser:
        webbrowser.open(f'http://127.0.0.1:{args.port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_active_engines()
        worker = getattr(app, 'worker', None)
        if worker is not None:
            worker.join(timeout=5)
        app.pool.close()
        server.server_close()


if __name__ == '__main__':
    main()
