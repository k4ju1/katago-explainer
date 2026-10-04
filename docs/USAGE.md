# 使用说明 / User Guide

## 本机启动 / Start on this computer

在文件资源管理器中打开项目目录，双击根目录的 `START_EXPLAINER.cmd`。浏览器打开 `http://127.0.0.1:8788`；保留启动窗口，结束时关闭它或按 Ctrl+C。

Open the project folder in File Explorer and double-click `START_EXPLAINER.cmd`. Your browser opens `http://127.0.0.1:8788`. Keep the launcher window open; close it or press Ctrl+C when finished.

此入口优先使用本机已配置的 Python，以及项目旁的 KaTrain 引擎和模型。应用没有第三方 Python 依赖，也不会下载模型。换电脑时需要指定实际文件路径。

The launcher uses the existing Python runtime and the KaTrain engine/model beside this project. The application has no third-party Python dependencies and does not download models. Supply actual file paths when running on another computer.

## 讲解一手棋 / Explain a move

1. 先用默认开局，或点击“上传 SGF”读取自己的棋谱。
   Start with the opening example, or select “Upload SGF” to load your game.
2. 选择要讲解的手数。页面显示的是这一手落下前的局面。
   Choose a move number. The board shows the position before that move.
3. 选择“讲解实战着法”或“讲解 AI 一选”。也可以点击棋盘上的空点指定自己的候选。
   Choose “Explain played move” or “Explain AI first choice”, or click an empty intersection to select your own move.
4. 点击“解释这一步”，等待真实 KataGo 分析。
   Click “Explain this move” and wait for the real KataGo analysis.
5. 查看讲解中的棋盘事实、搜索依据和位置性解读。选择一条后续变化，点击下一步或播放，查看棋子与评估如何变化。
   Read the board facts, search evidence, and positional interpretation. Select a continuation and advance or play it to inspect the stones and evaluations.

`examples/capture-demo.sgf` 是可用于验证提子说明的 9 路样例：导入后选择第一手的“实战着法”，工具应说明 C8 提掉 C7 的一颗白子，棋盘重放应显示白子消失。

`examples/capture-demo.sgf` is a 9×9 capture test. Import it, select the first recorded move, and explain the played move. The tool should report that C8 captures the White stone at C7, and replay should remove that stone.

## 如何读数字 / How to read the values

- 界面所有胜率和目差固定为本次被讲解的执棋方视角，即使后续轮到对手也不会反转。正目差表示这方预计领先。
  All displayed winrates and score leads keep the explained player's perspective, even on the opponent's turn. A positive score lead favors that player.
- 候选比较：从同一个初始局面，分别限制第一手进行 512 visits 的补搜；后续应手不限制。差值单位为“百分点”和“目”。
  Candidate comparison: separate searches request 512 visits from the same position, restricting only the first move. Differences are in percentage points and points.
- 变化曲线：初始局面与变化里的每个节点分别请求 256 visits 的重新评估。每条变化最多显示 6 手；这些评估会受到有限预算影响，不能当作精确因果分解。
  Continuation curve: the starting position and each later position receive separate 256-visit evaluations. Each line shows at most six plies. Finite search affects the estimates; the curve is not an exact causal decomposition.
- AI 一选来自未限制搜索的 `order=0`，而不是直接取原始胜率最大值。补搜后数值或排序可能不同，工具会保留原始排序与实测数值。
  The AI first choice is `order=0` from the unrestricted search, rather than the highest raw winrate. Deeper candidate evaluations may differ; the original ranking and observed values are retained.

## 当前讲解能力 / Current explanation scope

已实现：SGF 主线导入、初始摆子和完整历史重放、提子/打吃/连接/气的规则核验、有限位置性解读、原始一选与候选补搜、主要变化逐手播放、逐节点胜率评估、中英切换。

Implemented: SGF mainline import, setup and full-history replay, rule-verified captures/atari/connections/liberties, limited positional interpretations, original recommendation and candidate re-searches, principal-variation playback, per-position evaluation, and Chinese/English switching.

当前使用规则与证据模板生成讲解，尚未接入语言模型。厚薄、全局方向、死活和复杂劫争的深入解释仍需要扩展和专家评测。棋盘事实可以直接核对；位置性解读明确标为证据不足或推测；主要变化是示例路线，不表示对手只有一种应手。

The current version generates explanations using rules and evidence templates, without a language model. Deeper explanations of influence, direction of play, life/death, and complex ko require further development and expert evaluation. Board facts are directly checkable, positional interpretations are explicitly tentative, and principal variations are illustrative rather than forced replies.

支持 9、13、19 路棋盘；Chinese、Japanese、Korean、AGA 命名规则；最多 1000 手。存在分支时沿第一分支读取。缺少规则或贴目时会显示默认假设。中途编辑局面、非交替落子、自杀规则变体、未知规则会明确拒绝；不要把拒绝导入理解为棋谱本身一定无效。

Supported: 9×9, 13×13, and 19×19 boards; named Chinese, Japanese, Korean, and AGA rules; up to 1,000 plies. Variations follow the first branch. Missing rules or komi produce visible default assumptions. Mid-game edits, non-alternating play, suicide-rule variants, and unknown rules are rejected explicitly; a rejected import is not necessarily an invalid SGF.

## 其他电脑与开发运行 / Other computers and development

```powershell
python -m explainer.server `
  --engine 'C:\path\to\katago.exe' `
  --model 'C:\path\to\model.bin.gz' `
  --config 'C:\path\to\analysis.cfg' `
  --tuner 'C:\path\to\matching-opencl-tuning.txt' `
  --open-browser
```

本版本的启动配置针对 OpenCL。每个查询最长等待 40 秒，一次讲解整体分析期限 150 秒。后台一次只运行一个分析任务；结果、原始请求和响应保存到 `runs/<时间>-<任务号>/`。目前结果不自动保存到云端。

The current launch settings target OpenCL. Each query waits at most 40 seconds, within a 150-second analysis deadline per explanation. One analysis job runs at a time. Results and raw protocol data are stored in `runs/<time>-<job-id>/`. Results are not automatically sent to a cloud service.

```powershell
python -m unittest discover -s tests -v
```

上述单元测试无需 GPU；实际引擎验证需通过页面运行。发生错误时保留页面错误提示，检查本轮 `engine.log` 和 `error.json`。

Unit tests require no GPU. Use the page for real engine validation. On error, retain the message and check that run's `engine.log` and `error.json`.
