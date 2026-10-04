"""Bilingual explanations built from legal replay and explicit search evidence.

No language model is used. Board facts and tentative positional interpretations
are displayed separately so a plausible sentence cannot masquerade as proof.
"""
from __future__ import annotations

import math

from .board import Board, BoardError, other, point_to_vertex, vertex_to_point


def _bi(zh, en):
    return {"zh": zh, "en": en}


def _color(player):
    return ("黑方", "Black") if player == "B" else ("白方", "White")


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


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
        result.append(_bi(f"{move} 把原先 {facts['connectedGroups']} 块分别连接的己方棋子连成一块；连接后共 {facts['moveGroupLibertiesAfter']} 口气。",
                          f"{move} joins {facts['connectedGroups']} previously separate friendly chains into one chain with {facts['moveGroupLibertiesAfter']} liberties."))
    if facts["rescuedAtariGroups"]:
        anchors = ", ".join(group[0] for group in facts["rescuedAtariGroups"])
        result.append(_bi(f"原先在 {anchors} 的己方棋块只有一口气；{move} 后连接棋块有 {facts['moveGroupLibertiesAfter']} 口气，解除当前叫吃。",
                          f"The friendly chains at {anchors} had one liberty; after {move}, the joined chain has {facts['moveGroupLibertiesAfter']} liberties, escaping the immediate atari."))
    if facts["createdAtariGroups"]:
        anchors = ", ".join(group[0] for group in facts["createdAtariGroups"])
        result.append(_bi(f"{move} 将对方在 {anchors} 的棋块从多口气压到一口气，形成叫吃；对方仍可能逃跑或反击。",
                          f"{move} reduces the opposing chains at {anchors} from multiple liberties to one, giving atari; the opponent may still escape or counterplay."))
    if facts["selfAtari"]:
        result.append(_bi(f"{move} 后本方落子所在棋块仅剩一口气；是否值得这样下，必须结合后续变化判断。",
                          f"The chain containing {move} has only one liberty afterward; whether that is worthwhile depends on the continuation."))
    if facts.get("ko"):
        result.append(_bi(f"此着形成劫，{facts['ko']} 处不能立即回提。",
                          f"This move creates a ko; an immediate recapture at {facts['ko']} is illegal."))
    return result


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
    if friendly:
        zh += f" 最近的己方棋子是 {friendly[0][1]}，横纵格数相加相距 {friendly[0][0]} 格。"
        en += f" The nearest friendly stone is {friendly[0][1]}, at Manhattan distance {friendly[0][0]}."
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


def generate_explanation(before: Board, player: str, move: str, analysis: dict, pv=None) -> dict:
    """Return the bilingual public schema used by the local UI.

    `analysis` candidate metrics must use the original actor's perspective:
    winrate in percent, score_lead in points. Ownership stays raw Black-oriented.
    Branches contain an entire PV including its first move.
    """
    next_board = before.copy()
    facts = next_board.play(player, move)
    move = facts["move"]
    reasons, continuation, limitations = [], [], []
    immediate = _description(before, player, move, facts)
    for index, description in enumerate(immediate):
        reasons.append({"id": f"immediate-{index}", "level": "board", "text": description, "ply": 1})
    if facts["capturedCount"]:
        captured_chains = {}
        for vertex in facts["captured"]:
            chain = before.group_at(vertex)
            if chain:
                captured_chains[tuple(chain["stones"])] = chain
        if captured_chains and all(chain["libertyCount"] == 1 for chain in captured_chains.values()):
            reasons.append({"id": "capture-urgency", "level": "board", "ply": 1, "text": _bi(
                "被提掉的棋块在落子前已经处于叫吃、只有一口气；这手完成当前提子。是否应立即兑现这一收获，还要对照其他候选及对方的后续应手。",
                "The captured chains were already in atari with one liberty before this move; the move completes the immediate capture. Whether to take that gain now still requires comparison with other choices and the opponent's continuations.")})
    location, interpretation = _location(before, player, move)
    if location:
        reasons.append({"id": "location", "level": "board", "text": location, "ply": 1})
    if interpretation and not immediate:
        reasons.append({"id": "positional-reading", "level": "tentative", "text": interpretation, "ply": 1})

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
        reasons.append({"id": "candidate-comparison", "level": "search", "text": _bi(
            f"在本次候选补搜中，{move} 相比 {alt_move} 的{zh_color}胜率差为 {delta_rate:+.3f} 个百分点，预计目差差为 {delta_lead:+.3f} 目。它说明搜索如何评价两个选择，不能单独证明某条棋理是胜率变化的原因。",
            f"In this candidate re-search, {move} versus {alt_move} changes {en_color}'s win probability by {delta_rate:+.3f} percentage points and expected score lead by {delta_lead:+.3f} points. This reports the search comparison; it does not by itself prove a Go explanation caused the difference.")})
    if analysis.get("ai_move") and str(analysis["ai_move"]).lower() == move.lower():
        reasons.append({"id": "engine-choice", "level": "search", "text": _bi(
            f"{move} 是这次初始搜索排序的第一选择。排序受搜索预算和引擎综合评价影响；不能把“第一选择”理解为已穷尽所有变化的唯一正确答案。",
            f"{move} ranked first in the initial search. Ranking depends on the search budget and the engine's combined evaluation; it is not a proof that every continuation was exhausted or that only one move is correct.")})
    elif (facts["capturedCount"] and alternative.get("move") == analysis.get("ai_move")
          and _number(delta_rate) and _number(delta_lead) and delta_rate < 0 and delta_lead < 0):
        reasons.append({"id": "capture-versus-engine-choice", "level": "search", "text": _bi(
            f"{move} 的提子是可验证的局部收获，但本次初始搜索的一选是 {alternative['move']}，候选补搜的胜率与预计目差也都偏向 {alternative['move']}。因此，“能提子”本身不足以说明应优先下这里；需要把这项收获和另一条变化中的机会一并比较。这是本次有限搜索的判断，不把实战着法直接判成错误。",
            f"The capture at {move} is a verified local gain, but the initial search chose {alternative['move']}, and the candidate re-search favors it in both win probability and expected score lead. Capturing alone does not establish priority: compare that gain with the opportunities in the other line. This is a finite-search judgment, not an automatic verdict that the recorded move is a mistake.")})

    # Ownership differences are clues from the network, never exact territory attribution.
    first_ownership, second_ownership = selected.get("ownership"), alternative.get("ownership")
    point = vertex_to_point(move, before.size)
    if (point is not None and isinstance(first_ownership, list) and isinstance(second_ownership, list)
            and len(first_ownership) == len(second_ownership) == before.size ** 2):
        points = []
        x, y = point
        for a in range(max(0, x - 2), min(before.size, x + 3)):
            for b in range(max(0, y - 2), min(before.size, y + 3)):
                index = b * before.size + a
                if _number(first_ownership[index]) and _number(second_ownership[index]):
                    points.append((abs(first_ownership[index] - second_ownership[index]), (a, b), index))
        if points:
            magnitude, changed_point, index = max(points, key=lambda item: item[0])
            if magnitude >= .03:
                vertex = point_to_vertex(changed_point, before.size)
                reasons.append({"id": "ownership-clue", "level": "search", "text": _bi(
                    f"两候选附近的归属预测在 {vertex} 有明显差别：{move} 后为 {first_ownership[index]:+.3f}，{alternative.get('move', '?')} 后为 {second_ownership[index]:+.3f}（正偏黑、负偏白）。这可提示局部为何受到搜索关注；不能直接当作实地数量或棋块死活结论。",
                    f"The nearby ownership estimate differs at {vertex}: {first_ownership[index]:+.3f} after {move}, versus {second_ownership[index]:+.3f} after {alternative.get('move', '?')} (positive favors Black, negative White). This points to a local search difference, not an exact territory count or a life/death verdict.")})

    branches = analysis.get("branches") or []
    selected_branch = next((branch for branch in branches if branch.get("id") == "selected" or branch.get("selected")), {})
    if not selected_branch and branches:
        selected_branch = branches[0]
    replayed, replay_error = _replay_branch(before, player, selected_branch, pv)
    for step in replayed:
        ply, actor, vertex, step_facts = step["ply"], step["player"], step["move"], step["facts"]
        zh_actor, en_actor = _color(actor)
        step_details = _description(step["before"], actor, vertex, step_facts)
        if not step_details:
            detail, _ = _location(step["before"], actor, vertex)
            step_details = [detail] if detail else []
        zh = f"变化第 {ply} 手：{zh_actor} {vertex}。"
        en = f"Continuation ply {ply}: {en_actor} {vertex}."
        if step_details:
            zh += " " + step_details[0]["zh"]
            en += " " + step_details[0]["en"]
        evaluation = step.get("eval") or {}
        if _number(evaluation.get("winrate")):
            zh += f" 此局面重新分析的{zh_color}胜率为 {evaluation['winrate']:.3f}%。"
            en += f" Re-analysis of this position gives {en_color} a {evaluation['winrate']:.3f}% win probability."
        continuation.append(_bi(zh, en))
        if ply > 1 and any(step_facts.get(key) for key in ("capturedCount", "connectedGroups", "rescuedAtariGroups", "createdAtariGroups")):
            reasons.append({"id": f"continuation-fact-{ply}", "level": "board", "ply": ply, "text": _bi(
                f"在所示变化的第 {ply} 手，{step_details[0]['zh']} 这是在这条具体应对序列中可重放验证的效果。",
                f"At ply {ply} of the shown line, {step_details[0]['en']} This effect can be verified by replaying this particular sequence.")})
    if len(replayed) > 1:
        response = replayed[1]
        reply_zh, reply_en = _color(response["player"])
        reasons.append({"id": "anticipated-reply", "level": "search", "ply": 2, "text": _bi(
            f"KataGo 的这条主要变化首先预计{reply_zh}应在 {response['move']}；逐手演示展示的是在这一应手下局面如何推进。对方换应手时，应重新分析。",
            f"This principal variation first anticipates {reply_en} replying at {response['move']}. The replay shows how the position develops under that reply; a different reply requires fresh analysis.")})
    alternative_branch = next((branch for branch in branches if branch.get("id") == "alternative"), None)
    if alternative_branch:
        alternate_steps, _ = _replay_branch(before, player, alternative_branch)
        if len(alternate_steps) > 1:
            reasons.append({"id": "alternative-reply", "level": "search", "text": _bi(
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
                    reasons.append({"id": "opportunity-order", "level": "search", "text": _bi(
                        f"在所示搜索路线里，选择 {deferred_move} 后，{opponent_zh}在变化第 {first_occupation['ply']} 手先在 {occupied_move} 落子；改下 {occupied_move} 则{zh_color}先占据这一点。{tradeoff_zh}这只说明这两条具体变化的差别，不保证对方必然这样应，也不据此推断先手或实地收益。",
                        f"In the shown search line, choosing {deferred_move} lets {opponent_en} occupy {occupied_move} first at ply {first_occupation['ply']}; choosing {occupied_move} instead lets {en_color} take that point first. {tradeoff_en} This describes these two particular lines, not a forced reply, a sente claim, or a territory gain.")})
                    break

    limitations.extend([
        _bi("本讲解由棋盘规则与搜索数据生成；位置性的解读单独标为推测，没有语言模型补写未经验证的棋理。",
            "This explanation is generated from board rules and search data. Positional interpretations are labeled tentative; no language model adds unverified Go claims."),
        _bi("主要变化是搜索给出的示例路径，并不证明对方每一步都必须这样下；换应手后胜率和局面会改变。",
            "The principal variation is an illustrative search line, not proof that every opponent reply is forced. Other replies can change the evaluation and position."),
        _bi("胜率是引擎对给定规则、贴目和搜索预算的估计；小差距可能随追加搜索改变。每步重新分析的胜率不一定单调。",
            "Win probability is an engine estimate for the given rules, komi, and search budget. Small differences may change with more search; per-position re-analysis need not be monotonic."),
    ])
    if replay_error:
        limitations.append(_bi("变化遇到非法着法，已停止展示，后续步骤未用于讲解。",
                               "Replay stopped at an illegal move; later steps were excluded from the explanation."))
    if not immediate and interpretation:
        summary = interpretation
    elif immediate:
        summary = immediate[0]
    else:
        summary = _bi(f"先查看 {move} 对棋盘的直接影响，再沿搜索变化核对对方应手和局面的演变。",
                      f"Inspect the immediate board effect of {move}, then replay the search line to check the opponent's replies and the resulting positions.")
    return {"title": _bi(f"为什么下在 {move}", f"Why play {move}"), "summary": summary,
            "reasons": reasons, "continuation": continuation, "limitations": limitations}
