"""Move-centered explanation pipeline with independently evaluated PV positions."""

from contextlib import contextmanager
import json
from pathlib import Path
import time

from .board import other, point_to_vertex, vertex_to_point
from .engine import AnalysisEngine, actor_metric
from .explanation import generate_explanation


ROOT_VISITS = 800
CANDIDATE_VISITS = 600
TRACE_VISITS = 200
TENUKI_VISITS = 300
PV_PLIES = 6
# A PV tail explored by only a handful of playouts is not evidence of anything.
MIN_PV_VISITS = 16
MIN_PV_SHARE = 0.05
PHASES = 4


def text(zh, en):
    return {'zh': zh, 'en': en}


def trusted_pv(info, limit=PV_PLIES):
    """Keep the PV only while the search actually visited it.

    Returns (moves, truncated). Without per-move visit counts the PV is kept
    up to `limit`, as before.
    """
    pv = [move for move in (info.get('pv') or []) if isinstance(move, str)][:limit]
    visits = info.get('pvVisits')
    if not pv or not isinstance(visits, list) or not visits:
        return pv, False
    first = visits[0] if isinstance(visits[0], (int, float)) else 0
    floor = max(MIN_PV_VISITS, MIN_PV_SHARE * first)
    kept = [pv[0]]
    for move, count in zip(pv[1:], visits[1:]):
        if not isinstance(count, (int, float)) or count < floor:
            break
        kept.append(move)
    return kept, len(kept) < len(pv)


def _first_choice(response):
    return next((entry for entry in response.get('moveInfos', []) if entry.get('order') == 0), None)


@contextmanager
def _session(settings, output_dir, pool):
    if pool is None:
        with AnalysisEngine(settings, output_dir) as engine:
            yield engine
        return
    engine = pool.acquire(output_dir)
    failed = True
    try:
        yield engine
        failed = False
    finally:
        pool.release(engine, failed=failed)


def explain_move(game, game_id, move_index, choice, settings, output_dir, progress, custom_move=None, pool=None):
    started = time.monotonic()
    before = game.board_at(move_index)
    player = before.to_play
    opponent = other(player)
    history = [list(move) for move in game.moves[:move_index]]
    actual_move = game.moves[move_index][1] if move_index < len(game.moves) else None
    warnings = list(game.warnings)
    progress(text('正在分析当前局面，寻找推荐手…', 'Analyzing the position and finding the recommendation…'), 0, PHASES)
    with _session(settings, output_dir, pool) as engine:
        root = engine.query(game, history, ROOT_VISITS)
        ranked = sorted(root['moveInfos'], key=lambda entry: entry['order'])
        recommended = next((entry for entry in ranked if entry['order'] == 0), None)
        if recommended is None:
            raise ValueError('引擎未返回一选 / Engine returned no first choice')
        if root['rootInfo'].get('currentPlayer') != player:
            raise ValueError('引擎与棋谱的轮次不符 / Engine and SGF disagree about the player to move')
        ai_move = recommended['move']
        if custom_move:
            selected_move = point_to_vertex(vertex_to_point(custom_move, game.board_size), game.board_size)
            choice = 'custom'
        elif choice == 'actual':
            if actual_move is None:
                raise ValueError('棋谱在此处没有实战着法，请选择 AI 推荐 / No recorded move here; choose the AI move')
            selected_move = actual_move
        else:
            selected_move = ai_move
        # Validate the selected move against the real history before asking for a line.
        before.copy().play(player, selected_move)
        if selected_move != ai_move:
            alternative_move = ai_move
        elif actual_move is not None and actual_move != selected_move:
            alternative_move = actual_move
        else:
            alternative_move = next((entry['move'] for entry in ranked if entry['move'] != selected_move), None)
        chosen_moves = [selected_move] + ([alternative_move] if alternative_move else [])

        # Passing twice in a row would end the game, so the hypothetical-pass
        # comparison is skipped next to a real pass.
        compare_tenuki = (selected_move.lower() != 'pass'
                          and not (history and history[-1][1].lower() == 'pass'))
        progress(text(f'正在补搜候选 {"、".join(chosen_moves)}…', f'Re-searching {", ".join(chosen_moves)}…'), 1, PHASES)
        requests = [{'moves': history, 'visits': CANDIDATE_VISITS, 'forced_move': move, 'actor': player}
                    for move in chosen_moves]
        if compare_tenuki:
            requests.append({'moves': history + [[player, 'pass']], 'visits': TENUKI_VISITS, 'ownership': False})
        responses = engine.query_many(game, requests)
        forced_candidates, truncated = [], False
        for move, restricted in zip(chosen_moves, responses):
            infos = restricted['moveInfos']
            if len(infos) != 1 or infos[0]['move'] != move:
                raise ValueError('候选限制未生效 / The candidate restriction was not respected')
            info = infos[0]
            original = next((item for item in ranked if item['move'] == move), None)
            variation, cut = trusted_pv(info)
            truncated = truncated or cut
            forced_candidates.append({'move': move, 'original_order': original['order'] if original else None,
                                      **actor_metric(info, player), 'ownership': info.get('ownership', []),
                                      'pv': info.get('pv', [move]), 'trusted_pv': variation,
                                      'original': actor_metric(original, player) if original else None})
        tenuki = {}
        if compare_tenuki:
            skipped = responses[len(chosen_moves)]
            if skipped['rootInfo'].get('currentPlayer') != opponent:
                raise ValueError('脱先对比轮次不符 / Tenuki comparison has the wrong player')
            reply = _first_choice(skipped)
            tenuki['pass'] = {'eval': actor_metric(skipped['rootInfo'], player),
                              'reply': reply['move'] if reply else None}

        base_eval = actor_metric(root['rootInfo'], player)
        # Replay every line under the rules first, then evaluate all positions in one batch.
        pending, lines = [], []
        for candidate in forced_candidates:
            branch_board = before.copy()
            branch_history = [list(move) for move in history]
            variation = candidate['trusted_pv']
            if not variation or variation[0] != candidate['move']:
                variation = [candidate['move']]
                warnings.append(text('引擎变化起点不匹配，已仅保留首手。', 'PV start mismatch; only the first move was retained.'))
            line = []
            for ply, move in enumerate(variation, 1):
                turn = branch_board.to_play
                try:
                    facts = branch_board.play(turn, move)
                except ValueError as error:
                    warnings.append(text(f'变化第 {ply} 步未能通过规则校验：{error}', f'PV step {ply} failed rule validation: {error}'))
                    break
                branch_history.append([turn, move])
                line.append({'ply': ply, 'player': turn, 'move': move, 'board': branch_board.snapshot(),
                             'facts': facts, 'to_play': branch_board.to_play})
                pending.append({'moves': [list(item) for item in branch_history], 'visits': TRACE_VISITS,
                                'ownership': False})
                if len(branch_history) >= 2 and all(item[1].lower() == 'pass' for item in branch_history[-2:]):
                    break
            lines.append(line)
        if compare_tenuki:
            pending.append({'moves': history + [[player, selected_move], [opponent, 'pass']],
                            'visits': TENUKI_VISITS, 'ownership': False})
        progress(text(f'正在逐手评估变化（{len(pending)} 个局面）…', f'Evaluating the continuations ({len(pending)} positions)…'), 2, PHASES)
        evaluations = iter(engine.query_many(game, pending))
        branches = []
        for branch_index, (candidate, line) in enumerate(zip(forced_candidates, lines)):
            label = text('讲解这手的变化', 'Continuation for the explained move') if branch_index == 0 else text('另一选择的变化', 'Alternative continuation')
            steps = [{'ply': 0, 'player': None, 'move': None, 'board': before.snapshot(), 'eval': base_eval}]
            for step in line:
                position_analysis = next(evaluations)
                if position_analysis['rootInfo'].get('currentPlayer') != step.pop('to_play'):
                    raise ValueError('变化评估轮次不符 / Continuation evaluation has the wrong player')
                step['eval'] = actor_metric(position_analysis['rootInfo'], player)
                steps.append(step)
            branches.append({'id': 'selected' if branch_index == 0 else 'alternative',
                             'label': label, 'move': candidate['move'], 'steps': steps})
        if compare_tenuki:
            ignored = next(evaluations)
            if ignored['rootInfo'].get('currentPlayer') != player:
                raise ValueError('脱先对比轮次不符 / Tenuki comparison has the wrong player')
            followup = _first_choice(ignored)
            tenuki['ignored'] = {'eval': actor_metric(ignored['rootInfo'], player),
                                 'followup': followup['move'] if followup else None}

        selected = forced_candidates[0]
        alternative = forced_candidates[1] if len(forced_candidates) > 1 else None
        comparison = ({'winrate_pp': selected['winrate'] - alternative['winrate'],
                       'score_points': selected['score_lead'] - alternative['score_lead']} if alternative else None)
        root_ranked = [{'move': entry['move'], 'order': entry['order'], **actor_metric(entry, player)}
                       for entry in ranked[:6]]
        progress(text('正在把棋盘事实和搜索变化整理成讲解…', 'Turning board facts and search evidence into an explanation…'), 3, PHASES)
        evidence = {'selected': selected, 'alternative': alternative, 'comparison': comparison,
                    'ai_move': ai_move, 'actual_move': actual_move, 'base_eval': base_eval,
                    'branches': branches, 'root_ranked': root_ranked, 'tenuki': tenuki}
        explanation = generate_explanation(before, player, selected_move, evidence,
                                           pv=selected['trusted_pv'], history=game.moves[:move_index])
        explanation['limitations'].append(text(
            f'曲线按讲解这手的执棋方固定视角显示；每个节点重新搜索 {TRACE_VISITS} visits。前后差值也包含有限搜索的波动，不是因果证明。',
            f'The curve keeps the explained player’s perspective fixed. Each position is searched at {TRACE_VISITS} visits; differences also include finite-search variation and are not causal proof.'))
        if truncated:
            explanation['limitations'].append(text(
                '变化只显示搜索真正走到的部分：某一步的搜索次数过少时，其后的着法不再展示。',
                'The continuation shows only the part the search really explored: once a step has too few visits, later moves are omitted.'))
        result = {
            'game_id': game_id, 'move_index': move_index, 'player': player,
            'selected_move': selected_move, 'actual_move': actual_move, 'ai_move': ai_move, 'choice': choice,
            'board_size': game.board_size, 'rules': game.rules, 'komi': game.komi,
            'base_board': before.snapshot(), 'base_eval': base_eval,
            'selected': selected, 'alternative': alternative, 'comparison': comparison,
            'root_ranked': root_ranked, 'tenuki': tenuki,
            'explanation': explanation, 'branches': branches, 'warnings': warnings,
            'engine': {'version': engine.version, 'model': settings.model.name},
            'budgets': {'root_visits': ROOT_VISITS, 'candidate_visits': CANDIDATE_VISITS,
                        'trace_visits': TRACE_VISITS, 'tenuki_visits': TENUKI_VISITS, 'pv_plies': PV_PLIES},
        }
    result['elapsed_seconds'] = round(time.monotonic() - started, 3)
    result['cleanup'] = engine.cleanup
    if not (engine.cleanup.get('process_stopped') or engine.cleanup.get('kept_alive')):
        raise RuntimeError('引擎未正常停止，请检查运行日志 / Engine did not stop; check the run log')
    if output_dir is not None:  # the KaTrain plugin keeps results in memory only
        (Path(output_dir) / 'explanation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    progress(text('讲解已生成，可以逐步播放变化。', 'Explanation ready. You can replay the continuation.'), PHASES, PHASES)
    return result
