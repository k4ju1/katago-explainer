"""Small rule-validating Go board for replay and auditable local facts.

Coordinates use KataGo/GTP vertices (A1 is bottom left, I is skipped).
Only ordinary no-suicide rules are supported; this is not a life/death solver.
"""
from __future__ import annotations

from typing import Iterable


COLUMNS = "ABCDEFGHJKLMNOPQRST"


class BoardError(ValueError):
    """An invalid move or unsupported board configuration."""


def other(player: str) -> str:
    if player not in ("B", "W"):
        raise BoardError("棋子颜色必须是 B 或 W。 / Player must be B or W.")
    return "W" if player == "B" else "B"


def vertex_to_point(vertex: str, size: int) -> tuple[int, int] | None:
    if not isinstance(vertex, str):
        raise BoardError("落点必须是文本坐标。 / Move must be a text vertex.")
    token = vertex.strip().upper()
    if token == "PASS":
        return None
    if len(token) < 2 or token[0] not in COLUMNS or not token[1:].isdigit():
        raise BoardError(f"无效落点：{vertex}。 / Invalid vertex: {vertex}.")
    x, row = COLUMNS.index(token[0]), int(token[1:])
    if x >= size or not 1 <= row <= size:
        raise BoardError(f"落点超出棋盘：{vertex}。 / Vertex outside board: {vertex}.")
    return x, size - row


def point_to_vertex(point: tuple[int, int] | None, size: int) -> str:
    if point is None:
        return "pass"
    x, y = point
    if not (0 <= x < size and 0 <= y < size):
        raise BoardError("坐标超出棋盘。 / Point outside board.")
    return f"{COLUMNS[x]}{size - y}"


def normalize_rules(rules: str) -> str:
    """Map common SGF rules to accepted KataGo names without guessing variants."""
    aliases = {
        "chinese": "chinese", "中国规则": "chinese", "中国": "chinese",
        "japanese": "japanese", "日本规则": "japanese", "日本": "japanese",
        "korean": "korean", "韩国规则": "korean", "韩国": "korean",
        "aga": "aga",
    }
    key = str(rules).strip().lower()
    if key not in aliases:
        raise BoardError(
            f"暂不支持规则 {rules}；请选择 Chinese、Japanese、Korean 或 AGA。 "
            f"/ Unsupported rules {rules}; use Chinese, Japanese, Korean, or AGA."
        )
    return aliases[key]


class Board:
    def __init__(self, size: int = 19, setup: Iterable[Iterable[str]] | None = None,
                 to_play: str = "B", rules: str = "chinese"):
        if size not in (9, 13, 19):
            raise BoardError("目前支持 9、13、19 路棋盘。 / Supported board sizes: 9, 13, 19.")
        other(to_play)
        self.size = size
        self.rules = normalize_rules(rules)
        self.to_play = to_play
        self.cells: dict[tuple[int, int], str] = {}
        self.last_move: str | None = None
        self.ko: tuple[int, int] | None = None
        self.move_number = 0
        for player, vertex in setup or []:
            other(player)
            point = vertex_to_point(vertex, size)
            if point is None or point in self.cells:
                raise BoardError("摆子坐标重复或无效。 / Duplicate or invalid setup point.")
            self.cells[point] = player
        self._seen_situations = {(self._position(), self.to_play)}

    def copy(self) -> "Board":
        result = Board(self.size, to_play=self.to_play, rules=self.rules)
        result.cells = dict(self.cells)
        result.last_move, result.ko = self.last_move, self.ko
        result.move_number = self.move_number
        result._seen_situations = set(self._seen_situations)
        return result

    def _position(self) -> tuple:
        return tuple(sorted((x, y, color) for (x, y), color in self.cells.items()))

    def neighbors(self, point: tuple[int, int]) -> list[tuple[int, int]]:
        x, y = point
        return [(a, b) for a, b in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
                if 0 <= a < self.size and 0 <= b < self.size]

    def _group(self, point: tuple[int, int]) -> tuple[set, set]:
        color = self.cells.get(point)
        if color is None:
            return set(), set()
        stones, liberties, pending = set(), set(), [point]
        while pending:
            current = pending.pop()
            if current in stones:
                continue
            stones.add(current)
            for adjacent in self.neighbors(current):
                occupant = self.cells.get(adjacent)
                if occupant is None:
                    liberties.add(adjacent)
                elif occupant == color and adjacent not in stones:
                    pending.append(adjacent)
        return stones, liberties

    def _group_dict(self, stones: set, liberties: set) -> dict:
        color = self.cells[next(iter(stones))] if stones else None
        return {
            "player": color,
            "stones": sorted(point_to_vertex(p, self.size) for p in stones),
            "liberties": sorted(point_to_vertex(p, self.size) for p in liberties),
            "libertyCount": len(liberties),
        }

    def groups(self) -> list[dict]:
        checked, result = set(), []
        for point in sorted(self.cells):
            if point not in checked:
                stones, liberties = self._group(point)
                checked.update(stones)
                result.append(self._group_dict(stones, liberties))
        return result

    def group_at(self, vertex: str) -> dict | None:
        point = vertex_to_point(vertex, self.size)
        if point is None or point not in self.cells:
            return None
        return self._group_dict(*self._group(point))

    def snapshot(self) -> dict:
        return {
            "size": self.size,
            "stones": [{"player": color, "move": point_to_vertex(point, self.size),
                        "x": point[0], "y": point[1]}
                       for point, color in sorted(self.cells.items())],
            "toPlay": self.to_play,
            "lastMove": self.last_move,
            "moveNumber": self.move_number,
            "ko": point_to_vertex(self.ko, self.size) if self.ko else None,
        }

    def play(self, player: str, move: str) -> dict:
        """Apply one legal move, or leave the board unchanged on an error."""
        other(player)
        if player != self.to_play:
            raise BoardError("下棋方与轮次不符。 / Player does not match the turn.")
        point = vertex_to_point(move, self.size)
        vertex = point_to_vertex(point, self.size)
        if point is None:
            self.to_play = other(player)
            self.last_move, self.ko = "pass", None
            self.move_number += 1
            self._seen_situations.add((self._position(), self.to_play))
            return {"player": player, "move": "pass", "pass": True,
                    "captured": [], "capturedCount": 0, "connectedGroups": 0,
                    "rescuedAtariGroups": [], "createdAtariGroups": [],
                    "moveGroupLibertiesAfter": None, "selfAtari": False}
        if point in self.cells:
            raise BoardError(f"{vertex} 已有棋子。 / {vertex} is occupied.")
        if point == self.ko:
            raise BoardError("不能立即回提劫。 / Immediate ko recapture is illegal.")
        adjacent_groups, seen = [], set()
        for adjacent in self.neighbors(point):
            if adjacent in self.cells and adjacent not in seen:
                stones, liberties = self._group(adjacent)
                seen.update(stones)
                adjacent_groups.append((self.cells[adjacent], stones, liberties))
        old_cells = dict(self.cells)
        self.cells[point] = player
        captured = set()
        for adjacent in self.neighbors(point):
            if self.cells.get(adjacent) == other(player):
                stones, liberties = self._group(adjacent)
                if not liberties:
                    captured.update(stones)
                    for stone in stones:
                        del self.cells[stone]
        move_stones, move_liberties = self._group(point)
        if not move_liberties:
            self.cells = old_cells
            raise BoardError("本工具暂不支持自杀着法。 / Suicide moves are unsupported.")
        position, next_player = self._position(), other(player)
        # KataGo's named "chinese" rules use SIMPLE ko (not chinese-ogs PSK).
        # Japanese/Korean also use SIMPLE; named AGA uses SITUATIONAL superko.
        repeats = self.rules == "aga" and (position, next_player) in self._seen_situations
        if repeats:
            self.cells = old_cells
            raise BoardError("此着重复已有局面，违反超级劫规则。 / This move violates superko.")
        friendly = [(stones, liberties) for color, stones, liberties in adjacent_groups if color == player]
        rescued = [sorted(point_to_vertex(p, self.size) for p in stones)
                   for stones, liberties in friendly if len(liberties) == 1 and len(move_liberties) > 1]
        created = []
        for color, stones, liberties in adjacent_groups:
            surviving = stones - captured
            if color != player and surviving and len(liberties) > 1:
                after_stones, after_liberties = self._group(next(iter(surviving)))
                if len(after_liberties) == 1:
                    created.append(sorted(point_to_vertex(p, self.size) for p in after_stones))
        self.ko = (next(iter(captured)) if len(captured) == 1 and len(move_stones) == 1
                   and len(move_liberties) == 1 else None)
        self.last_move, self.to_play = vertex, next_player
        self.move_number += 1
        self._seen_situations.add((position, next_player))
        return {
            "player": player, "move": vertex, "pass": False,
            "captured": sorted(point_to_vertex(p, self.size) for p in captured),
            "capturedCount": len(captured),
            "connectedGroups": len(friendly) if len(friendly) > 1 else 0,
            "friendlyGroupsBefore": [sorted(point_to_vertex(p, self.size) for p in stones)
                                     for stones, _ in friendly],
            "rescuedAtariGroups": rescued, "createdAtariGroups": created,
            "moveGroupLibertiesAfter": len(move_liberties),
            "moveGroupLiberties": sorted(point_to_vertex(p, self.size) for p in move_liberties),
            "selfAtari": len(move_liberties) == 1,
            "ko": point_to_vertex(self.ko, self.size) if self.ko else None,
        }
