# 接口可行性验证 / Interface Feasibility Verification

本报告保留早期接口探针（probe）对真实 KataGo 引擎的验证记录。该次探针没有调用语言模型，也没有生成或推断棋理；其验证目标是确认候选排序、单候选根搜索、变化图和归属预测是否可通过 JSON 接口取得。

This report preserves the early interface probe's verification against a real KataGo engine. That probe did not call a language model or generate or infer Go reasoning. It checked whether the JSON interface provides candidate rankings, forced single-candidate root searches, principal variations, and ownership predictions.

项目随后已实现本机着法讲解原型与实验性 KaTrain 原生集成，使用规则核验、候选补搜和中英双语证据模板生成有限讲解；仍未接入语言模型或完成专家评测。当前功能与原生操作验收见[KaTrain 集成说明](KATRAIN_PLUGIN.md)，网页测试见[使用说明](USAGE.md)。下文保留原始探针的输入、数值、耗时和适用限制。

The project subsequently implemented a local move-explanation prototype and experimental native KaTrain integration, using rule checks, candidate searches, and bilingual evidence templates for limited explanations. Language models and expert evaluation remain future work. See the [native integration guide](KATRAIN_PLUGIN.md) for current features and user-assisted UI acceptance, or the [web user guide](USAGE.md) for testing. The original probe's inputs, values, timing, and limits are retained below.

**运行状态 / Run status:** `success`。**总耗时 / Total elapsed time:** 8.3440 秒 / seconds，包括环境查询、引擎启动、搜索和进程清理 / including environment queries, engine startup, searches, and process cleanup。

运行开始时间为 `2026-10-03T21:50:47.182192+00:00`；本机日志使用美国东部时间，首条日志为 `2026-10-03 17:50:47-0400`。

The run started at `2026-10-03T21:50:47.182192+00:00`. Local logs use US Eastern time; the first log entry is `2026-10-03 17:50:47-0400`.

首轮在启动阶段发现 `-analysis-threads` 与配置中的 `numAnalysisThreads` 重复。已改为只通过 `-override-config` 设置 `numAnalysisThreads=1`，原配置保持原样。本文状态、计时和原始输出均来自修正后的本轮运行。

The first attempt stopped during startup because `-analysis-threads` duplicated `numAnalysisThreads` in the supplied configuration. The corrected invocation sets `numAnalysisThreads=1` only through `-override-config` and leaves the original configuration unchanged. All status values, timings, and outputs in this report refer to the corrected run.

## 环境与输入 / Environment and Input

以下 metadata 来自实际执行的引擎版本查询和 GPU 查询；并非仅由源码文档推断。

The following metadata comes from actual engine-version and GPU queries, rather than being inferred solely from source documentation.

```text
KataGo v1.18.1
Git revision: 92ee95c0a4b25fec214da00951ab69e97e207729
Compile Time: Aug 23 2026 23:32:20
Using OpenCL backend
Compiled to support contributing to online distributed selfplay
NVIDIA GeForce RTX 5070 Laptop GPU, 8151 MiB, 582.05
```

| 项目 / Item | 实测值或样例路径 / Observed value or example path |
|---|---|
| 模型 / Model | `<LOCAL_WORKSPACE>\KaTrain-1.20.0\KaTrain\_internal\katrain\models\b10c384h6nbttflrs.bin.gz` |
| 模型大小 / Model size | 38,245,488 bytes |
| 模型 SHA-256 / Model SHA-256 | `0ba27eced5180b3e3d0b898b280c541112989765e789d1eb6cd0d31b2b2c1229` |
| 配置 / Configuration | `<LOCAL_WORKSPACE>\KaTrain-1.20.0\KaTrain\_internal\katrain\KataGo\analysis_config.cfg` |
| 只读使用的调优缓存 / Existing tuning cache used without modification | `<USER_PROFILE>\.katrain\opencltuning\tune13_gpuNVIDIAGeForceRTX5070LaptopGPU_x19_y19_c384_m192_h32_mv15.txt` |

发布样例已将本机绝对路径替换为 `<LOCAL_WORKSPACE>` 与 `<USER_PROFILE>`。它们是说明用占位符，不是可直接执行的路径；复现时需替换为自己的工作目录与用户目录，或通过探针的 CLI 参数指定实际文件。实测分析数值和测试条件保留。

Absolute paths in the published examples have been replaced with `<LOCAL_WORKSPACE>` and `<USER_PROFILE>`. These are documentation placeholders, not executable paths. Replace them with your workspace and user-profile directories, or supply actual files through the probe's CLI arguments. Measured analysis values and test conditions are preserved.

棋盘为 19×19，Chinese 规则，贴目 7.5；所有胜率和目差均为黑方视角。实际落子历史如下，当前轮到黑方：

The board is 19×19, with Chinese rules and komi 7.5. All win rates and score leads use Black's perspective. The actual move history is shown below; Black is to move:

```text
B Q16, W D4, B Q4, W D16, B R14, W C6, B F3, W C14
```

单分析线程、4 搜索线程、最大 batch 8，神经网络缓存参数 `nnCacheSizePowerOfTwo=18`。根搜索请求 256 visits；取引擎 `order=0` 与 `order=1`，分别请求 512 visits 的根节点单候选搜索。请求启用了 `includePolicy`、`includePVVisits`、`includeOwnership`、`includeMovesOwnership`，并设置 `analysisPVLen=8`。

The run uses one analysis thread, four search threads, maximum batch size 8, and `nnCacheSizePowerOfTwo=18`. The initial root search requests 256 visits. The candidates with engine ranks `order=0` and `order=1` then receive separate forced root searches requesting 512 visits each. Requests enable `includePolicy`, `includePVVisits`, `includeOwnership`, and `includeMovesOwnership`, with `analysisPVLen=8`.

`allowMoves` 的 `untilDepth=1` 只限制当前第一手，后续双方应手正常搜索。两个候选使用独立搜索树，但复用同一引擎进程的神经网络缓存；这不意味着统计独立。

With `untilDepth=1`, `allowMoves` restricts only the first move at the current root; subsequent replies for both players are searched normally. The two candidates use separate search trees but share the same engine process and neural-network cache. This does not establish statistical independence.

## 原始排序与等请求预算验证 / Original Ranking and Equal Requested Budgets

`order=0` 是引擎给出的第一选择，不能直接定义为原始 `winrate` 最大的候选。原始根搜索在候选之间分配的 visits 不相等。

`order=0` identifies the engine's first choice; it must not be defined simply as the candidate with the largest raw `winrate`. The initial root search allocates unequal visit counts across candidates.

| 手 / Move | 原始 order / Original order | 原始 visits / Original visits | 原始黑胜率 / Original Black win rate | 原始黑目差 / Original Black score lead | 单候选 visits / Forced candidate visits | 单候选黑胜率 / Forced Black win rate | 单候选黑目差 / Forced Black score lead |
|---|---:|---:|---:|---:|---:|---:|---:|
| O3 | 0 | 84 | 36.4982% | -0.7869 | 513 | 36.4671% | -0.7778 |
| R6 | 1 | 56 | 36.1269% | -0.8111 | 513 | 35.6072% | -0.8814 |

原始一选 O3 减二选 R6 的比较如下。胜率差采用百分点，目差之差采用目；表格显示值经过四舍五入，差值使用原始精度计算。

The following differences compare the original first choice O3 against the second choice R6. Win-rate differences are in percentage points; score-lead differences are in points. Displayed table values are rounded, while differences are calculated from the original precision.

| 指标 / Metric | 原始搜索 / Original search | 等请求预算单候选搜索 / Forced searches with equal requested budgets |
|---|---:|---:|
| O3 − R6 黑胜率 / Black win-rate difference | 0.3714 percentage points | 0.8599 percentage points |
| O3 − R6 黑目差 / Black score-lead difference | 0.0242 points | 0.1035 points |

这些差异只描述本次低预算搜索结果，不能据此证明最优性、估计置信区间或解释因果棋理。

These differences describe only this low-budget run. They do not prove optimality, establish confidence intervals, or explain causal Go reasoning.

## 已实际取得的输出字段 / Observed Output Fields

以下字段均出现在本次 **v1.18.1 可执行引擎**的真实返回中。因此，本次 `playSelectionValue`、`edgeVisits`、`edgeWeight` 与 `pvEdgeVisits` 的可用性有实际输出支持。未测试的请求功能不在本报告的验证范围内。

All fields below appear in real responses from the **v1.18.1 executable** used in this run. Availability of `playSelectionValue`, `edgeVisits`, `edgeWeight`, and `pvEdgeVisits` is therefore supported by observed output. Untested request features are outside this report's verified scope.

**顶层 / Top level:**

```text
id, isDuringSearch, moveInfos, ownership, policy, rootInfo, turnNumber
```

**候选 / Candidate move information:**

```text
edgeVisits, edgeWeight, lcb, move, order, ownership, playSelectionValue,
prior, pv, pvEdgeVisits, pvVisits, scoreLead, scoreMean, scoreSelfplay,
scoreStdev, utility, utilityLcb, visits, weight, winrate
```

**根局面 / Root position information:**

```text
currentPlayer, rawLead, rawNoResultProb, rawScoreSelfplay,
rawScoreSelfplayStdev, rawStScoreError, rawStWrError, rawVarTimeLeft,
rawWinrate, scoreLead, scoreSelfplay, scoreStdev, symHash, thisHash,
utility, visits, weight, winrate
```

根搜索返回了 12 个候选。目标根预算为 256，实际 `rootInfo.visits=259`；单候选目标预算均为 512，O3 搜索实际 `rootInfo.visits=514`，R6 搜索实际 `rootInfo.visits=515`。上表记录实际候选 `visits`，均为 513。请求上限与返回访问量不能直接视为完全相等；完整记录见 [`probe_summary.json`](../examples/probe_summary.json)。

The initial root response contains 12 candidates. Its requested budget is 256, with actual `rootInfo.visits=259`. Both forced searches request 512 visits; actual root visits are 514 for O3 and 515 for R6. The table records actual candidate `visits`, which are 513 for both. Requested limits and returned visit counts must not be treated as exactly equal. Full records are in [`probe_summary.json`](../examples/probe_summary.json).

| 数组 / Array | 实际长度 / Observed length |
|---|---:|
| policy（361 个交叉点及 pass）/ policy (361 intersections plus pass) | 362 |
| 根 ownership / Root ownership | 361 |
| O3 ownership / O3 ownership | 361 |
| R6 ownership / R6 ownership | 361 |

`pv` 和 `pvVisits` 可以提供变化图与逐手搜索支持量；`ownership` 可以提供黑白归属预测的区域比较。它们还需结合规则核验和反事实验证，才能支持自然语言棋理。本报告测试的早期探针只取得数据，没有实现后续原型中的讲解流程。

`pv` and `pvVisits` can support variation diagrams and show search support at each step; `ownership` can support regional comparisons of predicted Black and White ownership. These fields need rule checks and counterfactual verification to support natural-language Go reasoning. The early probe tested in this report collected data without the explanation workflow implemented in the later prototype.

## 测得时长与适用范围 / Timings and Scope

| 阶段 / Stage | 秒 / Seconds |
|---|---:|
| root_including_cold_start | 4.1410 |
| forced_O3 | 1.8590 |
| forced_R6 | 1.8600 |

首个阶段包含冷启动，后续阶段复用进程和缓存。总耗时 8.3440 秒还包含环境查询及清理。这是单个开局局面的一次接口验证，不能当作产品性能、平均延迟或复杂中盘耗时。

The first stage includes cold startup; subsequent stages reuse the process and cache. The total elapsed time of 8.3440 seconds also includes environment queries and cleanup. This is a single interface check on one opening position, not a product benchmark, average-latency measurement, or estimate for complex middlegame positions.

每阶段最多 40 秒，整体上限 90 秒；内部分析截止时间为启动后 82 秒，以预留清理时间。探针不会自动安装、下载或执行长时间调优。

Each stage is limited to 40 seconds, with an overall limit of 90 seconds. The internal analysis deadline is 82 seconds after startup to reserve cleanup time. The probe does not automatically install software, download files, or perform prolonged tuning.

**进程清理 / Process cleanup:**

```json
{"method": "stdin_eof_graceful", "returncode": 0, "process_stopped": true, "reader_threads_stopped": true}
```

引擎 warning 数量为 0。探针记录 warning，但不会把它误当作最终分析响应。

The engine emitted 0 warnings. The probe records warnings and does not mistake them for final analysis responses.

## 脚本与原始记录 / Script and Raw Records

以下链接相对于本报告所在的 `docs/` 目录。脚本位于 `../scripts/`，样例数据位于 `../examples/`。完整 stderr 保存在 JSON summary 的 `stderr` 数组中，此处省略长日志。

The following links are relative to this report's `docs/` directory. Scripts are in `../scripts/`, and example data is in `../examples/`. Complete stderr is retained in the JSON summary's `stderr` array; the lengthy log is omitted here.

| 文件 / File | 用途 / Purpose |
|---|---|
| [`smoke_probe.py`](../scripts/smoke_probe.py) | 仅使用 Python 标准库的接口探针；CLI 可覆盖引擎、模型、配置、缓存和输出目录。/ An interface probe using only the Python standard library; CLI options override the engine, model, configuration, cache, and output directory. |
| [`probe_input.jsonl`](../examples/probe_input.jsonl) | 本次实际请求，每行一条 JSON。/ Actual requests from this run, one JSON object per line. |
| [`probe_output.jsonl`](../examples/probe_output.jsonl) | 未经改写的引擎标准输出，每行一条 JSON。/ Unmodified engine stdout, one JSON object per line. |
| [`probe_summary.json`](../examples/probe_summary.json) | 环境 metadata、完整精度数值、比较结果、计时、warning、stderr 及清理状态；本机路径已替换为占位符。/ Environment metadata, full-precision values, comparisons, timings, warnings, stderr, and cleanup status; local paths are replaced with placeholders. |
