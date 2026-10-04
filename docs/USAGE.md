# 使用说明 / User Guide

此页说明独立网页测试入口。日常在 KaTrain 中使用时，请从 `START_KATRAIN_EXPLAINER.cmd` 启动；安装、恢复与原生弹窗操作见 [KaTrain 原生集成说明](KATRAIN_PLUGIN.md)。

This page covers standalone web testing. For use inside KaTrain, start `START_KATRAIN_EXPLAINER.cmd`; see the [native integration guide](KATRAIN_PLUGIN.md) for installation, restoration, and popup controls.

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

## 定式参考与术语 / Joseki references and terminology

直接测试：点击页面上方“定式示例”，再点击“解释这一步”。示例自动选中第 5 手黑 E3 的实战着法，棋盘显示落子前局面；无需另选 AI 一选。分析后应看到“星位点三三：传统扳长前缀”、E3 的二子头扳作用说明、★ 对应的参考手，以及相关术语和出处。引擎仍独立分析候选，可能推荐另一手。

For a direct test, click “Joseki example” at the top, then “Explain this move”. The example automatically selects the fifth recorded move, Black E3, and shows its pre-move position; keep the recorded-move selection. After analysis, expect the traditional star-point 3-3 hane reference, E3's role at the head of two stones, the ★ reference step, related terms, and sources. The engine still analyzes candidates independently and may recommend a different move.

在 KaTrain 中测试同一功能：打开 `examples/joseki-demo.sgf`，前进至第 5 手黑 E3 落下后的节点，再点击“解释刚才一手”。扩展会自动回到落子前局面分析；不要前进到文件末尾的第 7 手后才发起本例请求。原生集成步骤见 [KaTrain 原生说明](KATRAIN_PLUGIN.md)。

To test the same feature in KaTrain, open `examples/joseki-demo.sgf`, advance to the node after the fifth move, Black E3, and click “Explain last move”. The extension analyzes its pre-move position automatically; do not advance to the file's final seventh move before this request. See the [native guide](KATRAIN_PLUGIN.md) for integration steps.

19 路局面中，若正在讲解的一手属于参考目录中的角部手顺前缀，讲解会增加“定式关联”区块：显示定式名称、角部、阶段、关联类型、本手作用、参考手顺、出处与说明。★ 标出正在讲解的一手。中英术语表解释星位、小目、挂角、靠、扳、长、粘、小飞、打吃、气等专业词；显示某个术语不代表工具已经证明该手取得了先手、厚势或做活。

On a 19×19 board, a move matching a cataloged corner-sequence prefix adds a “Joseki reference” block with its name, corner, stage, relation, move role, reference sequence, sources, and notes. ★ marks the move being explained. A bilingual glossary explains Chinese professional terms such as 星位 (star point), 小目 (komoku), 挂角 (approach), 靠 (attachment), 扳 (hane), 长 (extend), 粘 (solid connection), 小飞 (keima), 打吃 (atari), and 气 (liberties). Including a term does not prove that the move gains sente, thickness, or life.

当前仅收录四类精选前缀，支持旋转、镜像和黑白互换，不覆盖全部定式，9、13 路局面也不套用这些 19 路参考。未显示定式关联只表示没有匹配当前目录。真实棋谱的局部落子顺序与初始摆子形成的相同棋形会分别标注；角外脱先、周边配合、征子与全局价值仍需结合实际搜索判断。定式名称不保证当前选择最优。

The catalog contains four curated prefixes, with rotations, reflections, and color reversal. It does not cover every joseki, and these 19×19 references are not applied to 9×9 or 13×13 positions. No reference block means no current catalog match. Actual local move order is labeled separately from an equivalent setup diagram. Tenuki, nearby support, ladders, and whole-board value still require the actual search; a joseki name does not establish optimal play.

“定式参考手顺”是带出处的知识参照；候选变化和胜率曲线来自本次 KataGo 搜索。不要把参考中的下一手当作引擎刚刚推荐的应手，或将曲线数值套到参考手顺。具体收录内容、来源和匹配规则见[定式参考说明](JOSEKI_REFERENCES.md)。

The “joseki reference sequence” is sourced reference material; candidate continuations and winrate curves come from this KataGo run. Do not treat the next reference move as the engine's current recommendation or assign the search curve to that reference line. See [Joseki references](JOSEKI_REFERENCES.md) for coverage, sources, and matching rules.

逐手作用说明按定式角色给出有条件的目的解释，并标为“定式参考”依据。它与可核验的提子、气数等棋盘事实，以及真实搜索中的数值判断，分别显示；不会因为出现“扳”或“拆三”就断言本局已经取得某种收益。

Move-purpose text gives a conditional explanation of a reference role and is labeled as reference evidence. It is separate from checkable captures/liberties and from numerical search judgments; a hane or extension label does not assert a realized benefit in this game.

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

已实现：SGF 主线导入、初始摆子和完整历史重放、提子/打吃/连接/气的规则核验、有限位置性解读、原始一选与候选补搜、主要变化逐手播放、逐节点胜率评估、精选定式前缀参考、中文专业术语释义、中英切换。

Implemented: SGF mainline import, setup and full-history replay, rule-verified captures/atari/connections/liberties, limited positional interpretations, original recommendation and candidate re-searches, principal-variation playback, per-position evaluation, curated joseki-prefix references, Chinese professional terminology, and Chinese/English switching.

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
