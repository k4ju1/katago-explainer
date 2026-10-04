# KataGo Explainer

A KaTrain plugin that explains Go moves with evidence: KataGo search, counterfactual comparison, and claim verification, shown inside KaTrain.

一个依附于 KaTrain 的着法讲解插件：在 KaTrain 里用 KataGo 搜索、候选反事实对比与主张验证，为着法提供有证据支撑的解释。

[KaTrain extension / KaTrain 扩展](docs/KATRAIN_PLUGIN.md) · [Web testing guide / 网页测试说明](docs/USAGE.md) · [Joseki references / 定式参考](docs/JOSEKI_REFERENCES.md) · [Project plan — English](docs/PROJECT_PLAN.md) · [项目方案 — 中文](docs/PROJECT_PLAN.zh-CN.md) · [Verification / 接口验证](docs/feasibility.md)

## Overview / 项目概览

The goal is to let players import an SGF, compare an AI recommendation with another move, replay the relevant variations, and read explanations whose claims can be checked against board facts and search evidence.

目标是让棋友导入 SGF 棋谱，比较 AI 推荐手与另一着法，播放关键变化，并阅读能够通过棋盘事实与搜索证据核对的讲解。

Documentation, the review interface, explanations, and probe reports support Chinese and English, with both languages using the same evidence and numerical values.

项目文档、复盘界面、讲解与探针报告使用中英双语，两种语言共用相同证据和数值。

**Current status: a runnable local move-explanation prototype.** Import an SGF, explain a recorded move or AI recommendation, replay the continuations, and inspect independently evaluated winrates. Explanations currently use verified board facts and evidence templates; language-model reasoning, a comprehensive claim verifier, and expert evaluation remain development stages.

**当前阶段：可运行的本机着法讲解原型。** 可导入 SGF，讲解实战手或 AI 推荐，逐步播放变化并查看重新评估的胜率。当前讲解使用可核验棋盘事实和证据模板；语言模型推理、完整主张验证器与专家评测仍需继续开发。

The current reference layer has seven curated entries on 19×19 boards, including 秀策尖 (Shusaku kosumi), 尖顶定式 (kick), 托退定式 (attachment and retreat), and one 芈氏飞刀 (Mi flying dagger) outside-hane branch, with rotations, reflections, and color reversal. A matching result adds a bilingual name, the move's role and conditional purpose, a reference sequence, sources, and context notes. Actual recorded order is distinguished from a matching diagram shape, and reference sequences stay separate from KataGo's searched variations. A Chinese-first bilingual glossary explains professional terms. This is a small reference catalog, not a comprehensive joseki database; see [reference coverage and safeguards](docs/JOSEKI_REFERENCES.md).

当前参考层在 19 路棋盘上收录七项精选参考，包括秀策尖、尖顶定式、托退定式和芈氏飞刀的一个外扳分支，支持旋转、镜像和黑白互换。匹配后提供中英定式名称、本手角色及有条件的目的说明、参考手顺、出处和适用说明。真实落子顺序与仅有相同棋形的摆子局面分别标注，定式参考手顺与 KataGo 搜索变化分别展示；中英术语表优先使用中文专业名称。这是小型参考目录，不是完整定式数据库；覆盖范围与核验边界见[定式参考说明](docs/JOSEKI_REFERENCES.md)。

The core has been tested with the real KataGo engine and automated tests. An earlier native build completed a user-assisted acceptance check: the original KaTrain executable opened with the board and two explanation buttons, and a native explanation request displayed an explanation, board, and winrate in the popup. This check does not establish manual acceptance of later additions such as the joseki reference display. The integration targets the pinned KaTrain v1.20.0 Windows folder build and is not an official stable plugin API.

核心流程已使用真实 KataGo 引擎与自动测试验证。此前的原生版本完成了用户协助的操作验收：原有 KaTrain 程序启动后显示棋盘和两个讲解按钮，发起原生讲解请求后，弹窗显示讲解、棋盘和胜率。这项验收不包含随后新增的定式参考显示等功能。集成仅针对固定版本的 KaTrain v1.20.0 Windows 文件夹版，不是官方稳定插件 API。

## Start in KaTrain / 在 KaTrain 中启动

On the configured Windows computer, close any running KaTrain instance, then double-click `START_KATRAIN_EXPLAINER.cmd` in the project folder. The launcher installs or updates the reversible plugin and opens the original KaTrain executable. The plugin runs inside KaTrain and sends its searches to the KataGo engine KaTrain already has running: there is no background service, no second KataGo process, and no separate Python runtime. After the first install KaTrain can also be opened directly. Open your game in KaTrain and use the right-side explanation panel for the selected recorded move or the current position's AI recommendation. No SGF re-upload is needed. The native popup opens with the verdict, keeps the board, playback and win-rate curve on the left, and sorts the explanation into five tabs (verdict, evidence, line, joseki and terms, limits). Clicking a reason or a step moves the board to it; ← → step through the line and Space plays it. See the [native integration guide](docs/KATRAIN_PLUGIN.md) for version checks, backups, and uninstall instructions.

在已配置的 Windows 电脑上，先关闭正在运行的 KaTrain，再双击项目目录中的 `START_KATRAIN_EXPLAINER.cmd`。启动器安装或更新可恢复的插件，并打开原有 KaTrain 程序。插件在 KaTrain 进程内运行，搜索直接交给 KaTrain 已经启动的 KataGo 引擎：没有后台服务，没有第二个 KataGo 进程，也不需要另外的 Python 环境。安装一次之后，也可以直接打开 KaTrain。在 KaTrain 中打开棋谱，通过右侧讲解面板解释选中的实战手，或讲解当前局面的 AI 一选，无需重新上传 SGF。原生弹窗先给结论，左侧是棋盘、逐手播放和胜率曲线，右侧把讲解分成五个标签页（结论、依据、变化、定式·术语、边界）。点击某条依据或某一手，棋盘会跳到对应的一步；← → 逐手，空格播放。版本检查、备份与卸载方法见[原生集成说明](docs/KATRAIN_PLUGIN.md)。

The two dock buttons follow KaTrain's selected interface language. The explanation popup also provides its own Chinese/English switch; both languages share the same search evidence and values.

右侧两个讲解按钮跟随 KaTrain 当前选择的界面语言。讲解弹窗还提供独立的中英切换，两种语言使用同一搜索证据与数值。

For a first reference test, open [examples/shusaku-demo.sgf](examples/shusaku-demo.sgf) in KaTrain, advance to move three (Black D5), and click “Explain last move”. Expect a 秀策尖 reference with its purpose, sources, and terms. More classic samples and target moves are listed in the [User Guide](docs/USAGE.md). These are test workflows for the new features; the prior native acceptance record covers the earlier capture UI.

首次测试可在 KaTrain 打开 [examples/shusaku-demo.sgf](examples/shusaku-demo.sgf)，前进到第 3 手黑 D5，再点击“解释刚才一手”。应显示秀策尖关联、作用说明、出处与术语。其他经典样例及目标手数见[使用说明](docs/USAGE.md)。这些是新增功能的测试步骤；此前记录的原生操作验收针对较早的提子界面。

### Development test page (optional) / 开发测试页（可选）

The plugin does not need this page. For developing or testing the explanation pipeline without KaTrain, double-click `START_EXPLAINER.cmd` and use `http://127.0.0.1:8788`. This secondary interface supports SGF upload, custom candidates, and the same explanation pipeline. Keep its launcher open while testing. See the [web user guide](docs/USAGE.md) for configuration and reading the numbers.

插件本身不需要这个页面。脱离 KaTrain 开发或测试讲解流程时，可双击 `START_EXPLAINER.cmd`，打开 `http://127.0.0.1:8788`。这个辅助界面支持 SGF 上传、自定义候选，并共用同一讲解流程。测试期间保留其启动窗口。配置方法与数字含义见[网页使用说明](docs/USAGE.md)。

Choose a sample under “经典棋形 / Classic pattern” on the web, click “定式示例 / Joseki example”, then “解释这一步 / Explain this move”. The example selects its intended recorded move automatically.

网页中先在“经典棋形 / Classic pattern”下拉框选择一类，再点击“定式示例 / Joseki example”和“解释这一步 / Explain this move”；示例自动选择对应的实战手。

## Available artifacts / 现有成果

| Artifact / 文件 | Purpose / 用途 |
| --- | --- |
| [Native integration guide / 原生集成说明](docs/KATRAIN_PLUGIN.md) | Experimental KaTrain v1.20.0 extension, installation, restoration, and workflow / 实验性 KaTrain v1.20.0 扩展、安装恢复与使用流程 |
| [Native launcher / 原生启动入口](START_KATRAIN_EXPLAINER.cmd) | Installs or updates the plugin and opens the original KaTrain / 安装或更新插件并打开原有 KaTrain |
| [Web user guide / 网页使用说明](docs/USAGE.md) | Secondary developer/testing interface and evidence interpretation / 辅助开发测试界面与证据解读 |
| [Joseki references / 定式参考说明](docs/JOSEKI_REFERENCES.md) | Curated prefixes, source attribution, history matching, and terminology limits / 精选前缀、来源、历史匹配与术语边界 |
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
  → Hypothetical-pass (tenuki) comparison / 假设停一手的脱先对比
  → Board facts and variation differences / 棋盘事实与变化差异
  → Board checks and evidence labels / 棋盘核验与证据分级
  → Explanation with replayable evidence / 附可播放证据的讲解
```

Read `order=0` to identify the recommendation from the unrestricted root search. Do not re-rank by winrate and call the result the engine's first choice. Candidate searches constrain only the first move; later replies remain free. Current rule checks and explanation labels distinguish exact board facts, search-supported assessments, and tentative interpretations. A comprehensive claim verifier remains planned.

The explanation opens with a verdict: how the move compares with the engine's first choice, in bands from “practically equal” (below 1 percentage point and 0.5 points, the size of search noise) to blunder. Two hypothetical-pass searches then estimate what the move is worth and whether it leaves a local follow-up. Values are shown to one decimal, and a variation is cut where the search stopped visiting it.

讲解第一句先给结论：这手与 AI 一选相比处于哪一档，从“基本等价”（差距小于 1 个百分点且小于 0.5 目，相当于搜索波动）到大失误。随后用两次“假设停一手”的搜索估计这手棋的价值，以及它是否留有局部后续手段。数值保留一位小数，变化只展示搜索真正走到的部分。

从未限制根搜索的 `order=0` 读取引擎推荐，不自行按胜率重新定义一选。候选补搜只约束第一手，后续应手保持自由。当前规则核验与讲解标签区分精确棋盘事实、搜索支持的判断和推测性解读；完整主张验证器仍在开发计划中。

Joseki recognition provides historical reference and terminology. It does not decide whether the move is the engine's first choice or justify its winrate change; those judgments use the actual root search, candidate re-searches, and replayed board facts.

定式识别提供已有手顺的参照与术语说明。一手棋是否为 AI 一选、胜率变化有多少，仍依据真实根搜索、候选补搜和棋盘重放事实判断；定式名称本身不能替代这些证据。

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

## References / 参考

- [KataGo Analysis Engine v1.18.1](https://github.com/lightvector/KataGo/blob/v1.18.1/docs/Analysis_Engine.md)
- [KaTrain](https://github.com/sanderland/katrain)
- [Streamlit](https://docs.streamlit.io/)
- [sgfmill](https://mjw.woodcraft.me.uk/sgfmill/doc/1.1.1/)
