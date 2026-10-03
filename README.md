# KataGo Explainer

Evidence-supported explanations of Go moves using KataGo, counterfactual search, and claim verification.

结合 KataGo、候选反事实搜索与主张验证，为围棋着法提供有证据支撑的解释。

[Project plan — English](docs/PROJECT_PLAN.md) · [项目方案 — 中文](docs/PROJECT_PLAN.zh-CN.md) · [Verification / 接口验证](docs/feasibility.md)

## Overview / 项目概览

The goal is to let players import an SGF, compare an AI recommendation with another move, replay the relevant variations, and read explanations whose claims can be checked against board facts and search evidence.

目标是让棋友导入 SGF 棋谱，比较 AI 推荐手与另一着法，播放关键变化，并阅读能够通过棋盘事实与搜索证据核对的讲解。

Documentation and probe help/reports are bilingual. The planned review interface and explanations will support Chinese and English using the same evidence package and a consistent Go terminology glossary.

项目文档、探针帮助和报告使用中英双语。后续复盘界面与讲解将支持中文、英文切换，共用同一证据包，并使用一致的围棋术语表。

**Current status: a detailed project plan and a working KataGo Analysis Engine probe.** The SGF review interface, language-model explanations, claim verifier, and complete agent are planned development stages.

**当前阶段：详细项目方案与已运行的 KataGo Analysis Engine 接口探针。** SGF 复盘界面、语言模型讲解、主张验证器和完整 Agent 将按开发路线逐步实现。

## Available artifacts / 现有成果

| Artifact / 文件 | Purpose / 用途 |
| --- | --- |
| [English plan](docs/PROJECT_PLAN.md) / [中文方案](docs/PROJECT_PLAN.zh-CN.md) | Scope, architecture, algorithm, dataset, evaluation, and roadmap / 范围、架构、算法、数据集、评测与开发路线 |
| [Verification report / 验证报告](docs/feasibility.md) | Bilingual record of a real engine run and its limits / 真实引擎运行与适用限制的双语报告 |
| [Probe / 探针](scripts/smoke_probe.py) | Standard-library Python program for one root search and two candidate searches / 用 Python 标准库运行根搜索和两个候选补搜 |
| [Requests / 请求](examples/probe_input.jsonl) | Three real JSON requests / 三条真实 JSON 请求 |
| [Responses / 响应](examples/probe_output.jsonl) | Unmodified engine JSON responses / 未改写的引擎 JSON 响应 |
| [Summary / 摘要](examples/probe_summary.json) | Environment, statistics, timing, and process cleanup / 环境、统计、计时与进程清理记录 |

The example used KataGo v1.18.1 / OpenCL on an RTX 5070 Laptop GPU, with a 256-visit root request and two 512-visit candidate requests. Total probe time was about 8.344 seconds. This single low-budget opening example demonstrates interface feasibility; it does not establish product latency, optimal play, or explanation accuracy.

样例使用 RTX 5070 Laptop GPU 与 KataGo v1.18.1 / OpenCL：根搜索目标 256 visits，两个候选各 512 visits，探针总耗时约 8.344 秒。这条低预算开局样例说明接口可用；产品延迟、最优性和讲解准确率仍需要进一步评测。

Personal absolute paths were replaced with environment placeholders in the published report and summary. Engine responses and measured numerical results were retained.

发布报告与摘要中的个人绝对路径已替换为环境占位符，引擎响应与实测数值保留。

## Approach / 方法

```text
Position / 局面
  → Unrestricted root search / 未限制根搜索
  → Independent candidate searches / 候选独立补搜
  → Board facts and variation differences / 棋盘事实与变化差异
  → Claim verification / 主张验证
  → Explanation with replayable evidence / 附可播放证据的讲解
```

Read `order=0` to identify the recommendation from the unrestricted root search. Do not re-rank by winrate and call the result the engine's first choice. Candidate searches constrain only the first move; later replies remain free. The verifier distinguishes exact board facts, search-supported assessments, and unresolved claims.

从未限制根搜索的 `order=0` 读取引擎推荐，不自行按胜率重新定义一选。候选补搜只约束第一手，后续应手保持自由。验证器区分精确棋盘事实、搜索支持的判断和仍未解决的主张。

## Run the probe / 运行探针

The development environment used Python 3.12. Supply your own compatible KataGo OpenCL engine, model, Analysis Engine configuration, and GPU/model/board-matched OpenCL tuning file. These external files are not bundled. See [KataGo](https://github.com/lightvector/KataGo) for downloads and setup.

开发验证环境为 Python 3.12。请在本机准备兼容的 KataGo OpenCL 引擎、模型、Analysis Engine 配置，以及匹配 GPU、模型和棋盘尺寸的调优文件。仓库不包含这些外部文件；下载和配置见 [KataGo](https://github.com/lightvector/KataGo)。

PowerShell example — replace the paths / PowerShell 示例，请替换为自己的真实路径：

```powershell
python scripts/smoke_probe.py `
  --engine 'C:\path\to\katago.exe' `
  --model 'C:\path\to\model.bin.gz' `
  --config 'C:\path\to\analysis.cfg' `
  --tuner 'C:\path\to\matching-opencl-tuning.txt'
```

Results default to `runs/`; use `--output-dir` to change the destination. Each stage has a 40-second limit, and the analysis has an overall deadline. The probe cleans up its engine process, does not install dependencies or download models, and does not edit the supplied configuration. CUDA/TensorRT support requires a separate adaptation.

结果默认写入 `runs/`，可通过 `--output-dir` 更改位置。每阶段最多 40 秒，分析整体有截止时间，结束或失败时清理引擎进程。探针不安装依赖、不下载模型、不修改提供的配置。CUDA/TensorRT 后端需要另行适配。

The probe overrides the report perspective to `BLACK`, so stored winrates, score leads, and ownership remain consistent with the example summary.

探针通过启动配置将输出视角固定为 `BLACK`，使胜率、目差和归属预测与摘要中的黑方视角保持一致。

## Roadmap / 开发路线

| Stage / 阶段 | Deliverable / 成果 |
| --- | --- |
| Weeks 1–3 / 第 1–3 周 | SGF navigation, candidates, PV playback / 棋谱浏览、候选表、变化播放 |
| Weeks 4–6 / 第 4–6 周 | Candidate comparison, board facts, explanations / 候选比较、棋盘事实、讲解 |
| Weeks 7–8 / 第 7–8 周 | Claim verification, follow-up questions, fixed dataset / 主张验证、追问、固定评测集 |
| Weeks 9–10 / 第 9–10 周 | Frozen evaluation build, baselines, expert review / 冻结评测版本、基线实验、专家评审 |
| Weeks 11–12 / 第 11–12 周 | Reliability fixes, report export, demo / 稳定性改进、报告导出、演示 |

These are planning estimates. Evaluation will test whether candidate comparison and claim verification reduce unsupported explanations, while measuring their computational cost. Start with 30 pilot positions, then freeze a held-out evaluation set. Record later engineering revisions separately from the evaluated build.

以上周期是计划估计。评测重点是候选比较与主张验证能否减少无依据讲解，以及增加多少计算成本。先做 30 个试标局面，再固定独立评测集；评测后的工程修改与被冻结的版本分开记录。

## References / 参考

- [KataGo Analysis Engine v1.18.1](https://github.com/lightvector/KataGo/blob/v1.18.1/docs/Analysis_Engine.md)
- [KaTrain](https://github.com/sanderland/katrain)
- [Streamlit](https://docs.streamlit.io/)
- [sgfmill](https://mjw.woodcraft.me.uk/sgfmill/doc/1.1.1/)
