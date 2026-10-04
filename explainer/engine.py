"""Bounded, single-job client for KataGo's JSON analysis protocol."""

from dataclasses import dataclass
import json
from pathlib import Path
import queue
import subprocess
import threading
import time
import weakref


_ACTIVE_ENGINES = weakref.WeakSet()
_ACTIVE_LOCK = threading.Lock()


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
    tuner: Path

    def validate(self):
        for name in ('engine', 'model', 'config', 'tuner'):
            if not getattr(self, name).is_file():
                raise ValueError(f'缺少 {name} 文件 / Missing {name} file: {getattr(self, name)}')


def discover_settings(project_dir, overrides=None):
    """Use CLI paths or this workspace's existing KaTrain/OpenCL installation."""
    overrides = overrides or {}
    workspace = Path(project_dir).parent
    bundled = workspace / 'KaTrain-1.20.0' / 'KaTrain' / '_internal' / 'katrain'
    paths = {
        'engine': bundled / 'KataGo' / 'katago.exe',
        'model': bundled / 'models' / 'b10c384h6nbttflrs.bin.gz',
        'config': bundled / 'KataGo' / 'analysis_config.cfg',
        'tuner': Path.home() / '.katrain' / 'opencltuning' /
            'tune13_gpuNVIDIAGeForceRTX5070LaptopGPU_x19_y19_c384_m192_h32_mv15.txt',
    }
    return EngineSettings(**{name: Path(overrides.get(name) or path).resolve()
                              for name, path in paths.items()})


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

    def __enter__(self):
        self.settings.validate()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.deadline = time.monotonic() + self.total_seconds
        try:
            self.input_file = (self.output_dir / 'requests.jsonl').open('w', encoding='utf-8')
            self.output_file = (self.output_dir / 'responses.jsonl').open('w', encoding='utf-8')
            metadata = subprocess.run([str(self.settings.engine), 'version'], capture_output=True,
                                      text=True, timeout=5, encoding='utf-8', errors='replace')
            if metadata.returncode:
                raise RuntimeError('无法查询引擎版本 / Engine version query failed')
            self.version = metadata.stdout.splitlines()[0]
            override = ('numAnalysisThreads=1,numSearchThreads=4,nnMaxBatchSize=8,'
                        'nnCacheSizePowerOfTwo=18,reportAnalysisWinratesAs=BLACK,'
                        f'openclTunerFile={self.settings.tuner}')
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

    def query(self, game, moves, visits, forced_move=None, actor=None):
        if forced_move and actor not in ('B', 'W'):
            raise ValueError('限制候选时必须指定执棋方 / A forced query requires actor B or W')
        self.request_counter += 1
        query_id = f'position-{self.request_counter}'
        payload = {
            'id': query_id, 'initialStones': game.initial_stones,
            'initialPlayer': game.initial_player, 'moves': moves,
            'rules': game.rules, 'komi': game.komi,
            'boardXSize': game.board_size, 'boardYSize': game.board_size,
            'maxVisits': visits, 'includeOwnership': True,
            'includeMovesOwnership': True, 'includePVVisits': True, 'analysisPVLen': 8,
        }
        if forced_move:
            payload['allowMoves'] = [{'player': actor, 'moves': [forced_move], 'untilDepth': 1}]
        encoded = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
        self.input_file.write(encoded + '\n')
        self.input_file.flush()
        if self.process.poll() is not None:
            raise RuntimeError('KataGo 已退出 / KataGo exited before the query')
        deadline = min(time.monotonic() + 40, self.deadline)
        send_errors = []

        def send():
            try:
                self.process.stdin.write(encoded + '\n')
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
        while True:
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
            if response.get('id') != query_id:
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
                return response

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
        for name in ('input_file', 'output_file'):
            stream = getattr(self, name, None)
            if stream is not None and not stream.closed:
                stream.close()
        if self.output_dir.is_dir():
            (self.output_dir / 'engine.log').write_text('\n'.join(self.logs), encoding='utf-8')
            (self.output_dir / 'cleanup.json').write_text(json.dumps(self.cleanup, indent=2), encoding='utf-8')

    def __exit__(self, *args):
        self.close()


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
