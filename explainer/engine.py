"""Bounded client for KataGo's JSON analysis protocol.

One explanation runs at a time, but its independent positions are sent as a
batch so KataGo can search them in parallel. `EnginePool` keeps the process
warm between explanations and stops it after a quiet period.
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
import weakref


_ACTIVE_ENGINES = weakref.WeakSet()
_ACTIVE_LOCK = threading.Lock()
DEFAULT_MODEL = 'b10c384h6nbttflrs.bin.gz'
QUERY_SECONDS = 40
EXTRA_SECONDS_PER_QUERY = 5


def stop_active_engines():
    """Stop child processes when the user closes the local server."""
    with _ACTIVE_LOCK:
        clients = list(_ACTIVE_ENGINES)
    for client in clients:
        process = client.process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass


@dataclass(frozen=True)
class EngineSettings:
    engine: Path
    model: Path
    config: Path
    # Optional: without a matching file KataGo uses or creates its own tuning.
    tuner: 'Path | None' = None

    def validate(self):
        for name in ('engine', 'model', 'config', 'tuner'):
            path = getattr(self, name)
            if path is None and name == 'tuner':
                continue
            if path is None or not path.is_file():
                raise ValueError(f'缺少 {name} 文件 / Missing {name} file: {path}')


def _pick_model(directory):
    preferred = directory / DEFAULT_MODEL
    if preferred.is_file():
        return preferred
    models = sorted(path for path in directory.glob('*.bin.gz') if path.is_file())
    return models[0] if models else preferred


def _pick_tuner(directory, model):
    """Newest 19x19 OpenCL tuning file, preferring the model's channel count."""
    try:
        files = [path for path in directory.glob('tune*.txt') if path.is_file() and '_x19_y19_' in path.name]
    except OSError:
        return None
    if not files:
        return None
    channels = re.search(r'c(\d+)', model.name)
    matching = [path for path in files if channels and f'_c{channels.group(1)}_' in path.name]
    return max(matching or files, key=lambda path: path.stat().st_mtime)


def discover_settings(project_dir, overrides=None, environ=None, home=None):
    """Resolve engine files: CLI path, then KATAGO_EXPLAINER_* variable, then discovery.

    Discovery looks for a KaTrain folder beside the project and for an OpenCL
    tuning file in the user's KaTrain data directory, so no machine-specific
    file name is required.
    """
    overrides = overrides or {}
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    workspace = Path(project_dir).parent
    fallback = workspace / 'KaTrain-1.20.0' / 'KaTrain' / '_internal' / 'katrain'
    installs = sorted(workspace.glob('KaTrain*/KaTrain/_internal/katrain'), reverse=True)
    engine_names = ('katago.exe', 'katago')
    bundled = next((path for path in installs
                    if any((path / 'KataGo' / name).is_file() for name in engine_names)), fallback)
    engine = next((bundled / 'KataGo' / name for name in engine_names
                   if (bundled / 'KataGo' / name).is_file()), bundled / 'KataGo' / 'katago.exe')

    def chosen(name, default):
        value = overrides.get(name) or environ.get('KATAGO_EXPLAINER_' + name.upper())
        path = Path(value) if value else default
        return path.resolve() if path is not None else None

    model = chosen('model', _pick_model(bundled / 'models'))
    return EngineSettings(engine=chosen('engine', engine), model=model,
                          config=chosen('config', bundled / 'KataGo' / 'analysis_config.cfg'),
                          tuner=chosen('tuner', _pick_tuner(home / '.katrain' / 'opencltuning', model)))


class AnalysisEngine:
    def __init__(self, settings, output_dir, total_seconds=150):
        self.settings = settings
        self.output_dir = Path(output_dir)
        self.total_seconds = total_seconds
        self.responses = queue.Queue()
        self.logs = []
        self.warnings = []
        self.process = None
        self.threads = []
        self.request_counter = 0
        self.cleanup = {}
        self.version = 'KataGo'
        self.input_file = None
        self.output_file = None
        self._file_lock = threading.Lock()
        self._log_start = 0
        self.attached = False

    def _open_run(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        requests = (self.output_dir / 'requests.jsonl').open('w', encoding='utf-8')
        responses = (self.output_dir / 'responses.jsonl').open('w', encoding='utf-8')
        with self._file_lock:
            self.input_file, self.output_file = requests, responses
        self.deadline = time.monotonic() + self.total_seconds
        self.warnings = []
        self.cleanup = {}
        self._log_start = len(self.logs)
        self.attached = True

    def _close_run_files(self):
        with self._file_lock:
            for name in ('input_file', 'output_file'):
                stream = getattr(self, name, None)
                if stream is not None and not stream.closed:
                    stream.close()

    def _write_run_summary(self):
        if self.output_dir.is_dir():
            (self.output_dir / 'engine.log').write_text('\n'.join(self.logs[self._log_start:]), encoding='utf-8')
            (self.output_dir / 'cleanup.json').write_text(json.dumps(self.cleanup, indent=2), encoding='utf-8')

    def __enter__(self):
        self.settings.validate()
        try:
            self._open_run(self.output_dir)
            metadata = subprocess.run([str(self.settings.engine), 'version'], capture_output=True,
                                      text=True, timeout=5, encoding='utf-8', errors='replace')
            if metadata.returncode:
                raise RuntimeError('无法查询引擎版本 / Engine version query failed')
            self.version = metadata.stdout.splitlines()[0]
            # Several analysis threads let one batch of positions share NN batches.
            override = ('numAnalysisThreads=4,numSearchThreads=4,nnMaxBatchSize=16,'
                        'nnCacheSizePowerOfTwo=18,reportAnalysisWinratesAs=BLACK')
            if self.settings.tuner is not None:
                override += f',openclTunerFile={self.settings.tuner}'
            self.process = subprocess.Popen(
                [str(self.settings.engine), 'analysis', '-config', str(self.settings.config),
                 '-model', str(self.settings.model), '-override-config', override],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='replace', bufsize=1,
                cwd=str(self.output_dir))
            with _ACTIVE_LOCK:
                _ACTIVE_ENGINES.add(self)

            def stdout_reader():
                try:
                    for line in self.process.stdout:
                        with self._file_lock:
                            if self.output_file is not None and not self.output_file.closed:
                                self.output_file.write(line)
                                self.output_file.flush()
                        try:
                            self.responses.put(json.loads(line))
                        except json.JSONDecodeError:
                            self.responses.put({'_parse_error': line[:250]})
                finally:
                    self.responses.put({'_eof': True})

            def stderr_reader():
                for line in self.process.stderr:
                    self.logs.append(line.rstrip())

            self.threads = [threading.Thread(target=stdout_reader, daemon=True),
                            threading.Thread(target=stderr_reader, daemon=True)]
            for thread in self.threads:
                thread.start()
            return self
        except Exception:
            self.close()
            raise

    start = __enter__

    def alive(self):
        return self.process is not None and self.process.poll() is None

    def attach(self, output_dir):
        """Reuse the running process for a new explanation with fresh run files."""
        while True:  # Late answers from an earlier run must not reach this one.
            try:
                self.responses.get_nowait()
            except queue.Empty:
                break
        self._open_run(output_dir)

    def detach(self):
        """Finish one explanation's records while leaving the process running."""
        self.cleanup = {'method': 'kept_alive', 'kept_alive': True, 'process_stopped': False,
                        'reader_threads_stopped': False}
        self._close_run_files()
        self._write_run_summary()
        self.attached = False

    def _payload(self, game, query_id, moves, visits, forced_move=None, actor=None, ownership=True):
        if forced_move and actor not in ('B', 'W'):
            raise ValueError('限制候选时必须指定执棋方 / A forced query requires actor B or W')
        payload = {
            'id': query_id, 'initialStones': game.initial_stones,
            'initialPlayer': game.initial_player, 'moves': moves,
            'rules': game.rules, 'komi': game.komi,
            'boardXSize': game.board_size, 'boardYSize': game.board_size,
            'maxVisits': visits, 'includeOwnership': bool(ownership),
            'includeMovesOwnership': bool(ownership), 'includePVVisits': True, 'analysisPVLen': 8,
        }
        if forced_move:
            payload['allowMoves'] = [{'player': actor, 'moves': [forced_move], 'untilDepth': 1}]
        return payload

    def query(self, game, moves, visits, forced_move=None, actor=None):
        return self.query_many(game, [{'moves': moves, 'visits': visits,
                                       'forced_move': forced_move, 'actor': actor}])[0]

    def query_many(self, game, requests):
        """Send independent positions together and return their final answers in order.

        Each request is a dict with `moves`, `visits` and optional `forced_move`,
        `actor`, `ownership`. Partial and unrelated responses are ignored.
        """
        if not requests:
            return []
        encoded, ids = [], []
        for request in requests:
            self.request_counter += 1
            query_id = f'position-{self.request_counter}'
            payload = self._payload(game, query_id, request['moves'], request['visits'],
                                    request.get('forced_move'), request.get('actor'),
                                    request.get('ownership', True))
            ids.append(query_id)
            encoded.append(json.dumps(payload, ensure_ascii=False, separators=(',', ':')))
        block = ''.join(line + '\n' for line in encoded)
        self.input_file.write(block)
        self.input_file.flush()
        if self.process.poll() is not None:
            raise RuntimeError('KataGo 已退出 / KataGo exited before the query')
        allowance = QUERY_SECONDS + EXTRA_SECONDS_PER_QUERY * (len(requests) - 1)
        deadline = min(time.monotonic() + allowance, self.deadline)
        if deadline - time.monotonic() <= 0:
            raise TimeoutError('分析超时，请减少变化长度或稍后重试 / Analysis timed out')
        send_errors = []

        def send():
            try:
                self.process.stdin.write(block)
                self.process.stdin.flush()
            except OSError as error:
                send_errors.append(error)

        # Long game histories can exceed an OS pipe buffer. Bound sending too.
        writer = threading.Thread(target=send, daemon=True)
        writer.start()
        writer.join(timeout=max(0, deadline - time.monotonic()))
        if writer.is_alive():
            self.process.terminate()
            writer.join(timeout=1)
            raise TimeoutError('向 KataGo 发送请求超时 / Timed out sending a query to KataGo')
        if send_errors:
            raise RuntimeError('无法写入 KataGo / Could not write to KataGo') from send_errors[0]
        pending, finals = set(ids), {}
        while pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('分析超时，请减少变化长度或稍后重试 / Analysis timed out')
            try:
                response = self.responses.get(timeout=remaining)
            except queue.Empty as error:
                raise TimeoutError('等待 KataGo 超时 / Timed out waiting for KataGo') from error
            if '_eof' in response:
                detail = '\n'.join(self.logs[-4:])
                raise RuntimeError('KataGo 输出已关闭 / KataGo output closed: ' + detail)
            if '_parse_error' in response:
                raise RuntimeError('引擎返回非 JSON / Non-JSON engine output: ' + response['_parse_error'])
            if response.get('id') not in pending:
                continue
            if 'warning' in response:
                self.warnings.append(response)
            if 'error' in response:
                raise ValueError('KataGo: ' + str(response['error']))
            if response.get('isDuringSearch') is False:
                if not response.get('moveInfos') or response.get('noResults'):
                    raise ValueError('引擎没有返回可用着法 / Engine returned no usable moves')
                # An implicit rule conversion changes the question being answered.
                if self.warnings:
                    raise ValueError('引擎报告规则或输入警告，未生成讲解 / Engine warning: ' +
                                     str(self.warnings[-1].get('warning', self.warnings[-1])))
                pending.discard(response['id'])
                finals[response['id']] = response
        return [finals[query_id] for query_id in ids]

    def close(self):
        if self.process is not None:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=2)
                self.cleanup['method'] = 'stdin_eof'
            except (OSError, subprocess.TimeoutExpired):
                try:
                    self.process.terminate()
                    self.process.wait(timeout=2)
                    self.cleanup['method'] = 'terminate'
                except (OSError, subprocess.TimeoutExpired):
                    try:
                        self.process.kill()
                        self.process.wait(timeout=2)
                        self.cleanup['method'] = 'kill'
                    except (OSError, subprocess.TimeoutExpired) as error:
                        self.cleanup['error'] = str(error)
            for thread in self.threads:
                thread.join(timeout=1)
            self.cleanup.pop('kept_alive', None)
            self.cleanup.update(returncode=self.process.returncode,
                                process_stopped=self.process.poll() is not None,
                                reader_threads_stopped=all(not thread.is_alive() for thread in self.threads))
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass
            with _ACTIVE_LOCK:
                _ACTIVE_ENGINES.discard(self)
        self._close_run_files()
        self._write_run_summary()
        self.attached = False

    def __exit__(self, *args):
        self.close()


class EnginePool:
    """Keep one KataGo process warm between explanations.

    Starting KataGo and loading the network costs several seconds, so the
    process is reused. It is closed after `idle_seconds` without work so it
    does not hold GPU memory next to KaTrain's own engine indefinitely, and
    after any failed run so a stuck search cannot leak into the next one.
    """

    def __init__(self, settings, idle_seconds=300, factory=AnalysisEngine):
        self.settings = settings
        self.idle_seconds = idle_seconds
        self._factory = factory
        self._engine = None
        self._timer = None
        self._lock = threading.Lock()

    def _cancel_timer(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def acquire(self, output_dir):
        with self._lock:
            self._cancel_timer()
            engine = self._engine
            if engine is not None and engine.alive():
                engine.attach(output_dir)
                return engine
            if engine is not None:
                engine.close()
            engine = self._factory(self.settings, output_dir)
            self._engine = None
            engine.start()
            self._engine = engine
            return engine

    def release(self, engine, failed=False):
        with self._lock:
            if failed or not engine.alive():
                engine.close()
                if self._engine is engine:
                    self._engine = None
                return
            engine.detach()
            self._cancel_timer()
            self._timer = threading.Timer(self.idle_seconds, self._expire, args=(engine,))
            self._timer.daemon = True
            self._timer.start()

    def _expire(self, engine):
        with self._lock:
            if self._engine is engine and not engine.attached:
                engine.close()
                self._engine = None

    def close(self):
        with self._lock:
            self._cancel_timer()
            if self._engine is not None:
                self._engine.close()
                self._engine = None


def actor_metric(info, player):
    """Normalize engine BLACK reports once; UI values use percentages."""
    if player not in ('B', 'W'):
        raise ValueError('评估视角必须是 B 或 W / Perspective must be B or W')
    black_probability = float(info['winrate'])
    lead = float(info['scoreLead'])
    return {'winrate': (black_probability if player == 'B' else 1 - black_probability) * 100,
            'score_lead': lead if player == 'B' else -lead,
            'black_winrate': black_probability * 100,
            'visits': int(info.get('visits', 0))}
