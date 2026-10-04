"""Conservative recognition of four sourced 19x19 corner prefixes.

This is a small teaching catalogue, not a joseki solver. It recognises exact
local stones and, when supplied, local move order. Setup diagrams without a
recorded opening are explicitly labelled as shape matches only. Reference
sequences contain factual short prefixes; explanatory wording is original.
"""
from __future__ import annotations

from dataclasses import dataclass

from .board import Board, BoardError, other, point_to_vertex, vertex_to_point


def _bi(zh: str, en: str) -> dict[str, str]:
    return {"zh": zh, "en": en}


@dataclass(frozen=True)
class _Prefix:
    id: str
    name: tuple[str, str]
    # Coordinates count from the left/bottom corner, starting at 1.
    moves: tuple[tuple[str, int, int, str, str], ...]
    guard: int
    source_title: tuple[str, str]
    source_url: str
    term_ids: tuple[str, ...]


_PREFIXES = (
    # Source GTP: Q16,R17,R16,Q17,P17,P18,O17; rotated 180 degrees.
    _Prefix(
        "star-33-traditional",
        ("星位点三三：传统扳长前缀", "Star-point 3-3 invasion: traditional hane prefix"),
        (("B", 4, 4, "星位占角", "Corner star point"),
         ("W", 3, 3, "点三三", "3-3 invasion"),
         ("B", 3, 4, "挡", "Block"),
         ("W", 4, 3, "长", "Extend"),
         ("B", 5, 3, "扳（二子头扳）", "Hane at the head of two stones"),
         ("W", 5, 2, "反扳", "Counter-hane"),
         ("B", 6, 3, "长", "Extend")),
        8,
        ("Nordic Go Dojo：Antti 的点三三示例", "Nordic Go Dojo: Antti's 3-3 example"),
        "https://www.nordicgodojo.eu/post/693/sunday-problem-41",
        ("joseki", "star_point", "invasion_33", "block", "extend", "hane", "counter_hane"),
    ),
    # Official OGS indexed record: Q16,R17,R16,Q17,O17,P17; rotated 180 degrees.
    _Prefix(
        "star-33-knight",
        ("星位点三三：小飞分支前缀", "Star-point 3-3 invasion: knight-move branch prefix"),
        (("B", 4, 4, "星位占角", "Corner star point"),
         ("W", 3, 3, "点三三", "3-3 invasion"),
         ("B", 3, 4, "挡", "Block"),
         ("W", 4, 3, "长", "Extend"),
         ("B", 6, 3, "小飞", "Small knight move"),
         ("W", 5, 3, "长", "Extend")),
        8,
        ("OGS 定式探索器：Yeonwoo Cho", "OGS Joseki Explorer: Yeonwoo Cho"),
        "https://online-go.com/joseki/22017",
        ("joseki", "star_point", "invasion_33", "block", "extend", "keima"),
    ),
    # Official OGS indexed record: Q16,R14,R15,Q14,O16,R10.
    # Source numeric (x,y) transforms to canonical (20-y,20-x).
    _Prefix(
        "star-approach-kick",
        ("星位小飞挂角：尖顶、一间跳与拆三前缀",
         "Star-point low approach: kick, one-space jump and extension prefix"),
        (("B", 4, 4, "星位占角", "Corner star point"),
         ("W", 6, 3, "小飞挂角", "Low knight approach"),
         ("B", 5, 3, "尖顶", "Kick (diagonal attachment)"),
         ("W", 6, 4, "长", "Extend"),
         ("B", 4, 6, "一间跳", "One-space jump"),
         ("W", 10, 3, "拆三", "Three-space extension")),
        11,
        ("OGS 定式探索器：曹薰铉《Lectures on Go Techniques》",
         "OGS Joseki Explorer: Cho Hunhyun, Lectures on Go Techniques"),
        "https://online-go.com/joseki/17781",
        ("joseki", "star_point", "approach", "keima", "kick", "extend", "jump", "three_space_extension"),
    ),
    # BGA diagram 2, read directly from the HTML grid: B C4, W E3.
    _Prefix(
        "komoku-knight-approach",
        ("小目小飞挂角入口", "3-4 point knight-approach opening"),
        (("B", 3, 4, "小目占角", "3-4 corner point"),
         ("W", 5, 3, "小飞挂角", "Knight approach")),
        8,
        ("英国围棋协会：Even Game Joseki, Part 1（图2）",
         "British Go Association: Even Game Joseki, Part 1 (diagram 2)"),
        "https://britgo.org/bgj/00221.html",
        ("joseki", "komoku", "approach", "keima"),
    ),
)


# Eight symmetries in a stable order; identity comes first.
_SYMMETRIES = tuple((swap, flip_x, flip_y)
                    for swap in (False, True)
                    for flip_x in (False, True)
                    for flip_y in (False, True))


def _transform(x: int, y: int, symmetry: tuple[bool, bool, bool]) -> tuple[int, int]:
    swap, flip_x, flip_y = symmetry
    if swap:
        x, y = y, x
    if flip_x:
        x = 20 - x
    if flip_y:
        y = 20 - y
    return x - 1, 19 - y  # Board uses zero-based coordinates from the top.


def _inside(point: tuple[int, int], symmetry: tuple[bool, bool, bool], width: int) -> bool:
    # The square is invariant under swapping; only the selected edges matter.
    _, flip_x, flip_y = symmetry
    x, y = point[0] + 1, 19 - point[1]
    if flip_x:
        x = 20 - x
    if flip_y:
        y = 20 - y
    return 1 <= x <= width and 1 <= y <= width


def _history_moves(history) -> list[tuple[str, tuple[int, int] | None]] | None:
    if history is None:
        return None
    if not isinstance(history, (list, tuple)) or len(history) > 1000:
        raise BoardError("无效落子历史。 / Invalid move history.")
    result = []
    for item in history:
        if isinstance(item, dict):
            player, move = item.get("player"), item.get("move")
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            player, move = item
        else:
            raise BoardError("无效落子历史。 / Invalid move history.")
        other(player)
        result.append((player, vertex_to_point(move, 19)))
    return result


def _history_relation(history, expected, symmetry, width) -> str | None:
    if history is None:
        return "shape"
    local = [(player, point) for player, point in history
             if point is not None and _inside(point, symmetry, width)]
    if local == expected:
        return "order"
    # A root setup can contain the initial stone, or an entire teaching diagram.
    # Only an exact suffix is compatible; arbitrary omitted/reordered moves are
    # not accepted. A setup match never certifies the missing move order.
    if any(local == expected[start:] for start in range(1, len(expected) + 1)):
        return "setup"
    return None


def _move_explanation(prefix: _Prefix, reference: list[dict], count: int) -> dict[str, str]:
    """Describe verified geometry, with conditional conventional purposes.

    Reference indices include the initial corner stone. All displayed vertices
    have already undergone the same symmetry as the matched board. These
    explanations describe the selected role; unplayed reference moves are not
    predictions and no local shape certifies an engine preference.
    """
    def at(ply):
        return reference[ply - 1]["move"]

    selected, seed = at(count), at(1)
    if prefix.id.startswith("star-33"):
        if count == 2:
            return _bi(
                f"{selected} 是相对对方星位 {seed} 的点三三，进入角部交涉。"
                "它可用于争取角部空间；能否做活及外围取舍仍需看实际应手。",
                f"{selected} invades at 3-3 beneath the opposing star-point stone at {seed}. "
                "It can contest corner space; survival and outside tradeoffs still depend on the actual replies.")
        if count == 3:
            return _bi(
                f"{selected} 紧贴对方 {at(2)}，并直接接到己方星位 {seed}，占住从 {at(2)} 向这一侧长的邻接点。"
                "这个挡可限制这一方向的直接延伸，但对手仍有其他应手。",
                f"{selected} touches the opposing stone at {at(2)}, connects directly to {seed}, "
                f"and occupies the adjacent extension point on this side of {at(2)}. "
                "This block can limit a direct extension in that direction, while other replies remain possible.")
        if count == 4:
            return _bi(
                f"{selected} 从己方 {at(2)} 沿三路线长出，两子直接相连并把棋形延长一格。"
                "它可作为继续沿边展开的基础。",
                f"{selected} extends directly from {at(2)} along the third line, joining the stones and lengthening the shape by one point. "
                "It can support further development along the side.")
        if prefix.id == "star-33-traditional":
            if count == 5:
                return _bi(
                    f"对方 {at(2)}/{at(4)} 两子相连，{selected} 占住其沿边下一处长的点，并从己方 {seed} 绕到 {at(4)} 外端，形成二子头扳。"
                    f"它可用于限制这一路继续长；参考 {at(6)} 反扳只是一个应法，实际后续仍以本局变化为准。",
                    f"The opposing stones at {at(2)}/{at(4)} are connected; {selected} occupies their next side-extension point "
                    f"and bends from {seed} around the end at {at(4)}, forming a hane at the head of two stones. "
                    f"It can check further extension on this line; the reference counter-hane at {at(6)} is only one option, not a forecast of this game.")
            if count == 6:
                return _bi(
                    f"{selected} 相对己方 {at(4)} 斜走，紧贴对方 {at(5)} 扳子，形成反扳。"
                    "它可用于围绕扳子继续接触交涉，后续须读气数与断点。",
                    f"{selected} plays diagonally from {at(4)} beside the opposing hane stone at {at(5)}, forming a counter-hane. "
                    "It can continue the contact exchange around that stone; the following liberties and cuts need reading.")
            if count == 7:
                return _bi(
                    f"{selected} 从己方扳子 {at(5)} 长出，两子直接相连并沿三路线延伸一格。"
                    "它可用于沿边继续发展和处理接触战。",
                    f"{selected} extends from the friendly hane stone at {at(5)}, connecting the two stones and moving one point along the third line. "
                    "It can develop further along the side and continue the contact fight.")
        if prefix.id == "star-33-knight":
            if count == 5:
                return _bi(
                    f"{selected} 与己方星位 {seed} 成小飞关系，两子并未直接连成一块。"
                    "这可作为沿边展开的方式，同时需留意小飞形的断点。",
                    f"{selected} forms a small knight move with the friendly star-point stone at {seed}; the stones are not directly connected. "
                    "It can develop along the side, while the knight shape's cutting points need attention.")
            if count == 6:
                return _bi(
                    f"{selected} 从己方 {at(4)} 长出，并紧邻对方小飞子 {at(5)}。"
                    "它可用于沿三路继续展开，并与小飞子进行接触交涉。",
                    f"{selected} extends from {at(4)} and touches the opposing knight-move stone at {at(5)}. "
                    "It can continue development along the third line and begin a contact exchange with the knight-move stone.")
    if prefix.id == "star-approach-kick":
        if count == 2:
            return _bi(
                f"{selected} 与对方星位 {seed} 呈小飞距离，落在第三线，是小飞挂角。"
                "它可用于接近角部、开启分角交涉。",
                f"{selected} approaches the opposing star-point stone at {seed} at a knight's-move distance on the third line. "
                "It can initiate negotiations over the corner.")
        if count == 3:
            return _bi(
                f"{selected} 与己方 {seed} 成尖形，紧贴 {at(2)} 挂角子，并占去它的一口气。"
                "这个尖顶可把挂角交涉转为接触战。",
                f"{selected} is diagonal to the friendly stone at {seed}, touches the approaching stone at {at(2)}, and removes one of its liberties. "
                "This kick can turn the approach into a contact fight.")
        if count == 4:
            return _bi(
                f"{selected} 从己方 {at(2)} 向第四线长出，两子直接相连。"
                "这种向外延伸可为继续处理挂角交涉增加活动空间。",
                f"{selected} extends from {at(2)} toward the fourth line, joining the two stones directly. "
                "This outward extension can give the stones more room to continue the corner interaction.")
        if count == 5:
            a, b = vertex_to_point(seed, 19), vertex_to_point(selected, 19)
            midpoint = point_to_vertex(((a[0] + b[0]) // 2, (a[1] + b[1]) // 2), 19)
            return _bi(
                f"{selected} 与己方 {seed} 之间隔着一个空点 {midpoint}，是一间跳，并非直接连接。"
                "它可用于向外发展、照应角上棋子，后续须留意切断手段。",
                f"{selected} is a one-space jump from {seed}, with the empty point {midpoint} between them; this is not a direct connection. "
                "It can develop outward while supporting the corner stones; cutting moves need attention.")
        if count == 6:
            return _bi(
                f"{selected} 从己方 {at(2)}/{at(4)} 两子沿边展开，与 {at(2)} 之间留三个空点，是拆三。"
                "它可用于扩大两子沿边的活动范围。",
                f"{selected} develops along the side from the two stones at {at(2)}/{at(4)}, leaving three empty points from {at(2)}. "
                "This three-space extension can expand their room along the side.")
    if prefix.id == "komoku-knight-approach" and count == 2:
        return _bi(
            f"{selected} 与对方小目 {seed} 呈小飞距离，落在第三线，是小飞挂角。"
            "它可用于开启角部交涉，后续应法尚未选择。",
            f"{selected} approaches the opposing 3-4 stone at {seed} at a knight's-move distance on the third line. "
            "It can begin a corner interaction; the continuation has not yet been chosen.")
    raise ValueError("The curated prefix has no explanation for this ply.")


def _entry(prefix, symmetry, swapped, count, relation):
    corner_point = _transform(1, 1, symmetry)
    left, bottom = corner_point[0] == 0, corner_point[1] == 18
    corners = {
        (True, True): ("左下角", "Lower-left corner"),
        (True, False): ("左上角", "Upper-left corner"),
        (False, True): ("右下角", "Lower-right corner"),
        (False, False): ("右上角", "Upper-right corner"),
    }
    relation_text = {
        "order": ("当前局部落子顺序与棋形均吻合此短前缀。",
                  "The local move order and current shape match this short prefix."),
        "shape": ("当前局部棋形吻合；未提供落子历史，仅作棋形对应。",
                  "The local shape matches; no move history was provided, so this is a shape match only."),
        "setup": ("当前局部棋形吻合；起始棋子未在历史中完整记录，仅作棋形对应。",
                  "The local shape matches; the starting stones are not fully recorded in the history, so this is a shape match only."),
    }
    reference = []
    for ply, (actor, x, y, zh, en) in enumerate(prefix.moves, 1):
        actor = other(actor) if swapped else actor
        reference.append({"ply": ply, "player": actor,
                          "move": point_to_vertex(_transform(x, y, symmetry), 19),
                          "role": _bi(zh, en), "selected": ply == count})
    notes = [
        _bi("只匹配所列短前缀，不表示完整定式已经结束。",
            "Only the listed short prefix is matched; this does not establish a completed joseki."),
        _bi("术语与棋形对应不证明本手是一选；实际取舍仍需结合全局与 KataGo 比较路线。",
            "Matching the terminology and shape does not prove this is the top move; the full board and KataGo comparison lines still matter."),
        _bi("不据此前缀判断征子、死活、先手或最终实地。",
            "This prefix does not establish ladder outcomes, life and death, sente, or final territory."),
    ]
    if count < len(reference):
        notes.insert(0, _bi(
            "后续未走步骤只是参考；尚未选择该后续分支，也不是本局预测变化。",
            "Unplayed steps are reference moves only; that later branch has not been chosen and is not a forecast of this game."))
    return {
        "id": prefix.id,
        "name": _bi(*prefix.name),
        "corner": _bi(*corners[left, bottom]),
        "stage": _bi(f"所列前缀第 {count}/{len(reference)} 手（非完整定式结论）",
                     f"Move {count}/{len(reference)} of the listed prefix (not a completed-joseki conclusion)"),
        "relation": _bi(*relation_text[relation]),
        "move_role": dict(reference[count - 1]["role"]),
        "move_explanation": _move_explanation(prefix, reference, count),
        "reference_line": reference,
        "sources": [{"title": _bi(*prefix.source_title), "url": prefix.source_url}],
        "notes": notes,
        "term_ids": list(prefix.term_ids),
    }


def find_joseki(before: Board, player: str, move: str, history=None) -> list[dict]:
    """Return exact corner-prefix teaching matches for the selected legal move.

    ``history`` contains BEFORE-position moves only, as [player, GTP] pairs or
    {player, move} dictionaries. Passes and moves outside a corner guard square
    do not change its local order. A complete local prefix validates the order;
    missing initial setup moves allow only an explicitly labelled shape match.
    An inconsistent supplied history suppresses the match. Neither board nor
    history is modified. At most three deterministic family matches are returned.
    """
    if not isinstance(before, Board) or before.size != 19:
        return []
    try:
        other(player)
        selected = vertex_to_point(move, 19)
        if selected is None:
            return []
        supplied_history = _history_moves(history)
        after = before.copy()
        facts = after.play(player, move)
        if facts["capturedCount"]:
            return []  # These curated prefixes contain no captures.
    except (BoardError, TypeError, ValueError):
        return []
    matches = []
    for prefix in _PREFIXES:
        family_matches = []
        for symmetry in _SYMMETRIES:
            for swapped in (False, True):
                line = [(other(actor) if swapped else actor, _transform(x, y, symmetry))
                        for actor, x, y, _, _ in prefix.moves]
                local_before = {point: actor for point, actor in before.cells.items()
                                if _inside(point, symmetry, prefix.guard)}
                local_after = {point: actor for point, actor in after.cells.items()
                               if _inside(point, symmetry, prefix.guard)}
                # A selected seed stone is not enough to identify a joseki.
                for count in range(len(line), 1, -1):
                    if line[count - 1] != (player, selected):
                        continue
                    expected_before = {point: actor for actor, point in line[:count - 1]}
                    expected_after = {point: actor for actor, point in line[:count]}
                    if local_before != expected_before or local_after != expected_after:
                        continue
                    relation = _history_relation(supplied_history, line[:count - 1],
                                                 symmetry, prefix.guard)
                    if relation is not None:
                        family_matches.append((count, _entry(prefix, symmetry, swapped, count, relation)))
                    break
        if family_matches:
            # Symmetry can leave a shared early shape identical. Select just one
            # reference orientation per family, preferring the longest match.
            family_matches.sort(key=lambda item: -item[0])
            matches.append(family_matches[0])
    matches.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [entry for _, entry in matches[:3]]
