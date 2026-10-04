"""Move-centered explanation pipeline with independently evaluated PV positions."""

import json
from pathlib import Path
import time

from .board import other, point_to_vertex, vertex_to_point
from .engine import AnalysisEngine, actor_metric
from .explanation import generate_explanation


ROOT_VISITS = 256
CANDIDATE_VISITS = 512
TRACE_VISITS = 256
PV_PLIES = 6


def text(zh, en):
    return {'zh': zh, 'en': en}


def snapshot(board):
    state = board.snapshot()
    state['to_play'] = board.to_play
    return state


def explain_move(game, game_id, move_index, choice, settings, output_dir, progress, custom_move=None):
    started = time.monotonic()
    before = game.board_at(move_index)
    player = before.to_play
    history = [list(move) for move in game.moves[:move_index]]
    actual_move = game.moves[move_index][1] if move_index < len(game.moves) else None
    warnings = list(game.warnings)
    progress(text('正在分析当前局面，寻找推荐手…', 'Analyzing the position and finding the recommendation…'), 0, 15)
    with AnalysisEngine(settings, output_dir) as engine:
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
        forced_candidates = []
        for count, move in enumerate(chosen_moves):
            progress(text(f'正在验证候选 {move} 的后续变化…', f'Searching the continuation for {move}…'), 1 + count, 15)
            restricted = engine.query(game, history, CANDIDATE_VISITS, move, player)
            infos = restricted['moveInfos']
            if len(infos) != 1 or infos[0]['move'] != move:
                raise ValueError('候选限制未生效 / The candidate restriction was not respected')
            info = infos[0]
            original = next((item for item in ranked if item['move'] == move), None)
            candidate = {'move': move, 'original_order': original['order'] if original else None,
                         **actor_metric(info, player), 'ownership': info.get('ownership', []),
                         'pv': info.get('pv', [move]),
                         'original': actor_metric(original, player) if original else None}
            forced_candidates.append(candidate)

        base_eval = actor_metric(root['rootInfo'], player)
        total = 1 + len(forced_candidates) + sum(min(PV_PLIES, len(item['pv'])) for item in forced_candidates)
        completed = 1 + len(forced_candidates)
        branches = []
        for branch_index, candidate in enumerate(forced_candidates):
            label = text('讲解这手的变化', 'Continuation for the explained move') if branch_index == 0 else text('另一选择的变化', 'Alternative continuation')
            branch_board = before.copy()
            branch_history = [list(move) for move in history]
            steps = [{'ply': 0, 'player': None, 'move': None, 'board': snapshot(before), 'eval': base_eval}]
            variation = candidate['pv'][:PV_PLIES]
            if not variation or variation[0] != candidate['move']:
                variation = [candidate['move']]
                warnings.append(text('引擎变化起点不匹配，已仅保留首手。', 'PV start mismatch; only the first move was retained.'))
            for ply, move in enumerate(variation, 1):
                turn = branch_board.to_play
                try:
                    facts = branch_board.play(turn, move)
                except ValueError as error:
                    warnings.append(text(f'变化第 {ply} 步未能通过规则校验：{error}', f'PV step {ply} failed rule validation: {error}'))
                    break
                branch_history.append([turn, move])
                progress(text(f'正在评估 {candidate["move"]} 变化第 {ply} 步：{move}…',
                              f'Evaluating {candidate["move"]}, continuation step {ply}: {move}…'), completed, total)
                position_analysis = engine.query(game, branch_history, TRACE_VISITS)
                if position_analysis['rootInfo'].get('currentPlayer') != branch_board.to_play:
                    raise ValueError('变化评估轮次不符 / Continuation evaluation has the wrong player')
                steps.append({'ply': ply, 'player': turn, 'move': move,
                              'board': snapshot(branch_board),
                              'eval': actor_metric(position_analysis['rootInfo'], player), 'facts': facts})
                completed += 1
                if len(branch_history) >= 2 and all(item[1].lower() == 'pass' for item in branch_history[-2:]):
                    break
            branches.append({'id': 'selected' if branch_index == 0 else 'alternative',
                             'label': label, 'move': candidate['move'], 'steps': steps})
        selected = forced_candidates[0]
        alternative = forced_candidates[1] if len(forced_candidates) > 1 else None
        comparison = ({'winrate_pp': selected['winrate'] - alternative['winrate'],
                       'score_points': selected['score_lead'] - alternative['score_lead']} if alternative else None)
        progress(text('正在把棋盘事实和搜索变化整理成讲解…', 'Turning board facts and search evidence into an explanation…'), completed, total)
        evidence = {'selected': selected, 'alternative': alternative, 'comparison': comparison,
                    'ai_move': ai_move, 'base_eval': base_eval, 'branches': branches}
        explanation = generate_explanation(before, player, selected_move, evidence,
                                           pv=selected['pv'][:PV_PLIES], history=game.moves[:move_index])
        explanation['limitations'].append(text(
            '曲线按讲解这手的执棋方固定视角显示；每个节点重新搜索 256 visits。前后差值也包含有限搜索的波动，不是因果证明。',
            'The curve keeps the explained player’s perspective fixed. Each position is searched at 256 visits; differences also include finite-search variation and are not causal proof.'))
        result = {
            'game_id': game_id, 'move_index': move_index, 'player': player,
            'selected_move': selected_move, 'actual_move': actual_move, 'ai_move': ai_move, 'choice': choice,
            'board_size': game.board_size, 'rules': game.rules, 'komi': game.komi,
            'base_board': snapshot(before), 'base_eval': base_eval,
            'selected': selected, 'alternative': alternative, 'comparison': comparison,
            'explanation': explanation, 'branches': branches, 'warnings': warnings,
            'engine': {'version': engine.version, 'model': settings.model.name},
            'budgets': {'root_visits': ROOT_VISITS, 'candidate_visits': CANDIDATE_VISITS,
                        'trace_visits': TRACE_VISITS, 'pv_plies': PV_PLIES},
        }
    result['elapsed_seconds'] = round(time.monotonic() - started, 3)
    result['cleanup'] = engine.cleanup
    if not engine.cleanup.get('process_stopped'):
        raise RuntimeError('引擎未正常停止，请检查运行日志 / Engine did not stop; check the run log')
    (Path(output_dir) / 'explanation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    progress(text('讲解已生成，可以逐步播放变化。', 'Explanation ready. You can replay the continuation.'), total, total)
    return result
