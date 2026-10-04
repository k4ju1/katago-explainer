"""Main-line SGF import, preserving rules, setup and every preceding move."""
from __future__ import annotations

from dataclasses import dataclass, field
import math

from .board import Board, BoardError, normalize_rules, point_to_vertex


class SGFError(ValueError):
    pass


@dataclass
class GameRecord:
    board_size: int
    komi: float
    rules: str
    initial_player: str
    initial_stones: list[list[str]]
    moves: list[list[str]]
    metadata: dict[str, str] = field(default_factory=dict)
    warnings: list[dict[str, str]] = field(default_factory=list)

    def board_at(self, index: int) -> Board:
        """Position after `index` plies; setup is position zero."""
        if not isinstance(index, int) or not 0 <= index <= len(self.moves):
            raise SGFError("手数超出棋谱。 / Move index outside the game.")
        board = Board(self.board_size, self.initial_stones, self.initial_player, self.rules)
        for player, move in self.moves[:index]:
            board.play(player, move)
        return board

    def to_dict(self) -> dict:
        return {"board_size": self.board_size, "komi": self.komi, "rules": self.rules,
                "initial_player": self.initial_player, "initial_stones": self.initial_stones,
                "moves": self.moves, "metadata": self.metadata, "warnings": self.warnings}


class _Parser:
    def __init__(self, text: str):
        self.text = text.lstrip("\ufeff")
        self.at, self.nodes = 0, 0

    def skip(self):
        while self.at < len(self.text) and self.text[self.at].isspace():
            self.at += 1

    def tree(self, depth=0):
        self.skip()
        if depth > 128:
            raise SGFError("棋谱变化树过深。 / SGF variation tree is too deep.")
        if self.at >= len(self.text) or self.text[self.at] != "(":
            raise SGFError("SGF 必须以括号内的棋谱树表示。 / Expected an SGF game tree.")
        self.at += 1
        sequence = []
        self.skip()
        while self.at < len(self.text) and self.text[self.at] == ";":
            sequence.append(self.node())
            self.skip()
        if not sequence:
            raise SGFError("SGF 棋谱树为空。 / Empty SGF game tree.")
        variations = []
        while self.at < len(self.text) and self.text[self.at] == "(":
            variations.append(self.tree(depth + 1))
            self.skip()
        if self.at >= len(self.text) or self.text[self.at] != ")":
            raise SGFError("SGF 括号不完整。 / Unclosed SGF game tree.")
        self.at += 1
        return sequence, variations

    def node(self):
        self.nodes += 1
        if self.nodes > 20000:
            raise SGFError("棋谱节点过多。 / Too many SGF nodes.")
        self.at += 1
        properties = {}
        self.skip()
        while self.at < len(self.text) and "A" <= self.text[self.at] <= "Z":
            start = self.at
            while self.at < len(self.text) and "A" <= self.text[self.at] <= "Z":
                self.at += 1
            name = self.text[start:self.at]
            self.skip()
            values = []
            while self.at < len(self.text) and self.text[self.at] == "[":
                values.append(self.value())
                self.skip()
            if not values or name in properties:
                raise SGFError("SGF 属性缺少值或重复。 / Missing or duplicate SGF property.")
            properties[name] = values
        return properties

    def value(self):
        self.at += 1
        result = []
        while self.at < len(self.text):
            char = self.text[self.at]
            self.at += 1
            if char == "]":
                return "".join(result)
            if char == "\\":
                if self.at >= len(self.text):
                    break
                escaped = self.text[self.at]
                self.at += 1
                if escaped in "\r\n":
                    if self.at < len(self.text) and self.text[self.at] in "\r\n" and self.text[self.at] != escaped:
                        self.at += 1
                    continue
                result.append(escaped)
            else:
                result.append(char)
        raise SGFError("SGF 属性值未关闭。 / Unclosed SGF property value.")


def _one(props, name, default=None):
    values = props.get(name)
    if values is None:
        return default
    if len(values) != 1:
        raise SGFError(f"{name} 应只有一个值。 / {name} must have one value.")
    return values[0]


def _sgf_point(value: str, size: int, allow_pass=False):
    if allow_pass and (value == "" or value == "tt"):
        return None
    if len(value) != 2 or not all("a" <= c <= "s" for c in value):
        raise SGFError(f"无效 SGF 坐标：{value}。 / Invalid SGF coordinate: {value}.")
    point = ord(value[0]) - 97, ord(value[1]) - 97
    if point[0] >= size or point[1] >= size:
        raise SGFError("SGF 坐标超出棋盘。 / SGF coordinate outside board.")
    return point


def _setup_points(values, size):
    result = []
    for value in values:
        if ":" in value:
            components = value.split(":")
            if len(components) != 2:
                raise SGFError("无效的摆子矩形。 / Invalid setup rectangle.")
            a, b = (_sgf_point(item, size) for item in components)
            if a[0] > b[0] or a[1] > b[1]:
                raise SGFError("摆子矩形端点顺序不正确。 / Reversed setup rectangle.")
            result.extend((x, y) for x in range(a[0], b[0] + 1) for y in range(a[1], b[1] + 1))
        else:
            result.append(_sgf_point(value, size))
    return result


def parse_sgf(text: str) -> GameRecord:
    if not isinstance(text, str) or len(text) > 2_000_000:
        raise SGFError("棋谱为空或过大。 / SGF text is invalid or too large.")
    parser = _Parser(text)
    tree = parser.tree()
    parser.skip()
    if parser.at != len(parser.text):
        raise SGFError("一次只能导入一盘棋。 / Import one game at a time.")
    mainline, variation_count = [], 0
    while tree:
        sequence, children = tree
        mainline.extend(sequence)
        variation_count += max(0, len(children) - 1)
        tree = children[0] if children else None
    root = mainline[0]
    if _one(root, "GM", "1") != "1":
        raise SGFError("此文件不是围棋棋谱。 / This SGF is not a Go game.")
    size_token = _one(root, "SZ", "19")
    try:
        if ":" in size_token:
            parts = size_token.split(":")
            if len(parts) != 2 or parts[0] != parts[1]:
                raise ValueError()
            size = int(parts[0])
        else:
            size = int(size_token)
        komi = float(_one(root, "KM", "7.5"))
        handicap = int(_one(root, "HA", "0"))
    except ValueError as exc:
        raise SGFError("棋盘大小、贴目或让子数无效。 / Invalid board size, komi, or handicap.") from exc
    if size not in (9, 13, 19) or not math.isfinite(komi) or not -100 <= komi <= 100 or handicap < 0:
        raise SGFError("棋盘大小、贴目或让子数不受支持。 / Unsupported board size, komi, or handicap.")
    warnings = []
    try:
        rules = normalize_rules(_one(root, "RU", "Chinese"))
    except BoardError as exc:
        raise SGFError(str(exc)) from exc
    if "RU" not in root:
        warnings.append({"zh": "棋谱未写规则，暂按中国规则；请在分析前确认。",
                         "en": "No rules in SGF; Chinese rules are assumed. Confirm before analysis."})
    if "KM" not in root:
        warnings.append({"zh": "棋谱未写贴目，暂用 7.5；请在分析前确认。",
                         "en": "No komi in SGF; 7.5 is assumed. Confirm before analysis."})
    if variation_count:
        warnings.append({"zh": "棋谱有分支；本次沿每处的第一个变化重放主线。",
                         "en": "The SGF has variations; replay follows the first branch at each fork."})
    initial_player = _one(root, "PL", "W" if handicap >= 2 else "B")
    if initial_player not in ("B", "W"):
        raise SGFError("PL 应为 B 或 W。 / PL must be B or W.")
    initial_stones, occupied = [], set()
    for prop, player in (("AB", "B"), ("AW", "W")):
        for point in _setup_points(root.get(prop, []), size):
            if point in occupied:
                raise SGFError("初始摆子重复或重叠。 / Duplicate or overlapping setup stones.")
            occupied.add(point)
            initial_stones.append([player, point_to_vertex(point, size)])
    # AE at the root can only remove points from an empty diagram; mixed setup is ambiguous.
    if root.get("AE"):
        _setup_points(root["AE"], size)
        if initial_stones:
            raise SGFError("暂不支持混合 AB/AW 与 AE 的初始编辑。 / Mixed add/remove setup is unsupported.")
    if ("AB" in root or "AW" in root or "AE" in root) and ("B" in root or "W" in root):
        raise SGFError("同一节点不能既摆子又落子。 / A node cannot contain setup and a move.")
    moves = []
    for index, props in enumerate(mainline):
        if index and any(prop in props for prop in ("AB", "AW", "AE", "PL", "SZ", "RU", "KM", "HA")):
            raise SGFError("暂不支持中途编辑局面、轮次或规则的棋谱。 / Mid-game setup, turn, or rule edits are unsupported.")
        if "B" in props and "W" in props:
            raise SGFError("节点包含两种颜色的落子。 / A node contains both Black and White moves.")
        for player in ("B", "W"):
            if player in props:
                moves.append([player, point_to_vertex(_sgf_point(_one(props, player), size, True), size)])
                if len(moves) > 1000:
                    raise SGFError("棋谱主线不能超过 1000 手。 / SGF main line cannot exceed 1000 plies.")
    game = GameRecord(size, komi, rules, initial_player, initial_stones, moves,
                      {key: _one(root, key, "") for key in ("PB", "PW", "GN", "DT", "RE")}, warnings)
    try:
        game.board_at(len(moves))
    except BoardError as exc:
        raise SGFError(f"棋谱无法合法重放：{exc} / Game cannot be legally replayed.") from exc
    return game
