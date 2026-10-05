"""Read-only KaTrain v1.20 bridge that runs the explanation inside KaTrain.

The explanation pipeline is imported as a library and its searches are sent to
the KataGo engine KaTrain already has running: no local server, no second
KataGo process and no extra Python runtime. No Kivy import is required; the
panel marshals worker callbacks through Clock. The existing KaTrain tree,
current node, engine analyses, and SGF files are never edited by this bridge.
Returned snapshots are exact legally replayed positions, including captures,
displayed by the panel inside the original app.
"""
from __future__ import annotations

from collections import OrderedDict
from contextlib import nullcontext
from dataclasses import dataclass
import hashlib
from pathlib import Path
import queue
import threading
import time
from types import SimpleNamespace
import uuid

if __package__ == "katrain_explainer":
    from .engine import analysis_payload, validate_analysis
else:
    from explainer.engine import analysis_payload, validate_analysis


def bilingual(zh, en):
    return {"zh": zh, "en": en}


class BridgeError(ValueError):
    pass


class EngineUnavailable(BridgeError):
    pass


QUERY_SECONDS = 40
EXTRA_SECONDS_PER_QUERY = 5
RUN_SECONDS = 150
# Explanation searches go ahead of KaTrain's background analysis of other moves.
QUERY_PRIORITY = 1000


def _core():
    """The pipeline modules: beside this file when installed, else the repository package."""
    if __package__ == "katrain_explainer":
        from . import service, sgf
    else:
        from explainer import service, sgf
    return service, sgf


class KaTrainEngineClient:
    """Send the pipeline's positions through KaTrain's own KataGo engine.

    It offers the `query` / `query_many` interface of the standalone client,
    so the same pipeline runs unchanged. KaTrain's reader thread delivers the
    answers; this client only waits for them, with a bound.
    """

    def __init__(self, katrain, total_seconds=RUN_SECONDS):
        self.katrain = katrain
        self.version = "KataGo (KaTrain engine)"
        self.cleanup = {"method": "katrain_engine", "kept_alive": True, "process_stopped": False}
        self.deadline = time.monotonic() + total_seconds

    def engine(self):
        engine = getattr(self.katrain, "engine", None)
        if engine is None or not callable(getattr(engine, "send_query", None)):
            raise EngineUnavailable("KaTrain 的 KataGo 引擎尚未启动。 / KaTrain's KataGo engine is not running yet.")
        check = getattr(engine, "check_alive", None)
        if callable(check) and not check():
            raise EngineUnavailable("KaTrain 的 KataGo 引擎已停止，请先在 KaTrain 中恢复引擎。 / KaTrain's KataGo engine has stopped; restore it in KaTrain first.")
        return engine

    @staticmethod
    def _payload(engine, game, request):
        settings = dict(getattr(engine, "override_settings", None) or {})
        settings.update({"reportAnalysisWinratesAs": "BLACK", "wideRootNoise": 0.0})
        payload = analysis_payload(game, request)
        payload.update(priority=getattr(engine, "base_priority", 0) + QUERY_PRIORITY,
                       overrideSettings=settings)
        return payload

    def query(self, game, moves, visits, forced_move=None, actor=None):
        return self.query_many(game, [{"moves": moves, "visits": visits,
                                       "forced_move": forced_move, "actor": actor}])[0]

    def query_many(self, game, requests):
        if not requests:
            return []
        engine = self.engine()
        answers, callbacks = queue.Queue(), []
        allowance = QUERY_SECONDS + EXTRA_SECONDS_PER_QUERY * (len(requests) - 1)
        deadline = min(time.monotonic() + allowance, self.deadline)
        results = {}
        try:
            for index, request in enumerate(requests):
                def done(analysis, partial_result=False, index=index):
                    if not partial_result:
                        answers.put((index, analysis, None))

                def failed(analysis, index=index):
                    answers.put((index, None, analysis))

                callbacks.append(done)
                engine.send_query(self._payload(engine, game, request), done, failed)
            while len(results) < len(requests):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise queue.Empty
                index, analysis, error = answers.get(timeout=remaining)
                if error is not None:
                    detail = error.get("error", error) if isinstance(error, dict) else error
                    raise ValueError("KataGo: " + str(detail))
                validate_analysis(analysis)
                results[index] = analysis
        except queue.Empty:
            self._abandon(engine, callbacks)
            raise TimeoutError("等待 KaTrain 引擎超时；如果刚开了新对局或引擎正忙，请稍后重试。 / Timed out waiting for KaTrain's engine; retry if a new game was started or the engine is busy.") from None
        except Exception:
            self._abandon(engine, callbacks)
            raise
        return [results[index] for index in range(len(requests))]

    @staticmethod
    def _abandon(engine, callbacks):
        """Best effort: stop searches whose answers nobody will read."""
        try:
            with engine.thread_lock:
                mine = [query_id for query_id, entry in engine.queries.items() if entry[0] in callbacks]
            for query_id in mine:
                engine.terminate_query(query_id)
        except Exception:
            pass


class _KaTrainEngineSession:
    """Pool-shaped adapter: each explanation borrows KaTrain's engine and returns it running."""

    def __init__(self, katrain):
        self.katrain = katrain

    def acquire(self, _output_dir):
        client = KaTrainEngineClient(self.katrain)
        client.engine()
        return client

    def release(self, _client, failed=False):
        return None


def _escape(value):
    return str(value).replace("\\", "\\\\").replace("]", "\\]").replace("\r", " ").replace("\n", " ")


def _property(name, values):
    return name + "".join("[" + _escape(value) + "]" for value in values)


@dataclass(frozen=True)
class PositionContext:
    sgf: str
    move_index: int
    choice: str
    source_game: object
    source_node: object
    base_node: object
    fingerprint: str


def export_position(game, choice="actual"):
    """Serialize only the selected branch ancestry, directly from KaTrain nodes.

    Actual means the last played move at or above the selected node. AI means
    the recommendation in the currently selected position. The whole ancestry
    is retained; a current-stones diagram is insufficient for ko/history.
    """
    choice = "actual" if choice == "last" else choice
    if choice not in ("actual", "ai"):
        raise BridgeError("请选择上一手或 AI 推荐。 / Choose the last move or the AI recommendation.")
    source_node = game.current_node
    path = list(source_node.nodes_from_root)
    if not path or path[0] is not game.root:
        raise BridgeError("当前节点不属于这盘棋。 / The selected node does not belong to this game.")
    size_x, size_y = source_node.board_size
    if size_x != size_y or size_x not in (9, 13, 19):
        raise BridgeError("讲解支持 9、13、19 路正方形棋盘。 / Explanation supports square 9, 13, or 19 boards.")
    rules = game.rules
    if not isinstance(rules, str) or rules.lower() not in ("chinese", "japanese", "korean", "aga"):
        raise BridgeError("当前规则暂不支持讲解。 / The current rules are not supported by the explainer.")
    initial_player = source_node.initial_player
    if initial_player not in ("B", "W"):
        raise BridgeError("无法确定初始下棋方。 / Could not determine the initial player.")
    # Read the actual rules KaTrain sends to KataGo, rather than interpreting RU
    # independently; KaTrain supports cn/jp aliases and inherits missing rules.
    root_properties = [_property("GM", [1]), _property("FF", [4]), _property("CA", ["UTF-8"]),
                       _property("SZ", [size_x]), _property("KM", [source_node.komi]),
                       _property("RU", [rules.lower()]), _property("PL", [initial_player])]
    setup = {"B": [], "W": []}
    for move in game.root.placements:
        if move.player not in setup:
            raise BridgeError("初始摆子颜色无效。 / Invalid setup color.")
        setup[move.player].append(move.sgf((size_x, size_y)))
    for player, vertices in setup.items():
        if vertices:
            root_properties.append(_property("A" + player, vertices))
    for key in ("PB", "PW", "GN", "DT"):
        value = game.root.get_property(key)
        if value is not None:
            root_properties.append(_property(key, [value]))
    move_nodes = []
    for node in path:
        if node.clear_placements or (node is not game.root and node.placements):
            raise BridgeError("暂不支持包含中途摆子或移除棋子的局面。 / Mid-game setup or removed stones are unsupported.")
        if node is not game.root and any(key in node.properties for key in ("PL", "SZ", "RU", "KM", "HA")):
            raise BridgeError("暂不支持中途修改轮次或规则。 / Mid-game turn or rule edits are unsupported.")
        node_moves = list(node.moves)
        if len(node_moves) > 1 or (node is game.root and node_moves and node.placements):
            raise BridgeError("暂不支持同节点的多着落子或摆子加落子。 / Multiple moves or mixed setup/moves in a node are unsupported.")
        for move in node_moves:
            if move.player not in ("B", "W"):
                raise BridgeError("棋谱落子颜色无效。 / Invalid move color.")
            move_nodes.append((node, _property(move.player, [move.sgf((size_x, size_y))])))
    if len(move_nodes) > 1000:
        raise BridgeError("讲解主线最多支持 1000 手。 / Explanation supports at most 1000 plies.")
    if choice == "actual":
        if not move_nodes:
            raise BridgeError("当前没有上一手，请选择 AI 推荐。 / No previous move here; choose the AI recommendation.")
        base_node = move_nodes[-1][0].parent
        if base_node is None:
            raise BridgeError("暂不支持根节点本身包含实战落子。 / A recorded move in the root node is unsupported.")
        move_index = len(move_nodes) - 1
    else:
        base_node, move_index = source_node, len(move_nodes)
    sgf = "(;" + "".join(root_properties) + "".join(";" + props for _, props in move_nodes) + ")"
    fingerprint = hashlib.sha256(sgf.encode("utf-8")).hexdigest()
    return PositionContext(sgf, move_index, choice, game, source_node, base_node, fingerprint)


class KaTrainBridge:
    def __init__(self, katrain):
        self.katrain = katrain
        self._contexts = OrderedDict()
        self._busy = False
        self._lock = threading.Lock()

    def _model_name(self):
        try:
            return Path(str(self.katrain.config("engine/model") or "KaTrain model")).name
        except Exception:
            return "KaTrain model"

    def analyze(self, choice, on_progress, on_result, on_error):
        """Capture on the UI thread, then run the pipeline on a daemon worker.

        Callbacks run on the worker: on_progress(message, completed, total),
        on_result(result), on_error({zh,en}). The panel schedules UI updates.
        """
        try:
            game = self.katrain.game
            with getattr(game, "_lock", nullcontext()):
                context = export_position(game, choice)
            with self._lock:
                if self._busy:
                    raise BridgeError("已有讲解在生成，请等待。 / An explanation is already running; please wait.")
                self._busy = True
        except Exception as error:
            threading.Thread(target=on_error, args=(bilingual(str(error), str(error)),), daemon=True).start()
            return False

        def worker():
            try:
                service, sgf = _core()
                on_progress(bilingual("读取 KaTrain 当前分支…", "Reading the selected KaTrain branch…"), 0, service.PHASES)
                record = sgf.parse_sgf(context.sgf)
                result = service.explain_move(
                    record, "katrain", context.move_index, context.choice,
                    SimpleNamespace(model=Path(self._model_name())), None, on_progress,
                    pool=_KaTrainEngineSession(self.katrain))
                token = uuid.uuid4().hex
                result["_katrain_bridge_token"] = token
                with self._lock:
                    self._contexts[token] = context
                    while len(self._contexts) > 6:
                        self._contexts.popitem(last=False)
                if not self.is_current(result):
                    raise BridgeError("生成期间棋盘位置已改变，请在新位置重新讲解。 / The position changed during analysis; request an explanation for the new position.")
                on_result(result)
            except Exception as error:
                on_error(bilingual(str(error), str(error)))
            finally:
                with self._lock:
                    self._busy = False
        threading.Thread(target=worker, name="katrain-explainer-bridge", daemon=True).start()
        return True

    def is_current(self, result):
        context = self._contexts.get(result.get("_katrain_bridge_token"))
        if not context or self.katrain.game is not context.source_game or self.katrain.game.current_node is not context.source_node:
            return False
        try:
            with getattr(context.source_game, "_lock", nullcontext()):
                return export_position(context.source_game, context.choice).fingerprint == context.fingerprint
        except Exception:
            return False

    def show_step(self, result, branch_id, ply):
        """Return an exact board for the native panel, without touching the tree."""
        if not self.is_current(result):
            raise BridgeError("棋盘位置已改变，请重新生成讲解。 / The position changed; generate a new explanation.")
        branch = next((item for item in result.get("branches", []) if item.get("id") == branch_id), None)
        if not branch or type(ply) is not int or not 0 <= ply < len(branch["steps"]):
            raise BridgeError("变化步骤无效。 / Invalid continuation step.")
        return branch["steps"][ply]["board"]
