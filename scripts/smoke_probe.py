"""Bounded, standard-library-only probe of KataGo's JSON analysis interface.

Writes only to --output-dir. Never edits the existing engine/model/config/cache.
This is a protocol feasibility check, not an explanation or performance benchmark.
"""

import argparse
import hashlib
import json
import queue
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


MOVES = [["B", "Q16"], ["W", "D4"], ["B", "Q4"], ["W", "D16"],
         ["B", "R14"], ["W", "C6"], ["B", "F3"], ["W", "C14"]]
STAT_KEYS = ("move", "order", "visits", "edgeVisits", "winrate", "scoreLead",
             "scoreMean", "scoreStdev", "utility", "utilityLcb", "lcb", "prior",
             "playSelectionValue", "pv", "pvVisits")


def stats(info):
    return {key: info[key] for key in STAT_KEYS if key in info}


def bounded_command(command, timeout=5):
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    return {"exit_code": result.returncode, "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()}


def query_payload(query_id, visits):
    return {"id": query_id, "moves": MOVES, "rules": "chinese", "komi": 7.5,
            "boardXSize": 19, "boardYSize": 19, "maxVisits": visits,
            "includePolicy": True, "includePVVisits": True,
            "includeOwnership": True, "includeMovesOwnership": True,
            "analysisPVLen": 8}


def run(args):
    started = time.monotonic()
    # Reserve time for graceful close, termination, file writes, and report creation.
    analysis_deadline = started + 82.0
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {"status": "not_started", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
               "purpose": "JSON protocol and evidence-field feasibility; no LLM or Go-reason claims",
               "paths": {"engine": str(args.engine), "model": str(args.model),
                         "config": str(args.config), "tuner": str(args.tuner)},
               "perspective": "BLACK", "rules": "chinese", "komi": 7.5,
               "board_size": [19, 19], "moves": MOVES, "stage_times_seconds": {},
               "limits": {"per_stage_seconds": 40, "overall_seconds": 90,
                          "analysis_deadline_seconds": 82},
               "warnings": [], "stderr": [], "cleanup": {},
               "configuration_note": "Analysis threads are configured only through numAnalysisThreads=1 in -override-config; the supplied configuration file is not edited."}
    responses = queue.Queue()
    process = None
    threads = []
    input_file = None
    output_file = None
    try:
        for label in ("engine", "model", "config", "tuner"):
            path = Path(getattr(args, label))
            if not path.is_file():
                raise FileNotFoundError(f"Missing {label}: {path}")
        summary["engine_version"] = bounded_command([str(args.engine), "version"])
        if summary["engine_version"]["exit_code"] != 0:
            raise RuntimeError("KataGo version command failed")
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi is None:
            summary["gpu"] = {"error": "GPU query unavailable: nvidia-smi was not found on PATH"}
        else:
            try:
                summary["gpu"] = bounded_command([
                    nvidia_smi, "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader"])
            except (OSError, subprocess.SubprocessError) as error:
                summary["gpu"] = {"error": str(error)}
        summary["model_size_bytes"] = Path(args.model).stat().st_size
        summary["model_sha256"] = hashlib.sha256(Path(args.model).read_bytes()).hexdigest()
        override = ("numAnalysisThreads=1,numSearchThreads=4,nnMaxBatchSize=8,nnCacheSizePowerOfTwo=18,"
                    f"openclTunerFile={args.tuner}")
        command = [str(args.engine), "analysis", "-config", str(args.config),
                   "-model", str(args.model),
                   "-override-config", override]
        summary["command"] = command
        input_file = (output_dir / "probe_input.jsonl").open("w", encoding="utf-8", newline="\n")
        output_file = (output_dir / "probe_output.jsonl").open("w", encoding="utf-8", newline="\n")
        launch_started = time.monotonic()
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                   errors="replace", bufsize=1, cwd=str(output_dir))

        def read_stdout():
            try:
                for line in process.stdout:
                    output_file.write(line)
                    output_file.flush()
                    try:
                        responses.put(json.loads(line))
                    except json.JSONDecodeError:
                        responses.put({"_parse_error": line.rstrip()})
            finally:
                responses.put({"_eof": True})

        def read_stderr():
            for line in process.stderr:
                summary["stderr"].append(line.rstrip())

        threads = [threading.Thread(target=read_stdout, daemon=True),
                   threading.Thread(target=read_stderr, daemon=True)]
        for thread in threads:
            thread.start()

        def request(payload, phase, phase_started=None):
            phase_started = time.monotonic() if phase_started is None else phase_started
            deadline = min(phase_started + 40, analysis_deadline)
            encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            input_file.write(encoded + "\n")
            input_file.flush()
            process.stdin.write(encoded + "\n")
            process.stdin.flush()
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"Stage {phase} exceeded its bounded deadline")
                try:
                    response = responses.get(timeout=remaining)
                except queue.Empty:
                    raise TimeoutError(f"Stage {phase} exceeded its bounded deadline")
                if "_eof" in response:
                    raise RuntimeError(f"Engine stdout closed before final {phase} response")
                if "_parse_error" in response:
                    raise RuntimeError(f"Unexpected non-JSON stdout: {response['_parse_error'][:250]}")
                if "warning" in response:
                    summary["warnings"].append(response)
                    # Warnings may precede a successful final response. Keep waiting.
                    if "moveInfos" not in response:
                        continue
                if response.get("id") != payload["id"]:
                    continue
                if "error" in response:
                    raise RuntimeError(f"Engine query error: {response['error']}")
                if response.get("isDuringSearch") is False:
                    if response.get("noResults") or "moveInfos" not in response:
                        raise RuntimeError(f"Final {phase} response has no analysis data")
                    summary["stage_times_seconds"][phase] = round(time.monotonic() - phase_started, 4)
                    return response

        root = request(query_payload("root-256", 256), "root_including_cold_start", launch_started)
        ranked = sorted(root["moveInfos"], key=lambda entry: entry["order"])
        by_order = {entry["order"]: entry for entry in ranked}
        if not all(order in by_order for order in (0, 1)):
            raise RuntimeError("Root search returned fewer than two ranked candidates")
        selected = [by_order[0], by_order[1]]
        summary["root"] = {"rootInfo": root["rootInfo"],
                           "candidate_count": len(ranked),
                           "selected_candidates": [stats(entry) for entry in selected],
                           "top_level_fields": sorted(root),
                           "move_info_fields": sorted(selected[0]),
                           "root_info_fields": sorted(root["rootInfo"]),
                           "policy_length": len(root.get("policy", [])),
                           "ownership_length": len(root.get("ownership", [])),
                           "move_ownership_lengths": {entry["move"]: len(entry.get("ownership", []))
                                                      for entry in selected}}
        summary["independent_candidates"] = []
        for entry in selected:
            move = entry["move"]
            payload = query_payload(f"forced-{move}-512", 512)
            payload["allowMoves"] = [{"player": "B", "moves": [move], "untilDepth": 1}]
            forced = request(payload, f"forced_{move}")
            matching = [info for info in forced["moveInfos"] if info["move"] == move]
            if len(matching) != 1 or len(forced["moveInfos"]) != 1:
                raise RuntimeError(f"Forced search did not restrict root to {move}")
            info = matching[0]
            summary["independent_candidates"].append({
                "move": move, "original_order": entry["order"], "original": stats(entry),
                "forced_rootInfo": forced["rootInfo"], "forced": stats(info),
                "winrate_change_percentage_points": (info["winrate"] - entry["winrate"]) * 100,
                "scoreLead_change_points": info["scoreLead"] - entry["scoreLead"],
                "ownership_length": len(info.get("ownership", []))})
        first, second = summary["independent_candidates"]
        summary["comparison"] = {
            "first_move": first["move"], "second_move": second["move"],
            "original_first_minus_second_winrate_percentage_points":
                (first["original"]["winrate"] - second["original"]["winrate"]) * 100,
            "forced_first_minus_second_winrate_percentage_points":
                (first["forced"]["winrate"] - second["forced"]["winrate"]) * 100,
            "original_first_minus_second_scoreLead_points":
                first["original"]["scoreLead"] - second["original"]["scoreLead"],
            "forced_first_minus_second_scoreLead_points":
                first["forced"]["scoreLead"] - second["forced"]["scoreLead"],
            "forced_higher_black_winrate_move": max(summary["independent_candidates"],
                                                     key=lambda item: item["forced"]["winrate"])["move"],
            "note": "Separate search trees with equal maxVisits; shared neural-net cache. Not proof of best move or statistical independence."}
        summary["status"] = "success"
    except Exception as error:
        summary["status"] = "limited"
        summary["error"] = f"{type(error).__name__}: {error}"
    finally:
        if process is not None:
            cleanup = summary["cleanup"]
            try:
                if process.stdin is not None:
                    process.stdin.close()
                process.wait(timeout=1.5)
                cleanup["method"] = "stdin_eof_graceful"
            except (OSError, subprocess.TimeoutExpired):
                process.terminate()
                try:
                    process.wait(timeout=1.5)
                    cleanup["method"] = "terminate"
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1.5)
                    cleanup["method"] = "kill"
            cleanup["returncode"] = process.returncode
            cleanup["process_stopped"] = process.poll() is not None
            for thread in threads:
                thread.join(timeout=0.5)
            cleanup["reader_threads_stopped"] = all(not thread.is_alive() for thread in threads)
        if input_file is not None:
            input_file.close()
        if output_file is not None:
            output_file.close()
        # Ensure requested artifacts exist even if startup prerequisites fail.
        for filename in ("probe_input.jsonl", "probe_output.jsonl"):
            path = output_dir / filename
            if not path.exists():
                path.write_text("", encoding="utf-8")
        summary["elapsed_seconds"] = round(time.monotonic() - started, 4)
        summary["limitations"] = [
            "Only one opening position and one low-budget run; not a product latency benchmark.",
            "First query includes cold engine startup; later queries reuse the process and NN cache.",
            "Original candidate visits are unequal; raw root candidate values are not equal-budget comparisons.",
            "Forced root searches restrict only depth 0; subsequent replies remain searched normally.",
            "No LLM explanations, fabricated Go concepts, calibration claims, or ranking certainty."]
        (output_dir / "probe_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_report(summary, output_dir)
    print(json.dumps({"status": summary["status"], "elapsed_seconds": summary["elapsed_seconds"],
                      "stage_times_seconds": summary["stage_times_seconds"],
                      "comparison": summary.get("comparison"), "error": summary.get("error"),
                      "output_dir": str(output_dir), "cleanup": summary["cleanup"]},
                     ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "success" else 1


def write_report(summary, output_dir):
    lines = ["# KataGo 解释 Agent：真实接口可行性验证", "",
             "本报告只展示真实引擎输出和接口能力，没有调用语言模型，也没有生成或推断棋理。", "",
             f"状态：{summary['status']}。总耗时：{summary['elapsed_seconds']:.4f} 秒（包括环境查询、启动、搜索和进程清理）。", "",
             "分析线程只通过 `-override-config` 中的 `numAnalysisThreads=1` 设置，原配置文件保持原样。", "",
             "## 环境与输入", "",
             "```text", summary.get("engine_version", {}).get("stdout", "版本查询未完成"),
             summary.get("gpu", {}).get("stdout", "GPU 查询未完成"), "```", "",
             f"模型：`{summary['paths']['model']}`。",
             f"模型 SHA-256：`{summary.get('model_sha256', '未完成')}`。",
             f"配置：`{summary['paths']['config']}`。",
             f"只读使用调优缓存：`{summary['paths']['tuner']}`。", "",
             "19×19，Chinese 规则，贴目 7.5；所有胜率和目差均为黑方视角。",
             "开局：黑 Q16、白 D4、黑 Q4、白 D16、黑 R14、白 C6、黑 F3、白 C14；当前黑方走。", "",
             "单分析线程、4 搜索线程、最大 batch 8。根搜索 256 visits；取引擎 order=0 与 order=1，分别做 512 visits 的根节点单候选搜索。",
             "`allowMoves` 的 `untilDepth=1` 只限制当前第一手，后续双方应手正常搜索。两个候选使用独立搜索树，但复用同一引擎的神经网络缓存。", ""]
    if "error" in summary:
        lines.extend(["## 已观察到的限制", "", summary["error"], ""])
    if "root" in summary:
        lines.extend(["## 原始排序与等预算候选验证", "",
                      "`order=0` 是引擎给出的第一选择；不可直接定义为原始 winrate 最大的候选。原始根搜索在候选之间分配的 visits 不相等。", "",
                      "| 手 | 原始 order | 原始 visits | 原始黑胜率 | 原始黑目差 | 独立 visits | 独立黑胜率 | 独立黑目差 |",
                      "|---|---:|---:|---:|---:|---:|---:|---:|"])
        forced_map = {item["move"]: item for item in summary.get("independent_candidates", [])}
        for original in summary["root"]["selected_candidates"]:
            forced = forced_map.get(original["move"], {}).get("forced")
            row = (f"| {original['move']} | {original['order']} | {original['visits']} | "
                   f"{original['winrate'] * 100:.4f}% | {original['scoreLead']:.4f} | ")
            row += (f"{forced['visits']} | {forced['winrate'] * 100:.4f}% | {forced['scoreLead']:.4f} |"
                    if forced else "未完成 | 未完成 | 未完成 |")
            lines.append(row)
        comparison = summary.get("comparison")
        if comparison:
            lines.extend(["", f"原始一选 {comparison['first_move']} 减二选 {comparison['second_move']}：",
                          f"原始黑胜率差 {comparison['original_first_minus_second_winrate_percentage_points']:.4f} 个百分点；"
                          f"等预算候选搜索后的黑胜率差 {comparison['forced_first_minus_second_winrate_percentage_points']:.4f} 个百分点。",
                          f"原始黑目差之差 {comparison['original_first_minus_second_scoreLead_points']:.4f} 目；"
                          f"等预算候选搜索后的黑目差之差 {comparison['forced_first_minus_second_scoreLead_points']:.4f} 目。", "",
                          "这些差异只描述本次低预算搜索结果；不能据此证明最优性、估计置信区间或解释因果棋理。"])
        root = summary["root"]
        lines.extend(["", "## 已实际取得的输出字段", "",
                      "顶层：`" + "`, `".join(root["top_level_fields"]) + "`。",
                      "候选：`" + "`, `".join(root["move_info_fields"]) + "`。",
                      "根局面：`" + "`, `".join(root["root_info_fields"]) + "`。", "",
                      f"目标根预算为 256，本轮实际 rootInfo.visits={root['rootInfo']['visits']}；"
                      "单候选目标预算均为 512。表格记录实际候选 visits，"
                      "probe_summary.json 也保留了各次实际 rootInfo.visits；请求上限与实际返回值不能直接视为完全相等。",
                      f"policy 长度：{root['policy_length']}（361 个交叉点及 pass）；根 ownership 长度：{root['ownership_length']}。",
                      f"一选和二选的 ownership 长度：`{json.dumps(root['move_ownership_lengths'], ensure_ascii=False)}`。",
                      "PV 和 pvVisits 可以提供变化图与逐手搜索支持量；ownership 可以提供黑白归属预测的区域比较。它们还需要规则核验和反事实验证，才能支持自然语言棋理。", ""])
    lines.extend(["## 测得时长与适用范围", "", "| 阶段 | 秒 |", "|---|---:|"])
    for stage, elapsed in summary["stage_times_seconds"].items():
        lines.append(f"| {stage} | {elapsed:.4f} |")
    lines.extend(["", "首个阶段包含冷启动；后续阶段复用进程和缓存。这是单个开局局面的接口验证，不能当作产品性能、平均延迟或复杂中盘耗时。",
                  "每阶段最多 40 秒，整体上限 90 秒；不会自动安装、下载或长时间调优。", "",
                  f"进程清理：`{json.dumps(summary['cleanup'], ensure_ascii=False)}`。",
                  f"引擎 warning 数量：{len(summary['warnings'])}。Warning 被记录，但不会被误当作最终分析响应。", "",
                  "## 文件", "",
                  "- `smoke_probe.py`：标准库探针，可通过 CLI 覆盖引擎、模型、配置、缓存和输出目录。",
                  "- `probe_input.jsonl`：真实请求；每行一条 JSON。",
                  "- `probe_output.jsonl`：未经改写的引擎标准输出；每行一条 JSON。",
                  "- `probe_summary.json`：环境、统计比较、计时、警告及清理状态。", ""])
    if summary["stderr"]:
        lines.extend(["## 引擎 stderr", "", "```text", "\n".join(summary["stderr"]), "```", ""])
    (output_dir / "feasibility.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, required=True, help="Path to the KataGo executable")
    parser.add_argument("--model", type=Path, required=True, help="Path to the KataGo model")
    parser.add_argument("--config", type=Path, required=True, help="Path to the analysis configuration")
    parser.add_argument("--tuner", type=Path, required=True, help="Path to an existing OpenCL tuning file")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "runs",
                        help="Output directory (default: repository/runs)")
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
