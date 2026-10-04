"""Bilingual explanations built from legal replay and explicit search evidence.

No language model is used. The summary leads with a search-based verdict,
then board facts. Board facts, search-supported statements, and tentative
positional interpretations stay separately labelled so a plausible sentence
cannot masquerade as proof.
"""
from __future__ import annotations

import math

from .board import Board, BoardError, other, point_to_vertex, vertex_to_point
from .joseki import find_joseki
from .terms import get_terms


# Two candidates closer than BOTH limits are reported as practically equal:
# repeated runs of the same position differ by about this much.
EQUAL_WINRATE_PP = 1.0
EQUAL_SCORE_POINTS = 0.5
# Beyond this the win probability saturates, so losses are graded by score only.
LOPSIDED_WINRATE = 90.0
_SCORE_STEPS = (0.5, 1.5, 3.0, 6.0)
_WINRATE_STEPS = (1.0, 4.0, 8.0, 15.0)
_LEVELS = ('equal', 'slight', 'inaccuracy', 'mistake', 'blunder')
_LABELS = {
    'best': ('AI 一选', 'Engine first choice'),
    'equal': ('基本等价', 'Practically equal'),
    'unstable': ('排序不稳', 'Unstable ranking'),
    'slight': ('略亏', 'Slightly worse'),
    'inaccuracy': ('小失误', 'Inaccuracy'),
    'mistake': ('失误', 'Mistake'),
    'blunder': ('大失误', 'Blunder'),
}
_REGIONS = {
    (0, 0): ('左上角', 'upper-left corner'), (1, 0): ('上边', 'upper side'),
    (2, 0): ('右上角', 'upper-right corner'), (0, 1): ('左边', 'left side'),
    (1, 1): ('中腹', 'center'), (2, 1): ('右边', 'right side'),
    (0, 2): ('左下角', 'lower-left corner'), (1, 2): ('下边', 'lower side'),
    (2, 2): ('右下角', 'lower-right corner'),
}
_ORTHOGONAL = ((0, -1), (-1, 0), (1, 0), (0, 1))
_DIAGONAL = ((-1, -1), (1, -1), (-1, 1), (1, 1))


def _bi(zh, en):
    return {"zh": zh, "en": en}


def _color(player):
    return ("黑方", "Black") if player == "B" else ("白方", "White")


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _r(value):
    """Round to the one decimal that the search budget can support."""
    rounded = round(float(value), 1)
    return 0.0 if rounded == 0 else rounded


def _chebyshev(first, second):
    return max(abs(first[0] - second[0]), abs(first[1] - second[1]))


def _local_radius(size):
    return max(3, size // 4 + 1)


def _region(point, size):
    third = size // 3
    column = 0 if point[0] < third else 2 if point[0] >= size - third else 1
    row = 0 if point[1] < third else 2 if point[1] >= size - third else 1
    return _REGIONS[column, row]


def _edge_lines(point, size):
    """Line numbers counted from the nearer vertical and horizontal edge."""
    return min(point[0], size - 1 - point[0]) + 1, min(point[1], size - 1 - point[1]) + 1


def _description(before: Board, player: str, move: str, facts: dict) -> list[dict]:
    zh_color, en_color = _color(player)
    result = []
    if facts["pass"]:
        return [_bi(f"{zh_color}停一手，棋盘上的棋子不变，轮到对方。",
                    f"{en_color} passes; the stones stay unchanged and the opponent takes the turn.")]
    if facts["capturedCount"]:
        points = ", ".join(facts["captured"])
        result.append(_bi(f"{move} 直接提掉对方 {facts['capturedCount']} 颗棋子（{points}），使这些交叉点重新变为空点。",
                          f"{move} immediately captures {facts['capturedCount']} opposing stones ({points}), freeing those intersections."))
    if facts["connectedGroups"]:
        result.append(_bi(f"{move} 粘住原先分开的 {facts['connectedGroups']} 块己方棋子，直接连成一块；连接后共 {facts['moveGroupLibertiesAfter']} 口气。",
                          f"{move} joins {facts['connectedGroups']} previously separate friendly chains into one chain with {facts['moveGroupLibertiesAfter']} liberties."))
    if facts["rescuedAtariGroups"]:
        anchors = ", ".join(group[0] for group in facts["rescuedAtariGroups"])
        result.append(_bi(f"原先在 {anchors} 的己方棋块处于打吃、只有一口气；{move} 后连接棋块有 {facts['moveGroupLibertiesAfter']} 口气，解除当前打吃。",
                          f"The friendly chains at {anchors} had one liberty; after {move}, the joined chain has {facts['moveGroupLibertiesAfter']} liberties, escaping the immediate atari."))
    if facts["createdAtariGroups"]:
        anchors = ", ".join(group[0] for group in facts["createdAtariGroups"])
        result.append(_bi(f"{move} 将对方在 {anchors} 的棋块从多口气压到一口气，形成打吃；对方仍可能逃跑或反击。",
                          f"{move} reduces the opposing chains at {anchors} from multiple liberties to one, giving atari; the opponent may still escape or counterplay."))
    if facts["selfAtari"]:
        result.append(_bi(f"{move} 后本方落子所在棋块仅剩一口气；是否值得这样下，必须结合后续变化判断。",
                          f"The chain containing {move} has only one liberty afterward; whether that is worthwhile depends on the continuation."))
    if facts.get("ko"):
        result.append(_bi(f"此着形成劫，{facts['ko']} 处不能立即回提。",
                          f"This move creates a ko; an immediate recapture at {facts['ko']} is illegal."))
    return result


def _fact_terms(facts):
    ids = []
    if facts.get('capturedCount'):
        ids.append('capture')
    if facts.get('connectedGroups'):
        ids.extend(['connect', 'liberties'])
    if any(facts.get(key) for key in ('createdAtariGroups', 'rescuedAtariGroups', 'selfAtari')):
        ids.extend(['atari', 'liberties'])
    if facts.get('ko'):
        ids.append('ko')
    return ids


def _shape(before, player, move):
    """Name the one local shape that the stones around the move establish.

    Every label is a checkable adjacency relation. The cases are ordered so a
    hane is never also reported as an attachment or a diagonal move. No
    strategic success is inferred.
    """
    point = vertex_to_point(move, before.size)
    if point is None:
        return [], []
    size, cells, enemy = before.size, before.cells, other(player)
    x, y = point

    def name(target):
        return point_to_vertex(target, size)

    def stone(dx, dy, color):
        target = (x + dx, y + dy)
        return target if cells.get(target) == color else None

    def empty(target):
        return 0 <= target[0] < size and 0 <= target[1] < size and target not in cells

    friend_orth = [p for d in _ORTHOGONAL if (p := stone(*d, player))]
    enemy_orth = [p for d in _ORTHOGONAL if (p := stone(*d, enemy))]
    friend_diag = [p for d in _DIAGONAL if (p := stone(*d, player))]
    enemy_diag = [p for d in _DIAGONAL if (p := stone(*d, enemy))]

    # Cut: with a friendly stone on the far corner, the move separates two
    # diagonally placed opposing stones that were not one chain.
    for dx in (-1, 1):
        for dy in (-1, 1):
            first, second, partner = stone(dx, 0, enemy), stone(0, dy, enemy), stone(dx, dy, player)
            if first and second and partner and second not in before._group(first)[0]:
                return [_bi(
                    f"{move} 与己方 {name(partner)} 斜向配合，把对方 {name(first)} 和 {name(second)} 分在两边，是断；这两子落子前不属同一棋块。断下的棋能否吃住，还要算气和征子。",
                    f"{move} works with the friendly stone at {name(partner)} to separate the opposing stones at {name(first)} and {name(second)}: a cut. They were not one chain before the move. Whether a cut-off stone can be captured still requires reading liberties and ladders.")], ['cut']

    if not friend_orth:
        for opponent in enemy_orth:
            for friend in friend_diag:
                if abs(opponent[0] - friend[0]) + abs(opponent[1] - friend[1]) != 1:
                    continue
                shared = [p for p in ((friend[0], y), (x, friend[1])) if p != opponent]
                zh = f"{move} 从己方 {name(friend)} 斜着绕到对方 {name(opponent)} 的侧面，是扳。"
                en = f"{move} bends around the opposing stone at {name(opponent)}, diagonally from the friendly stone at {name(friend)}: a hane."
                if shared and empty(shared[0]):
                    zh += f"扳出的子与 {name(friend)} 之间在 {name(shared[0])} 留有断点，要防对方断。"
                    en += f" The point {name(shared[0])} between the two friendly stones is a cutting point to watch."
                return [_bi(zh, en)], ['hane']

    if friend_orth:
        friend = friend_orth[0]
        if enemy_orth:
            opposite = next((p for p in enemy_orth
                             if p[0] - x == x - friend[0] and p[1] - y == y - friend[1]), None)
            if opposite:
                return [_bi(
                    f"{move} 从己方 {name(friend)} 直线顶到对方 {name(opposite)} 跟前，是顶；己方棋块延长一子，对方这颗子少一口气。",
                    f"{move} pushes in a straight line from the friendly stone at {name(friend)} into the opposing stone at {name(opposite)}; the friendly chain grows by one stone and that opposing stone loses a liberty.")], ['push', 'liberties']
            opponent = enemy_orth[0]
            return [_bi(
                f"{move} 紧接己方 {name(friend)} 长出一子，同时贴住对方 {name(opponent)}；两子直接相连，气数合并。",
                f"{move} extends directly from the friendly stone at {name(friend)} while touching the opposing stone at {name(opponent)}; the stones are solidly connected and share liberties.")], ['extend', 'liberties']
        return [_bi(
            f"{move} 紧接己方 {name(friend)} 长出一子，两子直接相连。",
            f"{move} extends directly from the friendly stone at {name(friend)}; the two stones are solidly connected.")], ['extend']

    if enemy_orth:
        opponent = enemy_orth[0]
        if friend_diag:
            friend = friend_diag[0]
            return [_bi(
                f"{move} 与己方 {name(friend)} 成尖，同时顶住对方 {name(opponent)}，是尖顶的形状；对方如何长出仍需计算。",
                f"{move} is diagonal to the friendly stone at {name(friend)} and touches the opposing stone at {name(opponent)}: a kick shape. The opponent's extension still requires reading.")], ['kick', 'diagonal']
        own_line, opponent_line = min(_edge_lines(point, size)), min(_edge_lines(opponent, size))
        if own_line < opponent_line and own_line <= 3:
            return [_bi(
                f"{move} 从靠边的一侧贴住对方 {name(opponent)}，是托；接触之后如何应对，需要沿实际变化核对。",
                f"{move} touches the opposing stone at {name(opponent)} from the edge side: an attachment underneath. The replies must be checked in the actual continuation.")], ['attach_under']
        return [_bi(
            f"{move} 靠在对方 {name(opponent)} 旁边，两个落点上下或左右紧邻；靠之后如何应对，需要沿实际变化核对。",
            f"{move} attaches beside the opposing stone at {name(opponent)}, sharing a grid edge; the replies must be checked in the actual continuation.")], ['attach']

    if friend_diag:
        friend = friend_diag[0]
        zh = f"{move} 与己方 {name(friend)} 构成尖形，横纵各相距一格；斜邻关系本身不等于直接粘连。"
        en = f"{move} forms a diagonal shape with the friendly stone at {name(friend)}; diagonal adjacency alone is not a solid connection."
        if empty((friend[0], y)) and empty((x, friend[1])):
            zh += "两个连接点目前都空着，对方占一个，己方还能粘另一个。"
            en += " Both connecting points are empty, so if the opponent takes one the other can still be connected."
        return [_bi(zh, en)], ['diagonal']

    for opponent in enemy_diag:
        if min(_edge_lines(point, size)) > min(_edge_lines(opponent, size)) and min(_edge_lines(opponent, size)) >= 3:
            return [_bi(
                f"{move} 落在对方 {name(opponent)} 的斜上方、更靠中腹一路，是肩冲的形状；能否压低对方，要看应手。",
                f"{move} sits diagonally above the opposing stone at {name(opponent)}, one line nearer the center: a shoulder-hit shape. Whether it presses the opponent low depends on the replies.")], ['shoulder_hit']

    for dx, dy in _ORTHOGONAL:
        friend = stone(2 * dx, 2 * dy, player)
        if friend and empty((x + dx, y + dy)):
            return [_bi(
                f"{move} 与己方 {name(friend)} 在同一直线上隔一个空点，是一间跳；中间的空点并未直接连通。",
                f"{move} is a one-space jump from the friendly stone at {name(friend)}; the empty point between them is not a direct connection.")], ['jump']

    def friends_at(first, second):
        return [p for (a, b), color in sorted(cells.items())
                if color == player and sorted((abs(x - a), abs(y - b))) == [first, second]
                for p in [(a, b)]]

    knight = friends_at(1, 2)
    if knight:
        return [_bi(
            f"{move} 与己方 {name(knight[0])} 构成小飞形，横纵距离为一格与两格；能否被切断，要结合对方应手和外围配置判断。",
            f"{move} forms a small knight-move shape with the friendly stone at {name(knight[0])}, offset by one and two grid steps; cutting possibilities depend on replies and surrounding stones.")], ['keima']

    lines = _edge_lines(point, size)
    nearby_friend = any(color == player and _chebyshev(point, p) <= 3 for p, color in cells.items())
    if not nearby_friend and min(lines) in (3, 4):
        kinds = {(1, 2): ('小飞', 'knight-move'), (0, 2): ('一间', 'one-space'),
                 (1, 3): ('大飞', 'large-knight'), (0, 3): ('二间', 'two-space')}
        for (a, b), color in sorted(cells.items(), key=lambda item: _chebyshev(point, item[0])):
            offset = tuple(sorted((abs(x - a), abs(y - b))))
            if color == enemy and offset in kinds and max(_edge_lines((a, b), size)) <= 5:
                height = ('低', 'low') if min(lines) == 3 else ('高', 'high')
                return [_bi(
                    f"{move} 以{kinds[offset][0]}的间隔从{height[0]}位接近对方角上的 {name((a, b))}，是挂角。",
                    f"{move} approaches the opposing corner stone at {name((a, b))} at a {height[1]} {kinds[offset][1]} distance.")], ['approach']

    for dx, dy in _ORTHOGONAL:
        friend = stone(3 * dx, 3 * dy, player)
        if friend and empty((x + dx, y + dy)) and empty((x + 2 * dx, y + 2 * dy)):
            return [_bi(
                f"{move} 与己方 {name(friend)} 在同一直线上隔两个空点，是二间跳；间隔较宽，对方有打入或分断的余地。",
                f"{move} is a two-space jump from the friendly stone at {name(friend)}; the wider gap leaves room for the opponent to invade or separate.")], ['two_space_jump']
    large = friends_at(1, 3)
    if large:
        return [_bi(
            f"{move} 与己方 {name(large[0])} 构成大飞形，横纵距离为一格与三格；步子较大，联络比小飞薄。",
            f"{move} forms a large knight-move shape with the friendly stone at {name(large[0])}, offset by one and three grid steps; it covers more ground but links more thinly than a small knight move.")], ['large_knight']

    if size >= 13 and max(lines) <= 5 and not any(_chebyshev(point, p) <= 5 for p in cells):
        corner = {(4, 4): ('星位', 'star point', 'star_point'), (3, 4): ('小目', '3-4 point', 'komoku'),
                  (3, 3): ('三三', '3-3 point', None), (3, 5): ('目外', '3-5 point', None),
                  (4, 5): ('高目', '4-5 point', None)}.get(tuple(sorted(lines)))
        zh_region, en_region = _region(point, size)
        if corner:
            return [_bi(f"{move} 占据{zh_region}的{corner[0]}，这个角此前还没有棋子。",
                        f"{move} takes the {corner[1]} in the empty {en_region}.")], [corner[2]] if corner[2] else []
    return [], []


def _location(before: Board, player: str, move: str):
    point = vertex_to_point(move, before.size)
    if point is None:
        return None, None
    x, y = point
    edge_distances = [(y, "上边", "upper side"), (before.size - 1 - y, "下边", "lower side"),
                      (x, "左边", "left side"), (before.size - 1 - x, "右边", "right side")]
    distance, zh_side, en_side = min(edge_distances, key=lambda item: item[0])
    friendly = sorted(((abs(x - a) + abs(y - b), point_to_vertex((a, b), before.size))
                       for (a, b), color in before.cells.items() if color == player), key=lambda item: (item[0], item[1]))
    enemy = sorted(((abs(x - a) + abs(y - b), point_to_vertex((a, b), before.size))
                    for (a, b), color in before.cells.items() if color != player), key=lambda item: (item[0], item[1]))
    en = f"{move} lies on line {distance + 1} from the {en_side}."
    zh = f"{move} 位于{zh_side}起第 {distance + 1} 路。"
    if enemy and enemy[0][0] == 1:
        zh += f" 此着紧贴对方 {enemy[0][1]}。"
        en += f" It touches the opposing stone at {enemy[0][1]}."
    interpretation = None
    if 1 <= distance <= 3 and friendly:
        nearby = [vertex for dist, vertex in friendly if dist <= 8][:2]
        if nearby:
            anchors = "、".join(nearby)
            interpretation = _bi(
                f"从落点与现有 {anchors} 的关系看，可以把它理解为沿{zh_side}布置下一颗棋子、发展这一侧的局部。这是位置上的解释；是否获得实地或形成有效连接，需要看对方应手及后续变化。",
                f"Relative to the existing stones at {', '.join(nearby)}, this can be read as developing the local position along the {en_side}. This is a positional interpretation; territory gains or an effective connection depend on the opponent's replies and the continuation.",
            )
    return _bi(zh, en), interpretation


def _replay_branch(before: Board, player: str, branch: dict, fallback_pv=None):
    steps = [step for step in (branch.get("steps") or [])
             if not (step.get("ply") == 0 and step.get("move") is None)]
    if not steps and fallback_pv:
        steps = [{"ply": i + 1, "player": player if i % 2 == 0 else other(player), "move": move}
                 for i, move in enumerate(fallback_pv)]
    board = before.copy()
    replayed, error = [], None
    for i, step in enumerate(steps[:16]):
        try:
            actor = step.get("player", board.to_play)
            move = step["move"]
            position_before = board.copy()
            facts = board.play(actor, move)
        except (BoardError, KeyError, TypeError) as exc:
            error = str(exc)
            break
        ply = step.get("ply", i + 1)
        replayed.append({"ply": ply if isinstance(ply, int) and ply > 0 else i + 1,
                         "player": actor, "move": facts["move"],
                         "facts": facts, "before": position_before, "eval": step.get("eval")})
    return replayed, error


def _grade(loss_points, loss_pp, base_winrate):
    """Coarse tier for how much worse a move is than the engine's choice."""
    lopsided = _number(base_winrate) and not (100 - LOPSIDED_WINRATE < base_winrate < LOPSIDED_WINRATE)
    score_rank = sum(1 for step in _SCORE_STEPS if loss_points >= step)
    rate_rank = 0 if lopsided else sum(1 for step in _WINRATE_STEPS if loss_pp >= step)
    return _LEVELS[max(score_rank, rate_rank)], lopsided


def _verdict(move, player, analysis, replayed):
    """One search-based sentence that answers 'was this a good move?' first."""
    selected = analysis.get("selected") or {}
    alternative = analysis.get("alternative") or {}
    ai_move, actual_move = analysis.get("ai_move"), analysis.get("actual_move")
    is_ai = bool(ai_move) and str(ai_move).lower() == move.lower()
    numbers = [selected.get("winrate"), alternative.get("winrate"),
               selected.get("score_lead"), alternative.get("score_lead")]
    alt_move = alternative.get("move")
    if not alt_move or not all(_number(value) for value in numbers):
        if is_ai:
            return {"level": "best", "label": _bi(*_LABELS["best"]),
                    "text": _bi(f"{move} 是本次根搜索的一选。", f"{move} ranked first in this root search.")}
        return None
    delta_pp = _r(selected["winrate"] - alternative["winrate"])
    delta_points = _r(selected["score_lead"] - alternative["score_lead"])
    zh_gap = f"胜率 {delta_pp:+.1f} 个百分点、目差 {delta_points:+.1f} 目"
    en_gap = f"{delta_pp:+.1f} percentage points of win probability and {delta_points:+.1f} points of score"
    equal = abs(delta_pp) < EQUAL_WINRATE_PP and abs(delta_points) < EQUAL_SCORE_POINTS
    base_rate = (analysis.get("base_eval") or {}).get("winrate")
    zh_opponent, en_opponent = _color(other(player))

    def result(level, zh, en, **extra):
        return {"level": level, "label": _bi(*_LABELS[level]), "text": _bi(zh, en),
                "winrate_pp": delta_pp, "score_points": delta_points, "compared_with": alt_move, **extra}

    if is_ai:
        played = bool(actual_move) and str(actual_move).lower() == str(alt_move).lower()
        zh_alt = f"实战的 {alt_move} " if played else f"另一候选 {alt_move} "
        en_alt = f"the game move {alt_move}" if played else f"the other candidate {alt_move}"
        if equal:
            return result("equal",
                          f"{move} 是本次根搜索的一选，但与{zh_alt}基本等价：补搜的差距只有{zh_gap}，在搜索波动范围内，两手都可下。",
                          f"{move} ranked first in the root search, but it is practically equal to {en_alt}: the re-search differs by only {en_gap}, within search noise. Both moves are playable.")
        level, _ = _grade(-delta_points, -delta_pp, base_rate)
        if level != "equal":
            return result("unstable",
                          f"{move} 是本次根搜索的一选，但补搜后{zh_alt}的评估反而更高（{move} 相比之下：{zh_gap}）。一选的排序在当前搜索预算下并不稳固，两手都值得考虑。",
                          f"{move} ranked first in the root search, yet the re-search rates {en_alt} higher ({move} by comparison: {en_gap}). The ranking is not stable at this search budget; consider both moves.")
        return result("best",
                      f"{move} 是本次搜索的一选。与{zh_alt}相比：{zh_gap}。",
                      f"{move} is the first choice of this search. Compared with {en_alt}: {en_gap}.")

    is_reference = bool(ai_move) and str(ai_move).lower() == str(alt_move).lower()
    zh_alt = f" AI 一选 {alt_move} " if is_reference else f"另一候选 {alt_move} "
    en_alt = f"the engine's first choice {alt_move}" if is_reference else f"the other candidate {alt_move}"
    level, lopsided = _grade(-delta_points, -delta_pp, base_rate)
    if equal:
        return result("equal",
                      f"{move} 与{zh_alt}基本等价：补搜的差距只有{zh_gap}，在搜索波动范围内，这手可下。",
                      f"{move} is practically equal to {en_alt}: the re-search differs by only {en_gap}, within search noise. The move is playable.")
    if level == "equal":
        return result("equal",
                      f"补搜后 {move} 的评估不低于{zh_alt.rstrip()}（{zh_gap}），这手可下；一选的排序在当前搜索预算下并不稳固。",
                      f"After the re-search, {move} is rated no lower than {en_alt} ({en_gap}). The move is playable; the ranking is not stable at this search budget.")
    zh_label, en_label = _LABELS[level]
    zh = f"{zh_label}：按本次搜索，{move} 不如{zh_alt.rstrip()}（{zh_gap}）。"
    en = f"{en_label}: in this search, {move} is worse than {en_alt} ({en_gap})."
    if len(replayed) > 1 and replayed[1]["player"] == other(player) and replayed[1]["move"] != "pass":
        zh += f"搜索预计{zh_opponent}的下一手是 {replayed[1]['move']}。"
        en += f" The search expects {en_opponent} to continue at {replayed[1]['move']}."
    if lopsided:
        zh += "局面优劣已经悬殊，胜率变化不敏感，这里按目差分档。"
        en += " The game is already lopsided, so the tier is based on score rather than win probability."
    return result(level, zh, en, lopsided=bool(lopsided))


def _close_candidates(analysis):
    """Root-search moves whose gap to the first choice is inside search noise."""
    ranked = [entry for entry in (analysis.get("root_ranked") or [])
              if isinstance(entry, dict) and all(_number(entry.get(key)) for key in ("order", "visits", "winrate", "score_lead"))]
    first = next((entry for entry in ranked if entry["order"] == 0), None)
    if not first:
        return None
    close = [entry["move"] for entry in sorted(ranked, key=lambda entry: entry["order"])
             if entry["order"] > 0 and entry["visits"] >= max(8, .1 * first["visits"])
             and abs(entry["winrate"] - first["winrate"]) < EQUAL_WINRATE_PP
             and abs(entry["score_lead"] - first["score_lead"]) < EQUAL_SCORE_POINTS][:3]
    if not close:
        return None
    zh_moves, en_moves = "、".join(close), ", ".join(close)
    return {"id": "close-candidates", "level": "search", "text": _bi(
        f"根搜索里 {zh_moves} 与一选 {first['move']} 的差距不到 {EQUAL_WINRATE_PP:g} 个百分点、{EQUAL_SCORE_POINTS:g} 目，在搜索波动范围内。可以把它们看成同一档的选择；谁排第一会随搜索次数变化。",
        f"In the root search, {en_moves} trail the first choice {first['move']} by less than {EQUAL_WINRATE_PP:g} percentage point and {EQUAL_SCORE_POINTS:g} points, inside search noise. Treat them as one tier; which ranks first changes with the visit count.")}


def _tenuki_reasons(before, player, move, analysis):
    """Counterfactual passes: what the move is worth and whether it must be answered."""
    tenuki = analysis.get("tenuki") or {}
    selected = analysis.get("selected") or {}
    point = vertex_to_point(move, before.size)
    if point is None:
        return [], []
    reasons, ids = [], []
    zh_color, en_color = _color(player)
    zh_opponent, en_opponent = _color(other(player))
    radius = _local_radius(before.size)

    def where(vertex):
        try:
            target = vertex_to_point(vertex, before.size)
        except BoardError:
            return None, None
        if target is None:
            return None, None
        return _chebyshev(point, target) <= radius, _region(target, before.size)

    skipped = tenuki.get("pass") or {}
    skipped_eval = skipped.get("eval") or {}
    if all(_number(value) for value in (selected.get("winrate"), selected.get("score_lead"),
                                        skipped_eval.get("winrate"), skipped_eval.get("score_lead"))):
        value_points = _r(selected["score_lead"] - skipped_eval["score_lead"])
        value_pp = _r(selected["winrate"] - skipped_eval["winrate"])
        zh = (f"脱先对比：{zh_color}这手如果不下（假设停一手），本次搜索的评估是胜率 {_r(skipped_eval['winrate']):.1f}%、目差 {_r(skipped_eval['score_lead']):+.1f}；"
              f"下 {move} 后是 {_r(selected['winrate']):.1f}%、{_r(selected['score_lead']):+.1f}。")
        en = (f"Tenuki comparison: if {en_color} did not play here (a hypothetical pass), this search gives {_r(skipped_eval['winrate']):.1f}% and a score lead of {_r(skipped_eval['score_lead']):+.1f}; "
              f"after {move} it gives {_r(selected['winrate']):.1f}% and {_r(selected['score_lead']):+.1f}.")
        if value_points > 0:
            zh += f"按这次搜索，这手棋约值 {value_points:.1f} 目（胜率 {value_pp:+.1f} 个百分点）。"
            en += f" In this search the move is worth about {value_points:.1f} points ({value_pp:+.1f} percentage points)."
        else:
            zh += f"按这次搜索，这手并不比停一手好（目差 {value_points:+.1f}）。"
            en += f" In this search the move is no better than passing ({value_points:+.1f} points)."
        reply = skipped.get("reply")
        if isinstance(reply, str) and reply.lower() != "pass":
            local, region = where(reply)
            if reply.upper() == move.upper():
                zh += f"而且{zh_color}不下时，搜索给{zh_opponent}的第一选择正是 {move} 这一点：这里是双方都想先下的地方。"
                en += f" If {en_color} does not play it, the search's first choice for {en_opponent} is this same point: both sides want it."
            elif local:
                zh += f"{zh_color}不下时，搜索给{zh_opponent}的第一选择是同一局部的 {reply}，说明这一带对双方都要紧。"
                en += f" If {en_color} plays elsewhere, the search's first choice for {en_opponent} is {reply} in the same area, so this area matters to both sides."
            elif region:
                zh += f"{zh_color}不下时，搜索给{zh_opponent}的第一选择是别处的 {reply}（{region[0]}），没有显示这个局部必须马上处理。"
                en += f" If {en_color} plays elsewhere, the search's first choice for {en_opponent} is {reply} in the {region[1]}, so this area does not look urgent."
        zh += "停一手只是用来衡量价值的假设，不是实战选项。"
        en += " The pass is only a measuring device, not a practical option."
        reasons.append({"id": "move-value", "level": "search", "ply": 1, "text": _bi(zh, en)})
        ids.append("tenuki")

    ignored = tenuki.get("ignored") or {}
    ignored_eval = ignored.get("eval") or {}
    followup = ignored.get("followup")
    if (isinstance(followup, str) and followup.lower() != "pass"
            and all(_number(value) for value in (selected.get("winrate"), selected.get("score_lead"),
                                                 ignored_eval.get("winrate"), ignored_eval.get("score_lead")))):
        local, region = where(followup)
        gain_points = _r(ignored_eval["score_lead"] - selected["score_lead"])
        gain_pp = _r(ignored_eval["winrate"] - selected["winrate"])
        if local:
            reasons.append({"id": "followup-if-ignored", "level": "search", "ply": 1, "text": _bi(
                f"后续手段：{move} 之后如果{zh_opponent}脱先不应，搜索给{zh_color}的下一手是同一局部的 {followup}，评估再变化 {gain_points:+.1f} 目、{gain_pp:+.1f} 个百分点。全盘最大的一手就在这里，说明这手留有后续，{zh_opponent}多半需要应一手（接近先手）；是否真是先手，仍要看{zh_opponent}实际怎么应。",
                f"Follow-up: if {en_opponent} ignores {move}, the search's next move for {en_color} is {followup} in the same area, changing the evaluation by {gain_points:+.1f} points and {gain_pp:+.1f} percentage points. The biggest move on the board is right here, so the move leaves a follow-up and {en_opponent} will probably need to answer (close to sente); whether it really is sente depends on the actual reply.")})
            ids.append("sente")
        elif region:
            reasons.append({"id": "followup-if-ignored", "level": "search", "ply": 1, "text": _bi(
                f"后续手段：{move} 之后即使{zh_opponent}脱先，搜索给{zh_color}的下一手也是别处的 {followup}（{region[0]}）。没有显示这手在局部留下必须马上兑现的后续，{zh_opponent}可以考虑脱先（这手偏后手）。",
                f"Follow-up: even if {en_opponent} ignores {move}, the search's next move for {en_color} is {followup} in the {region[1]}. No urgent local follow-up is shown, so {en_opponent} may play elsewhere (the move leans gote).")})
            ids.append("gote")
        ids.append("tenuki")
    return reasons, ids


def _ownership_reasons(before, player, move, selected, alternative):
    """Summarise where the two candidates' ownership predictions differ.

    Raw ownership is Black-oriented. Sums are converted once to the explained
    player's perspective; group means use each group owner's perspective.
    These are network estimates, never territory counts or life/death verdicts.
    """
    first, second = selected.get("ownership"), alternative.get("ownership")
    size = before.size
    if not (isinstance(first, list) and isinstance(second, list) and len(first) == len(second) == size ** 2):
        return []
    if not all(_number(value) for value in first) or not all(_number(value) for value in second):
        return []
    sign = 1 if player == "B" else -1
    alt_move = alternative.get("move", "?")
    zh_color, en_color = _color(player)
    try:
        centers = [vertex_to_point(vertex, size) for vertex in (move, alt_move)]
    except BoardError:
        return []
    centers = [center for center in centers if center is not None]
    if not centers:
        return []
    # Far from both candidates the two searches simply spend their free moves
    # in different places, so only the neighbourhoods of the moves are compared.
    radius = _local_radius(size) + 1
    together = len(centers) == 1 or _chebyshev(centers[0], centers[1]) <= radius
    windows = [centers] if together else [[center] for center in centers]

    def shift(window):
        return sum(sign * (first[b * size + a] - second[b * size + a])
                   for b in range(size) for a in range(size)
                   if any(_chebyshev((a, b), center) <= radius for center in window))

    parts_zh, parts_en = [], []
    for window, vertex in zip(windows, (move, alt_move)):
        amount = shift(window)
        if abs(amount) < .5:
            continue
        zh_region, en_region = _region(window[0], size)
        zh_way, en_way = ("多", "toward") if amount > 0 else ("少", "away from")
        parts_zh.append(f"{vertex} 周围（{zh_region}）合计对{zh_color}{zh_way}约 {abs(_r(amount)):.1f} 目")
        parts_en.append(f"around {vertex} ({en_region}) it shifts about {abs(_r(amount)):.1f} points of predicted ownership {en_way} {en_color}")
    reasons = []
    total = sum(sign * (one - two) for one, two in zip(first, second))
    if parts_zh:
        reasons.append({"id": "ownership-clue", "level": "search", "text": _bi(
            f"归属预测汇总：下 {move} 与下 {alt_move} 相比，" + "；".join(parts_zh) + f"（全盘合计 {_r(total):+.1f} 目，局部的出入可能在别处找回）。这是网络对最终归属的估计，可提示两手的差别主要落在哪里，不等于确定的实地或死活结论。",
            f"Ownership summary: compared with {alt_move}, playing {move} changes the local prediction: " + "; ".join(parts_en) + f" (whole board {_r(total):+.1f}; a local swing may be recovered elsewhere). This is the network's estimate of final ownership; it shows where the two moves differ, not a territory count or a life-and-death verdict.")})
    best = None
    for group in before.groups():
        points = [vertex_to_point(vertex, size) for vertex in group["stones"]]
        if not any(_chebyshev(point, center) <= radius for point in points for center in centers):
            continue
        indexes = [b * size + a for a, b in points]
        owner_sign = 1 if group["player"] == "B" else -1
        after_selected = owner_sign * sum(first[i] for i in indexes) / len(indexes)
        after_alternative = owner_sign * sum(second[i] for i in indexes) / len(indexes)
        change = abs(after_selected - after_alternative)
        if change >= .4 and (best is None or change > best[0]):
            best = (change, group, after_selected, after_alternative)
    if best:
        _, group, after_selected, after_alternative = best
        zh_owner, en_owner = _color(group["player"])
        anchor, count = group["stones"][0], len(group["stones"])
        reasons.append({"id": "ownership-group", "level": "search", "text": _bi(
            f"棋块安危线索：{zh_owner} {anchor} 所在的棋块（{count} 子），下 {move} 后归属预测均值为 {after_selected:+.2f}，下 {alt_move} 后为 {after_alternative:+.2f}（+1 表示稳属{zh_owner}，−1 表示多半被吃）。这块棋的处境是两手差别的线索之一，不是死活结论。",
            f"Group-safety clue: for the {en_owner} chain containing {anchor} ({count} stones), mean predicted ownership is {after_selected:+.2f} after {move} and {after_alternative:+.2f} after {alt_move} (+1 means safely {en_owner}'s, −1 means probably captured). The fate of this chain is one clue to the difference, not a life-and-death verdict.")})
    return reasons


def generate_explanation(before: Board, player: str, move: str, analysis: dict, pv=None, *, history=None) -> dict:
    """Return the bilingual public schema used by the local UI.

    `analysis` candidate metrics must use the original actor's perspective:
    winrate in percent, score_lead in points. Ownership stays raw Black-oriented.
    Branches contain an entire PV including its first move. Optional keys
    `actual_move`, `base_eval`, `root_ranked` and `tenuki` add the verdict tier,
    close-candidate and pass-comparison evidence when the service supplies them.
    """
    next_board = before.copy()
    facts = next_board.play(player, move)
    move = facts["move"]
    limitations = []
    reference_reasons, shape_reasons, search_reasons, line_reasons, place_reasons = [], [], [], [], []
    continuation = []
    immediate = _description(before, player, move, facts)
    term_ids = _fact_terms(facts)
    joseki = find_joseki(before, player, move, history=history)
    for match in joseki:
        term_ids.extend(match.get('term_ids', []))
        if match.get('move_explanation'):
            reference_reasons.append({'id': f"joseki-role-{match['id']}", 'level': 'reference',
                                      'text': match['move_explanation'], 'ply': 1})
    # A matched joseki role already names the shape; a second generic label
    # for the same stones would only risk contradicting it.
    shapes, shape_terms = _shape(before, player, move) if not immediate and not joseki else ([], [])
    term_ids.extend(shape_terms)
    for index, description in enumerate(shapes):
        shape_reasons.append({'id': f'move-shape-{index}', 'level': 'board', 'text': description, 'ply': 1})
    for index, description in enumerate(immediate):
        shape_reasons.append({"id": f"immediate-{index}", "level": "board", "text": description, "ply": 1})
    if facts["capturedCount"]:
        captured_chains = {}
        for vertex in facts["captured"]:
            chain = before.group_at(vertex)
            if chain:
                captured_chains[tuple(chain["stones"])] = chain
        if captured_chains and all(chain["libertyCount"] == 1 for chain in captured_chains.values()):
            shape_reasons.append({"id": "capture-urgency", "level": "board", "ply": 1, "text": _bi(
                "被提掉的棋块在落子前已经处于打吃、只有一口气；这手完成当前提子。是否应立即兑现这一收获，还要对照其他候选及对方的后续应手。",
                "The captured chains were already in atari with one liberty before this move; the move completes the immediate capture. Whether to take that gain now still requires comparison with other choices and the opponent's continuations.")})
    location, interpretation = _location(before, player, move)
    if location:
        place_reasons.append({"id": "location", "level": "board", "text": location, "ply": 1})
    if interpretation and not immediate:
        place_reasons.append({"id": "positional-reading", "level": "tentative", "text": interpretation, "ply": 1})

    selected = analysis.get("selected") or {}
    alternative = analysis.get("alternative") or {}
    comparison = analysis.get("comparison") or {}
    selected_rate, alternative_rate = selected.get("winrate"), alternative.get("winrate")
    selected_lead, alternative_lead = selected.get("score_lead"), alternative.get("score_lead")
    delta_rate, delta_lead = comparison.get("winrate_pp"), comparison.get("score_points")
    if not _number(delta_rate) and _number(selected_rate) and _number(alternative_rate):
        delta_rate = selected_rate - alternative_rate
    if not _number(delta_lead) and _number(selected_lead) and _number(alternative_lead):
        delta_lead = selected_lead - alternative_lead
    zh_color, en_color = _color(player)
    if alternative and _number(delta_rate) and _number(delta_lead):
        alt_move = alternative.get("move", "?")
        shown_rate, shown_lead = _r(delta_rate), _r(delta_lead)
        if abs(shown_rate) < EQUAL_WINRATE_PP and abs(shown_lead) < EQUAL_SCORE_POINTS:
            zh_tail = "两项差距都在搜索波动范围内，可视为基本等价。"
            en_tail = "Both gaps are inside search noise, so the two moves are practically equal."
        else:
            zh_tail = "它说明搜索如何评价两个选择，不能单独证明某条棋理是差距的原因。"
            en_tail = "This reports the search comparison; it does not by itself prove a Go explanation caused the difference."
        search_reasons.append({"id": "candidate-comparison", "level": "search", "text": _bi(
            f"候选补搜：{move} 相比 {alt_move}，{zh_color}胜率 {shown_rate:+.1f} 个百分点，预计目差 {shown_lead:+.1f} 目。{zh_tail}",
            f"Candidate re-search: {move} versus {alt_move} changes {en_color}'s win probability by {shown_rate:+.1f} percentage points and expected score lead by {shown_lead:+.1f} points. {en_tail}")})
    if analysis.get("ai_move") and str(analysis["ai_move"]).lower() == move.lower():
        search_reasons.append({"id": "engine-choice", "level": "search", "text": _bi(
            f"{move} 是这次初始搜索排序的第一选择。排序受搜索预算和引擎综合评价影响；不能把“第一选择”理解为已穷尽所有变化的唯一正确答案。",
            f"{move} ranked first in the initial search. Ranking depends on the search budget and the engine's combined evaluation; it is not a proof that every continuation was exhausted or that only one move is correct.")})
    elif (facts["capturedCount"] and alternative.get("move") == analysis.get("ai_move")
          and _number(delta_rate) and _number(delta_lead) and delta_rate < 0 and delta_lead < 0):
        search_reasons.append({"id": "capture-versus-engine-choice", "level": "search", "text": _bi(
            f"{move} 的提子是可验证的局部收获，但本次初始搜索的一选是 {alternative['move']}，候选补搜的胜率与预计目差也都偏向 {alternative['move']}。因此，“能提子”本身不足以说明应优先下这里；需要把这项收获和另一条变化中的机会一并比较。这是本次有限搜索的判断，不把实战着法直接判成错误。",
            f"The capture at {move} is a verified local gain, but the initial search chose {alternative['move']}, and the candidate re-search favors it in both win probability and expected score lead. Capturing alone does not establish priority: compare that gain with the opportunities in the other line. This is a finite-search judgment, not an automatic verdict that the recorded move is a mistake.")})
    close = _close_candidates(analysis)
    if close:
        search_reasons.append(close)
    tenuki_reasons, tenuki_terms = _tenuki_reasons(before, player, move, analysis)
    search_reasons.extend(tenuki_reasons)
    term_ids.extend(tenuki_terms)
    ownership_reasons = _ownership_reasons(before, player, move, selected, alternative) if alternative else []

    branches = analysis.get("branches") or []
    selected_branch = next((branch for branch in branches if branch.get("id") == "selected" or branch.get("selected")), {})
    if not selected_branch and branches:
        selected_branch = branches[0]
    replayed, replay_error = _replay_branch(before, player, selected_branch, pv)
    replay_history = list(history) if isinstance(history, (list, tuple)) else history
    radius = _local_radius(before.size)
    anchors, left_area = [], False
    for step in replayed:
        ply, actor, vertex, step_facts = step["ply"], step["player"], step["move"], step["facts"]
        term_ids.extend(_fact_terms(step_facts))
        zh_actor, en_actor = _color(actor)
        point = vertex_to_point(vertex, before.size)
        far = bool(point is not None and anchors and min(_chebyshev(point, anchor) for anchor in anchors) > radius)
        step_details = _description(step["before"], actor, vertex, step_facts)
        if not step_details and far:
            zh_region, en_region = _region(point, before.size)
            if not left_area:
                left_area = True
                term_ids.append('tenuki')
                step_details = [_bi(f"脱先：离开此前的局部，转向{zh_region}。",
                                    f"Tenuki: leaves the earlier local area for the {en_region}.")]
                if ply == 2:
                    line_reasons.append({"id": "tenuki-in-line", "level": "search", "ply": ply, "text": _bi(
                        f"在所示变化里，{zh_actor}没有在局部应这手，而是直接脱先到{zh_region}的 {vertex}：搜索不认为 {move} 必须马上应对。",
                        f"In the shown line, {en_actor} does not answer locally and plays {vertex} in the {en_region} instead: the search does not treat {move} as requiring an immediate reply.")})
                else:
                    line_reasons.append({"id": "tenuki-in-line", "level": "search", "ply": ply, "text": _bi(
                        f"在所示变化里，第 {ply} 手{zh_actor}脱先到{zh_region}的 {vertex}：搜索认为原来的局部走到第 {ply - 1} 手可以暂告一段落。",
                        f"In the shown line, {en_actor} plays elsewhere at ply {ply} ({vertex}, {en_region}): the search treats the original local exchange as settled for now after ply {ply - 1}.")})
            else:
                step_details = [_bi(f"落在{zh_region}，仍在别处。", f"Plays in the {en_region}, still away from the original area.")]
        elif not step_details:
            step_shapes, step_terms = _shape(step["before"], actor, vertex)
            if step_shapes and ply > 1:
                term_ids.extend(step_terms)
            detail = step_shapes[0] if step_shapes else _location(step["before"], actor, vertex)[0]
            step_details = [detail] if detail else []
        if point is not None:
            anchors.append(point)
        zh = f"变化第 {ply} 手：{zh_actor} {vertex}。"
        en = f"Continuation ply {ply}: {en_actor} {vertex}."
        if step_details:
            zh += " " + step_details[0]["zh"]
            en += " " + step_details[0]["en"]
        if ply > 1:
            references = find_joseki(step['before'], actor, vertex, history=replay_history)
            if references:
                reference = references[0]
                term_ids.extend(reference.get('term_ids', []))
                role, purpose = reference['move_role'], reference['move_explanation']
                zh += f" 定式参考中，本手为「{role['zh']}」。{purpose['zh']}"
                en += f" In the joseki reference, this move is {role['en'].lower()}. {purpose['en']}"
                reference_reasons.append({'id': f'continuation-reference-{ply}', 'level': 'reference',
                                          'ply': ply, 'text': purpose})
        if isinstance(replay_history, list):
            replay_history.append((actor, vertex))
        evaluation = step.get("eval") or {}
        if _number(evaluation.get("winrate")):
            zh += f" 此局面重新分析的{zh_color}胜率为 {_r(evaluation['winrate']):.1f}%。"
            en += f" Re-analysis of this position gives {en_color} a {_r(evaluation['winrate']):.1f}% win probability."
        continuation.append(_bi(zh, en))
        if ply > 1 and any(step_facts.get(key) for key in ("capturedCount", "connectedGroups", "rescuedAtariGroups", "createdAtariGroups")):
            line_reasons.append({"id": f"continuation-fact-{ply}", "level": "board", "ply": ply, "text": _bi(
                f"在所示变化的第 {ply} 手，{step_details[0]['zh']} 这是在这条具体应对序列中可重放验证的效果。",
                f"At ply {ply} of the shown line, {step_details[0]['en']} This effect can be verified by replaying this particular sequence.")})
    reply_reasons = []
    if len(replayed) > 1:
        response = replayed[1]
        reply_zh, reply_en = _color(response["player"])
        reply_reasons.append({"id": "anticipated-reply", "level": "search", "ply": 2, "text": _bi(
            f"KataGo 的这条主要变化首先预计{reply_zh}应在 {response['move']}；逐手演示展示的是在这一应手下局面如何推进。对方换应手时，应重新分析。",
            f"This principal variation first anticipates {reply_en} replying at {response['move']}. The replay shows how the position develops under that reply; a different reply requires fresh analysis.")})
    alternative_branch = next((branch for branch in branches if branch.get("id") == "alternative"), None)
    if alternative_branch:
        alternate_steps, _ = _replay_branch(before, player, alternative_branch)
        if len(alternate_steps) > 1:
            reply_reasons.append({"id": "alternative-reply", "level": "search", "text": _bi(
                f"若改下 {alternate_steps[0]['move']}，对应变化预计下一手为 {alternate_steps[1]['move']}。可切换分支，对照同一初始局面下两条演变，避免把不同应手的效果混在一起。",
                f"After the alternative {alternate_steps[0]['move']}, its line anticipates {alternate_steps[1]['move']} next. Switch branches to compare both developments from the same initial position.")})
        # Compare the *first* occupation of the other candidate's point. A later
        # recapture must not be misreported as the opponent getting there first.
        if (replayed and alternate_steps and replayed[0]["player"] == player
                and alternate_steps[0]["player"] == player and replayed[0]["move"] == move
                and alternate_steps[0]["move"] == alternative.get("move")
                and move != alternate_steps[0]["move"]
                and "pass" not in (move, alternate_steps[0]["move"])):
            for deferred_line, occupied_line in ((replayed, alternate_steps), (alternate_steps, replayed)):
                deferred_move, occupied_move = deferred_line[0]["move"], occupied_line[0]["move"]
                first_occupation = next((step for step in deferred_line[1:] if step["move"] == occupied_move), None)
                if first_occupation and first_occupation["player"] == other(player):
                    opponent_zh, opponent_en = _color(other(player))
                    capture_line = next((line for line in (replayed, alternate_steps)
                                         if line[0]["facts"]["capturedCount"]), None)
                    tradeoff_zh = (f"这里可对照 {capture_line[0]['move']} 的当前提子与 {occupied_move} 的先占顺序。"
                                   if capture_line else f"两条路线显示了 {occupied_move} 的先占顺序不同。")
                    tradeoff_en = (f"The tradeoff includes the immediate capture at {capture_line[0]['move']} and who occupies {occupied_move} first."
                                   if capture_line else f"The lines differ in who occupies {occupied_move} first.")
                    reply_reasons.append({"id": "opportunity-order", "level": "search", "text": _bi(
                        f"在所示搜索路线里，选择 {deferred_move} 后，{opponent_zh}在变化第 {first_occupation['ply']} 手先在 {occupied_move} 落子；改下 {occupied_move} 则{zh_color}先占据这一点。{tradeoff_zh}这只说明这两条具体变化的差别，不保证对方必然这样应，也不据此推断先手或实地收益。",
                        f"In the shown search line, choosing {deferred_move} lets {opponent_en} occupy {occupied_move} first at ply {first_occupation['ply']}; choosing {occupied_move} instead lets {en_color} take that point first. {tradeoff_en} This describes these two particular lines, not a forced reply, a sente claim, or a territory gain.")})
                    break

    verdict = _verdict(move, player, analysis, replayed)
    limitations.extend([
        _bi("本讲解由棋盘规则与搜索数据生成；位置性的解读单独标为推测，没有语言模型补写未经验证的棋理。",
            "This explanation is generated from board rules and search data. Positional interpretations are labeled tentative; no language model adds unverified Go claims."),
        _bi("主要变化是搜索给出的示例路径，并不证明对方每一步都必须这样下；换应手后胜率和局面会改变。",
            "The principal variation is an illustrative search line, not proof that every opponent reply is forced. Other replies can change the evaluation and position."),
        _bi("胜率是引擎对给定规则、贴目和搜索预算的估计；小差距可能随追加搜索改变。每步重新分析的胜率不一定单调。",
            "Win probability is an engine estimate for the given rules, komi, and search budget. Small differences may change with more search; per-position re-analysis need not be monotonic."),
    ])
    if verdict and verdict["level"] != "best":
        limitations.append(_bi(
            f"“基本等价”指补搜差距同时小于 {EQUAL_WINRATE_PP:g} 个百分点和 {EQUAL_SCORE_POINTS:g} 目；略亏、小失误、失误、大失误是按本次有限搜索的差距划分的粗略档位，加大搜索后可能变化。",
            f"“Practically equal” means the re-search gap is below both {EQUAL_WINRATE_PP:g} percentage point and {EQUAL_SCORE_POINTS:g} points. The tiers from slightly worse to blunder are coarse bands for this finite search and may change with more visits."))
    if tenuki_reasons:
        limitations.append(_bi(
            "脱先对比用“假设停一手”的局面重新搜索得到；它衡量这手棋的分量与后续手段，不代表实战中应当停一手，也不是先后手的证明。",
            "The tenuki comparison re-searches hypothetical pass positions. It gauges the move's size and follow-up; it does not recommend passing and does not prove sente or gote."))
    if replay_error:
        limitations.append(_bi("变化遇到非法着法，已停止展示，后续步骤未用于讲解。",
                               "Replay stopped at an illegal move; later steps were excluded from the explanation."))
    if joseki:
        role = joseki[0]['move_role']
        description = _bi(
            f"从定式参考棋形看，{move} 是「{role['zh']}」这一步。本局是否应优先这样下，仍要结合候选补搜、对方应手与全盘配置判断。",
            f"In the reference corner pattern, {move} plays the {role['en'].lower()} role. Whether to prioritize this move in the game still depends on candidate searches, replies, and the whole-board position.")
        limitations.append(_bi(
            '定式关联只核对已收录的短前缀；参考手顺与 KataGo 实际搜索变化分别展示。匹配定式不表示当前局面已完成定式、已经做活或必然应走完整条参考路线。',
            'Joseki references check only short cataloged prefixes. Reference sequences are separate from actual KataGo search lines. A match does not establish a completed joseki, life, or an obligation to follow the entire reference.'))
    elif immediate:
        description = immediate[0]
    elif shapes:
        description = shapes[0]
    elif interpretation:
        description = interpretation
    else:
        description = _bi(f"先查看 {move} 对棋盘的直接影响，再沿搜索变化核对对方应手和局面的演变。",
                          f"Inspect the immediate board effect of {move}, then replay the search line to check the opponent's replies and the resulting positions.")
    summary = (_bi(verdict["text"]["zh"] + description["zh"], verdict["text"]["en"] + " " + description["en"])
               if verdict else description)
    reasons = (reference_reasons + shape_reasons + search_reasons + reply_reasons + line_reasons
               + ownership_reasons + place_reasons)
    return {"title": _bi(f"为什么下在 {move}", f"Why play {move}"), "summary": summary, "verdict": verdict,
            "reasons": reasons, "continuation": continuation, "limitations": limitations,
            "joseki": joseki, "terms": get_terms(term_ids)}
