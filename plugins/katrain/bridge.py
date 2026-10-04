"""Read-only KaTrain v1.20 bridge to the local explanation service.

No Kivy import is required. The panel marshals worker callbacks through Clock.
The existing KaTrain tree, current node, engine analyses, and SGF files are never
edited by this bridge. Returned snapshots are exact legally replayed positions,
including captures, displayed by the panel inside the original app.
"""
from __future__ import annotations

from collections import OrderedDict
from contextlib import nullcontext
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import uuid


def bilingual(zh, en):
    return {"zh": zh, "en": en}


class BridgeError(ValueError):
    pass


class BackendUnavailable(BridgeError):
    pass


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
    def __init__(self, katrain, settings=None):
        if settings is None:
            config_path = Path(__file__).with_name("settings.json")
            settings = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        self.settings = settings
        base_url = settings.get("backend_url", "http://127.0.0.1:8788")
        address = urlsplit(base_url)
        if (address.scheme != "http" or address.hostname not in ("127.0.0.1", "localhost")
                or address.username or address.password or address.path not in ("", "/")
                or address.query or address.fragment):
            raise BridgeError("讲解服务必须在本机运行。 / The explanation service must run locally.")
        self.katrain, self.base_url = katrain, base_url.rstrip("/")
        self._contexts = OrderedDict()
        self._busy = False
        self._lock = threading.Lock()

    def _request(self, path, payload=None, timeout=10):
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        request = Request(self.base_url + path, data=encoded,
                          headers={"Content-Type": "application/json"} if encoded else {})
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            try:
                message = json.loads(error.read().decode("utf-8")).get("error")
            except (ValueError, UnicodeError):
                message = None
            if isinstance(message, dict):
                raise BridgeError(message.get("zh", "") + " / " + message.get("en", "")) from error
            raise BridgeError("本机讲解服务拒绝了请求。 / The local explanation service rejected the request.") from error
        except (URLError, TimeoutError, OSError) as error:
            raise BackendUnavailable("无法连接本机讲解服务。 / Cannot reach the local explanation service.") from error
        except (json.JSONDecodeError, UnicodeError) as error:
            raise BridgeError("本机端口未返回兼容的讲解数据，可能被其他应用占用。 / The local port returned incompatible data and may belong to another application.") from error

    def _ensure_backend(self):
        def verify(state):
            if not isinstance(state, dict) or state.get("application") != "katago-explainer" or state.get("api_version") != 1:
                raise BridgeError("本机端口被其他应用占用，请调整讲解插件的端口设置。 / The local port belongs to another application; change the explainer port setting.")
        deadline = time.monotonic() + 12
        try:
            verify(self._request("/api/state", timeout=1))
            return
        except BackendUnavailable:
            pass
        project = Path(self.settings.get("project_path", ""))
        python = Path(self.settings.get("python_path", ""))
        if not project.is_dir() or not (project / "explainer" / "server.py").is_file() or not python.is_file():
            raise BridgeError("增强版的讲解路径配置缺失，请重新运行安装入口。 / The enhanced app's explainer paths are missing; run its installer again.")
        log_path = project / "runs" / "plugin-backend.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        port = urlsplit(self.base_url).port or 80
        with log_path.open("ab") as backend_log:
            self._backend_process = subprocess.Popen(
                [str(python), "-m", "explainer.server", "--port", str(port)], cwd=str(project),
                stdin=subprocess.DEVNULL, stdout=backend_log, stderr=backend_log,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        while time.monotonic() < deadline:
            try:
                verify(self._request("/api/state", timeout=max(.05, min(1, deadline - time.monotonic()))))
                return
            except BackendUnavailable:
                threading.Event().wait(.35)
            if self._backend_process.poll() is not None:
                raise BridgeError("讲解服务未能启动，请查看 runs/plugin-backend.log；其他程序不会被关闭。 / The explainer did not start; check runs/plugin-backend.log. Other applications were left running.")
        raise BridgeError("讲解服务启动超时，请查看 runs/plugin-backend.log。 / The explainer startup timed out; check runs/plugin-backend.log.")

    def analyze(self, choice, on_progress, on_result, on_error):
        """Capture on the UI thread, then perform HTTP work on a daemon worker.

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
                self._ensure_backend()
                on_progress(bilingual("读取 KaTrain 当前分支…", "Reading the selected KaTrain branch…"), 0, 15)
                imported = self._request("/api/game", {"sgf": context.sgf})
                game_id = imported["game"]["id"]
                job_id = self._request("/api/analyze", {"game_id": game_id, "move_index": context.move_index,
                                                       "choice": context.choice})["job_id"]
                deadline, last_progress = time.monotonic() + 180, None
                while time.monotonic() < deadline:
                    job = self._request("/api/jobs/" + job_id)
                    progress = job.get("progress") or {}
                    if progress and progress != last_progress:
                        on_progress(progress["message"], progress.get("completed", 0), progress.get("total", 15))
                        last_progress = progress
                    if job.get("status") == "complete":
                        result = job["result"]
                        token = uuid.uuid4().hex
                        result["_katrain_bridge_token"] = token
                        with self._lock:
                            self._contexts[token] = context
                            while len(self._contexts) > 6:
                                self._contexts.popitem(last=False)
                        if not self.is_current(result):
                            raise BridgeError("生成期间棋盘位置已改变，请在新位置重新讲解。 / The position changed during analysis; request an explanation for the new position.")
                        on_result(result)
                        return
                    if job.get("status") == "error":
                        on_error(job.get("error") or bilingual("讲解失败。", "Explanation failed."))
                        return
                    threading.Event().wait(.7)
                raise BridgeError("等待讲解超时，请稍后重试。 / Explanation timed out; try again later.")
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

    def clear_preview(self):
        """Panel compatibility; preview state belongs entirely to the panel."""
        return None
