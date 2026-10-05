"""What the chat model is told about the game, and where its settings live.

Kept free of Kivy so it can be tested anywhere. The model only sees what is
built here: the moves, the current position, KataGo's numbers for it and, when
there is one, the explanation already generated for this move. Everything is
read from KaTrain's objects; nothing is changed.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .llm import OPENAI, PRESETS

COLUMNS = "ABCDEFGHJKLMNOPQRST"
MAX_HISTORY_TURNS = 12
MAX_CANDIDATES = 6

SYSTEM_PROMPT = {
    "zh": (
        "你是一位耐心的围棋老师，正在陪学生复盘。下面的“对局资料”来自棋谱和 KataGo 的搜索，是你判断的唯一依据。\n"
        "要求：\n"
        "1. 坐标用资料里的写法（如 Q16，列不含 I）。黑棋 X，白棋 O。\n"
        "2. 胜率、目差和候选手只引用资料里的数字，不要编造；资料里没有的变化，要说明只是你的推测。\n"
        "3. 先直接回答问题，再用棋理解释原因（厚薄、先后手、大小、死活、方向），语言通俗，避免堆砌术语。\n"
        "4. 搜索次数少的候选不可靠，要提醒；差距在 0.5 目或 1 个百分点以内的两手视为基本等价。\n"
        "5. 回答尽量简短，除非学生要求详细。"
    ),
    "en": (
        "You are a patient Go teacher reviewing a game with a student. The game data below comes from the record "
        "and from KataGo's search, and is the only basis for your judgement.\n"
        "Rules:\n"
        "1. Use the coordinates as written in the data (e.g. Q16; columns skip I). Black is X, White is O.\n"
        "2. Quote win rates, score leads and candidate moves only from the data; never invent numbers, and say so "
        "when a line is your own guess rather than the engine's.\n"
        "3. Answer the question first, then explain the reason in Go terms (thickness, sente, size, life and death, "
        "direction) in plain language.\n"
        "4. Candidates with few visits are unreliable; moves within 0.5 points or 1 percentage point are about equal.\n"
        "5. Keep answers short unless asked for detail."
    ),
}

QUICK_PROMPTS = {
    "zh": ["刚才这手棋好不好？为什么？", "现在形势如何？", "下一手该下哪里？", "用初学者能懂的话讲讲"],
    "en": ["Was the last move good, and why?", "Who is ahead right now?", "Where should the next move be?",
           "Explain it for a beginner"],
}


# ----------------------------------------------------------------- settings

def settings_path(config_file=None, home=None):
    """Beside the configuration KaTrain is running with, so each installation keeps its own."""
    if config_file:
        try:
            return Path(config_file).resolve().parent / "explainer_chat.json"
        except OSError:
            pass
    return Path(home or os.path.expanduser("~")) / ".katrain" / "explainer_chat.json"


def default_settings():
    name, protocol, base_url, model = PRESETS[0]
    return {"preset": name, "protocol": protocol, "base_url": base_url, "model": model, "api_key": "",
            "temperature": 0.5, "max_tokens": 2000}


def load_settings(path=None):
    settings = default_settings()
    try:
        stored = json.loads(Path(path or settings_path()).read_text(encoding="utf-8"))
        if isinstance(stored, dict):
            settings.update({key: stored[key] for key in settings if key in stored})
    except (OSError, ValueError):
        pass
    if settings.get("protocol") not in ("openai", "anthropic"):
        settings["protocol"] = OPENAI
    return settings


def save_settings(settings, path=None):
    """The API key stays on this computer, in the user's own KaTrain folder."""
    path = Path(path or settings_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    allowed = default_settings()
    path.write_text(json.dumps({key: settings.get(key, allowed[key]) for key in allowed},
                               ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def is_configured(settings):
    if not settings.get("base_url") or not settings.get("model"):
        return False
    local = re.match(r"https?://(localhost|127\.0\.0\.1|\[::1\])([:/]|$)", str(settings.get("base_url")))
    return bool(settings.get("api_key")) or bool(local)


# ------------------------------------------------------------------ context

def _text(value, language):
    if isinstance(value, dict):
        return str(value.get(language) or value.get("zh") or value.get("en") or "")
    return "" if value is None else str(value)


def board_diagram(size, stones, last=None):
    """A plain-text board. ``stones`` are (player, x, y) with y counted from the bottom."""
    grid = [["." for _ in range(size)] for _ in range(size)]
    for player, x, y in stones:
        if 0 <= x < size and 0 <= y < size:
            grid[y][x] = "X" if player == "B" else "O"
    header = "   " + " ".join(COLUMNS[:size])
    rows = [header]
    for y in range(size - 1, -1, -1):
        rows.append(f"{y + 1:>2} " + " ".join(grid[y]) + f" {y + 1}")
    rows.append(header)
    return "\n".join(rows)


def _percent(black_winrate, player):
    value = black_winrate if player == "B" else 1 - black_winrate
    return f"{value * 100:.1f}%"


def _lead(black_lead, zh):
    if abs(black_lead) < 0.05:
        return "均势" if zh else "even"
    side = ("黑" if black_lead > 0 else "白") if zh else ("B" if black_lead > 0 else "W")
    return f"{side}+{abs(black_lead):.1f}"


def game_context(game, language="zh", max_moves=400):
    """Describe the KaTrain game at its current node."""
    zh = language == "zh"
    node = game.current_node
    size = game.board_size[0]
    lines = []
    root = game.root
    black = root.get_property("PB", None) or ("黑方" if zh else "Black")
    white = root.get_property("PW", None) or ("白方" if zh else "White")
    try:
        rules = game.rules
    except Exception:
        rules = "?"
    lines.append((f"棋盘 {size} 路，贴目 {game.komi}，规则 {rules}。黑：{black}，白：{white}。" if zh else
                  f"Board {size}x{size}, komi {game.komi}, rules {rules}. Black: {black}, White: {white}."))
    path = list(node.nodes_from_root)
    moves = []
    for item in path:
        for move in item.moves:
            moves.append((move.player, move.gtp()))
    shown = moves[-max_moves:]
    offset = len(moves) - len(shown)
    record = " ".join(f"{offset + index + 1}.{player}{vertex}" for index, (player, vertex) in enumerate(shown))
    lines.append((f"已下 {len(moves)} 手：" if zh else f"{len(moves)} moves played: ") + (record or ("（无）" if zh else "(none)")))
    to_play = node.next_player
    last = moves[-1] if moves else None
    if last:
        lines.append((f"刚下的一手：第 {len(moves)} 手 {'黑' if last[0] == 'B' else '白'} {last[1]}。" if zh else
                      f"Last move: move {len(moves)}, {'Black' if last[0] == 'B' else 'White'} {last[1]}."))
    lines.append(f"轮到{'黑' if to_play == 'B' else '白'}棋下。" if zh else f"{'Black' if to_play == 'B' else 'White'} to play.")
    stones = [(stone.player, stone.coords[0], stone.coords[1]) for stone in game.stones if stone.coords]
    lines.append(("当前局面（X 黑，O 白）：\n" if zh else "Current position (X Black, O White):\n")
                 + board_diagram(size, stones))
    try:
        prisoners = game.prisoner_count
        lines.append((f"提子：黑提 {prisoners.get('W', 0)} 子，白提 {prisoners.get('B', 0)} 子。" if zh else
                      f"Captures: Black took {prisoners.get('W', 0)}, White took {prisoners.get('B', 0)}."))
    except Exception:
        pass
    lines.extend(_analysis_lines(node, to_play, zh))
    return "\n".join(lines)


def _analysis_lines(node, to_play, zh):
    if not getattr(node, "analysis_exists", False):
        return ["KataGo 还没有分析完这个局面，暂时没有数字可用。" if zh else
                "KataGo has not analysed this position yet; no numbers are available."]
    lines = []
    winrate, score = node.winrate, node.score
    visits = getattr(node, "root_visits", 0)
    if winrate is not None and score is not None:
        lines.append((f"KataGo 对当前局面的评估（{visits} 次搜索）：黑胜率 {winrate * 100:.1f}%，目差 {_lead(score, zh)}。" if zh else
                      f"KataGo on this position ({visits} visits): Black win rate {winrate * 100:.1f}%, score {_lead(score, zh)}."))
    lost = getattr(node, "points_lost", None)
    if lost is not None and node.parent is not None:
        lines.append((f"刚下的一手比 KataGo 的首选约亏 {max(0.0, lost):.1f} 目。" if zh else
                      f"The last move lost about {max(0.0, lost):.1f} points against KataGo's first choice."))
    candidates = [move for move in (node.candidate_moves or []) if move.get("move")][:MAX_CANDIDATES]
    if candidates:
        lines.append(("KataGo 给下一手的候选（按推荐顺序；胜率为下棋方视角）：" if zh else
                      "KataGo's candidates for the next move (in order; win rate from the mover's side):"))
        for index, move in enumerate(candidates, 1):
            parts = [f"{index}. {move['move']}"]
            if move.get("winrate") is not None:
                parts.append(("胜率 " if zh else "win ") + _percent(move["winrate"], to_play))
            if move.get("scoreLead") is not None:
                parts.append(("目差 " if zh else "score ") + _lead(move["scoreLead"], zh))
            if move.get("pointsLost") is not None and index > 1:
                parts.append((f"比首选亏 {max(0.0, move.get('relativePointsLost', move['pointsLost'])):.1f} 目" if zh else
                              f"{max(0.0, move.get('relativePointsLost', move['pointsLost'])):.1f} pts behind the first"))
            parts.append((f"搜索 {move.get('visits', 0)} 次" if zh else f"{move.get('visits', 0)} visits"))
            pv = [str(step) for step in (move.get("pv") or [])[:8]]
            if len(pv) > 1:
                parts.append(("后续 " if zh else "line ") + " ".join(pv))
            lines.append("，".join(parts) if zh else ", ".join(parts))
    return lines


def explanation_context(result, language="zh", max_reasons=8):
    """Summarise an explanation the plugin has already generated for this position."""
    if not result:
        return ""
    zh = language == "zh"
    explanation = result.get("explanation") or {}
    player = result.get("player")
    name = ("黑" if player == "B" else "白") if zh else ("Black" if player == "B" else "White")
    number = int(result.get("move_index", 0)) + 1
    lines = [(f"本软件已生成的着法讲解（第 {number} 手 {name} {result.get('selected_move', '')}）：" if zh else
              f"Explanation already generated by this app (move {number}, {name} {result.get('selected_move', '')}):")]
    verdict = _text((explanation.get("verdict") or {}).get("label"), language)
    if verdict:
        lines.append(("结论：" if zh else "Verdict: ") + verdict)
    summary = _text(explanation.get("summary"), language)
    if summary:
        lines.append(summary)
    selected, alternative = result.get("selected") or {}, result.get("alternative") or {}
    if selected.get("winrate") is not None:
        lines.append((f"{result.get('selected_move')}：{name}方胜率 {selected['winrate']:.1f}%，目差 {selected.get('score_lead', 0):+.1f}。" if zh else
                      f"{result.get('selected_move')}: {name} win rate {selected['winrate']:.1f}%, score {selected.get('score_lead', 0):+.1f}."))
    if alternative.get("move") and alternative.get("winrate") is not None:
        lines.append((f"对比手 {alternative['move']}：胜率 {alternative['winrate']:.1f}%，目差 {alternative.get('score_lead', 0):+.1f}。" if zh else
                      f"Compared move {alternative['move']}: win rate {alternative['winrate']:.1f}%, score {alternative.get('score_lead', 0):+.1f}."))
    levels = {"board": "棋盘事实" if zh else "board fact", "search": "搜索支持" if zh else "search",
              "tentative": "推测" if zh else "tentative", "reference": "定式参考" if zh else "joseki reference"}
    for reason in (explanation.get("reasons") or [])[:max_reasons]:
        body = _text(reason.get("text"), language)
        if body:
            lines.append(f"- [{levels.get(reason.get('level'), reason.get('level') or '')}] {body}")
    for branch in result.get("branches") or []:
        steps = [f"{step.get('player')}{step.get('move')}" for step in branch.get("steps") or [] if step.get("ply")]
        if steps:
            label = ("讲解手的搜索变化：" if branch.get("id") == "selected" else "对比手的搜索变化：") if zh else (
                "Line after the explained move: " if branch.get("id") == "selected" else "Line after the compared move: ")
            lines.append(label + " ".join(steps))
    return "\n".join(lines)


def build_system(game_text, explanation_text="", language="zh"):
    language = language if language in SYSTEM_PROMPT else "en"
    heading = "对局资料" if language == "zh" else "Game data"
    body = game_text + ("\n\n" + explanation_text if explanation_text else "")
    return f"{SYSTEM_PROMPT[language]}\n\n===== {heading} =====\n{body}"


def trim_history(messages, turns=MAX_HISTORY_TURNS):
    """Keep the most recent exchanges, starting on a user message."""
    kept = [dict(message) for message in messages if message.get("content")][-2 * turns:]
    while kept and kept[0].get("role") != "user":
        kept.pop(0)
    return kept


# ------------------------------------------------------------------ markup

HEADING_COLOR = "ffd27a"


def to_markup(text):
    """Turn the Markdown models usually write into Kivy label markup.

    Only whole lines are styled. Inline emphasis is reduced to plain text:
    Kivy wraps Chinese by character, and a style change in the middle of a
    line would force a break there.
    """
    escaped = str(text).replace("&", "&amp;").replace("[", "&bl;").replace("]", "&br;")
    lines = []
    for line in escaped.split("\n"):
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]
        plain = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)
        plain = re.sub(r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])", r"\1", plain)
        plain = re.sub(r"`([^`\n]+)`", r"\1", plain)
        heading = re.match(r"#{1,6}\s+(.*)", plain)
        whole_bold = re.fullmatch(r"\*\*([^*]+)\*\*[:：]?", stripped)
        if heading or whole_bold:
            title = (heading.group(1) if heading else whole_bold.group(1)).strip("# ")
            line = f"[b][color={HEADING_COLOR}]{title}[/color][/b]"
        elif re.match(r"[-*+]\s+", plain):
            line = indent + "• " + re.sub(r"^[-*+]\s+", "", plain)
        elif re.fullmatch(r"\s*([-*_]\s*){3,}", line):
            line = "────────"
        else:
            line = indent + plain
        lines.append(line)
    return "\n".join(lines)


# ------------------------------------------------------------------ session

class ChatSession:
    """The conversation and the one request that may be running for it."""

    def __init__(self, stream=None):
        from .llm import stream_chat
        import threading

        self._stream = stream or stream_chat
        self._threading = threading
        self.messages = []
        self.busy = False
        self._generation = 0

    def clear(self):
        self.stop()
        self.messages = []

    def stop(self):
        """Abandon the running reply; whatever has arrived is kept by the caller."""
        self._generation += 1
        self.busy = False

    def ask(self, question, settings, system, on_delta, on_done, on_error):
        """Send ``question``. Callbacks run on a worker thread: on_delta(text), on_done(full), on_error(message)."""
        question = str(question).strip()
        if not question or self.busy:
            return False
        self.messages.append({"role": "user", "content": question})
        history = trim_history(self.messages)
        self.busy = True
        self._generation += 1
        generation = self._generation

        def current():
            return generation == self._generation

        def work():
            pieces = []
            try:
                for piece in self._stream(dict(settings), system, history, should_stop=lambda: not current()):
                    if not current():
                        break
                    pieces.append(piece)
                    on_delta(piece)
            except Exception as error:  # LLMError carries a readable message; anything else is shown as is
                if current():
                    self.busy = False
                    if pieces:
                        self.messages.append({"role": "assistant", "content": "".join(pieces)})
                    on_error(str(error))
                return
            reply = "".join(pieces)
            if current():  # a stopped reply is recorded by whoever stopped it
                self.busy = False
                if reply:
                    self.messages.append({"role": "assistant", "content": reply})
                    on_done(reply)
                else:
                    on_error("大模型没有返回内容。 / The model returned nothing.")

        self._threading.Thread(target=work, name="katrain-explainer-chat", daemon=True).start()
        return True
