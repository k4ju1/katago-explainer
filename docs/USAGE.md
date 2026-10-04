# 使用说明 / User Guide

此页说明可选的开发测试页，KaTrain 插件本身不需要它。日常在 KaTrain 中使用时，请从 `START_KATRAIN_EXPLAINER.cmd` 启动；安装、恢复与原生弹窗操作见 [KaTrain 原生集成说明](KATRAIN_PLUGIN.md)。

This page covers the optional development test page; the KaTrain plugin does not need it. For use inside KaTrain, start `START_KATRAIN_EXPLAINER.cmd`; see the [native integration guide](KATRAIN_PLUGIN.md) for installation, restoration, and popup controls.

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

直接测试：在页面上方的“经典棋形”下拉框选择要测试的类型，首次可选“秀策尖”；点击“定式示例”，再点击“解释这一步”。页面自动选中对应的实战手并显示落子前局面；保持“讲解实战着法”。分析后应看到相应参考名称、有条件的作用说明、★ 对应的参考手、专业术语和出处。引擎仍独立分析候选，可能推荐另一手。

For a direct test, use the top “Classic pattern” dropdown; “Shusaku diagonal” is a short first example. Click “Joseki example”, then “Explain this move”. The page selects the intended recorded move and its pre-move position automatically; keep the recorded-move selection. After analysis, expect its reference name, conditional purpose text, the ★ reference step, professional terms, and sources. The engine still analyzes candidates independently and may recommend another move.

在 KaTrain 中测试：打开下表对应的 SGF，前进至目标手落下后的节点，再点击“解释刚才一手”。扩展自动从该手落下前的局面分析；目标手数不一定是文件的最后一手。原生集成步骤见 [KaTrain 原生说明](KATRAIN_PLUGIN.md)。

In KaTrain, open the SGF below, advance to the node after the target move, and click “Explain last move”. The extension analyzes the position before that move automatically; the target is not always the final move in the file. See the [native guide](KATRAIN_PLUGIN.md) for integration steps.

| 样例 / Sample | 文件 / File | 目标节点 / Target node | 应核对的内容 / Expected reference |
| --- | --- | --- | --- |
| 秀策尖 / Shusaku kosumi | [`shusaku-demo.sgf`](../examples/shusaku-demo.sgf) | 第 3 手黑 D5 / Black D5, move 3 | 小目挂角后的尖；不要与尖顶混称。 / Diagonal response to a 3-4 approach, distinct from a kick. |
| 尖顶定式 / Kick | [`kick-demo.sgf`](../examples/kick-demo.sgf) | 第 3 手黑 E3 / Black E3, move 3 | 星位小飞挂角代表线中的尖顶。 / Kick in the representative star-point low-approach line. |
| 托退定式 / Attachment and retreat | [`attach-retreat-demo.sgf`](../examples/attach-retreat-demo.sgf) | 第 5 手黑 D3 / Black D3, move 5 | 托、扳后退回；后续分支仍需具体判断。 / Retreat after attachment and hane; later branches depend on context. |
| 芈氏飞刀：外扳分支入口 / Mi flying dagger: outside-hane branch entry | [`mi-flying-dagger-demo.sgf`](../examples/mi-flying-dagger-demo.sgf) | 第 17 手黑 G6 / Black G6, move 17 | 所收录外扳分支入口；第 13 手的尖入只是中间步骤。 / The stored outside-hane branch entry; the move-13 diagonal entry is an intermediate step. |
| 传统点三三 / Traditional 3-3 | [`joseki-demo.sgf`](../examples/joseki-demo.sgf) | 第 5 手黑 E3 / Black E3, move 5 | 二子头扳与参考说明。 / Hane at the head of two stones and reference text. |

芈氏飞刀样例只测试这个 17 手分支的识别，不能把匹配理解为征子有利、必然做活或当前最优。秀策尖只命名这段局部应对，不表示工具已经识别完整秀策流布局。以上步骤不等于新增原生功能已经完成人工操作验收。

The Mi sample tests recognition of this 17-move branch, not a favorable ladder, guaranteed life, or optimal play. The Shusaku entry names a local response, not a complete Shusaku opening. These steps do not constitute completed manual native acceptance of the additions.

19 路局面中，若正在讲解的一手属于参考目录中的角部手顺前缀，讲解会增加“定式关联”区块：显示定式名称、角部、阶段、关联类型、本手作用、参考手顺、出处与说明。★ 标出正在讲解的一手。中英术语表解释星位、小目、挂角、靠、扳、长、粘、小飞、打吃、气等专业词；显示某个术语不代表工具已经证明该手取得了先手、厚势或做活。

On a 19×19 board, a move matching a cataloged corner-sequence prefix adds a “Joseki reference” block with its name, corner, stage, relation, move role, reference sequence, sources, and notes. ★ marks the move being explained. A bilingual glossary explains Chinese professional terms such as 星位 (star point), 小目 (komoku), 挂角 (approach), 靠 (attachment), 扳 (hane), 长 (extend), 粘 (solid connection), 小飞 (keima), 打吃 (atari), and 气 (liberties). Including a term does not prove that the move gains sente, thickness, or life.

当前收录七项精选参考，支持旋转、镜像和黑白互换，不覆盖全部定式，9、13 路局面也不套用这些 19 路参考。未显示定式关联只表示没有匹配当前目录。真实棋谱的局部落子顺序与初始摆子形成的相同棋形会分别标注；角外脱先、周边配合、征子与全局价值仍需结合实际搜索判断。定式名称不保证当前选择最优。

The catalog has seven curated entries, with rotations, reflections, and color reversal. It does not cover every joseki, and these 19×19 references are not applied to 9×9 or 13×13 positions. No reference block means no current catalog match. Actual local move order is labeled separately from an equivalent setup diagram. Tenuki, nearby support, ladders, and whole-board value still require the actual search; a joseki name does not establish optimal play.

“定式参考手顺”是带出处的知识参照；候选变化和胜率曲线来自本次 KataGo 搜索。不要把参考中的下一手当作引擎刚刚推荐的应手，或将曲线数值套到参考手顺。具体收录内容、来源和匹配规则见[定式参考说明](JOSEKI_REFERENCES.md)。

The “joseki reference sequence” is sourced reference material; candidate continuations and winrate curves come from this KataGo run. Do not treat the next reference move as the engine's current recommendation or assign the search curve to that reference line. See [Joseki references](JOSEKI_REFERENCES.md) for coverage, sources, and matching rules.

逐手作用说明按定式角色给出有条件的目的解释，并标为“定式参考”依据。它与可核验的提子、气数等棋盘事实，以及真实搜索中的数值判断，分别显示；不会因为出现“扳”或“拆三”就断言本局已经取得某种收益。

Move-purpose text gives a conditional explanation of a reference role and is labeled as reference evidence. It is separate from checkable captures/liberties and from numerical search judgments; a hane or extension label does not assert a realized benefit in this game.

实际搜索变化里的后续手，也会按累计的真实历史重新匹配自己的角色，例如变化确实走到 E2 时解释反扳；不会借用尚未走出的参考步骤作为本局证据。

Later moves in an actual searched variation can receive their own role match using accumulated history, such as a counter-hane explanation if E2 is actually played; unplayed reference steps are not borrowed as evidence for this game.

## 如何读数字 / How to read the values

- 界面所有胜率和目差固定为本次被讲解的执棋方视角，即使后续轮到对手也不会反转。正目差表示这方预计领先。
  All displayed winrates and score leads keep the explained player's perspective, even on the opponent's turn. A positive score lead favors that player.
- 结论在最前：讲解第一句先给出本次搜索的判断，再说明棋形。实战手与 AI 一选的补搜差距同时小于 1 个百分点和 0.5 目时写“基本等价”；否则按差距分为略亏、小失误、失误、大失误（目差 0.5／1.5／3／6 目，胜率 1／4／8／15 个百分点，取较重的一档）。原局面胜率超过 90% 或低于 10% 时胜率已不敏感，只按目差分档。
  The verdict comes first: the opening sentence states this search's judgment, then the shape. When the re-search gap between the game move and the first choice is below both 1 percentage point and 0.5 points, the moves are called “practically equal”. Otherwise the gap is banded as slightly worse, inaccuracy, mistake, or blunder (0.5/1.5/3/6 points of score, 1/4/8/15 percentage points, whichever is more severe). Above 90% or below 10% win probability only the score is used.
- 数值保留一位小数：同一局面重复搜索，胜率常有零点几个百分点的出入，更多小数位没有意义。
  Values are shown to one decimal: repeated searches of one position differ by a few tenths of a percentage point, so more digits carry no information.
- 根搜索请求 800 visits。候选比较：从同一个初始局面，分别限制第一手进行 600 visits 的补搜；后续应手不限制。差值单位为“百分点”和“目”。根搜索里与一选差距在波动范围内、且搜索次数足够的着法会列为同一档。
  The root search requests 800 visits. Candidate comparison: separate searches request 600 visits from the same position, restricting only the first move. Differences are in percentage points and points. Root moves within noise of the first choice, with enough visits, are listed as one tier.
- 脱先对比：另外搜索两个假设局面（各 300 visits）。“这手不下、停一手”的评估与下了这手的评估之差，是这手棋的大致价值，同时显示对方此时最想下哪里。“下了这手后对方停一手”的局面给出己方的后续手：后续手就在同一局部，说明这手留有后续、接近先手；后续手在别处，说明对方可以脱先。停一手只是衡量手段，不是实战建议；上一手或本手是停一手时跳过这项对比。
  Tenuki comparison: two hypothetical positions are searched (300 visits each). The gap between “pass instead of this move” and the move itself approximates the move's value, and shows where the opponent most wants to play. “The opponent passes after this move” gives the follow-up: a follow-up in the same area means the move leaves a threat and is close to sente; a follow-up elsewhere means the opponent can play away. The pass is a measuring device, not advice; the comparison is skipped next to a real pass.
- 变化曲线：初始局面与变化里的每个节点分别请求 200 visits 的重新评估，这些局面一次性并行发送给引擎。每条变化最多显示 6 手，而且只显示搜索真正走到的部分：某一步的搜索次数低于门槛（首手的 5% 与 16 次中较高者）时，其后的着法不再展示。评估会受到有限预算影响，不能当作精确因果分解。
  Continuation curve: the starting position and each later position receive separate 200-visit evaluations, sent to the engine as one parallel batch. Each line shows at most six plies and only the part the search really explored: once a step falls below the floor (the larger of 5% of the first move's visits and 16 visits), later moves are omitted. Finite search affects the estimates; the curve is not an exact causal decomposition.
- 变化中的脱先：某一手离此前所有落点都很远时，直接写“脱先，转向某处”，并说明原来的局部走到上一手暂告一段落。
  Tenuki inside a line: a move far from every earlier move of the line is reported as playing elsewhere, with a note that the original local exchange is settled for now.
- 归属预测：只汇总两个候选着法周围的差别，以及附近哪块棋的归属均值变化最大。远离候选的区域只反映两条变化各自把闲手下在了哪里，不参与汇总。它是网络估计，不是实地数目或死活结论。
  Ownership: only the neighbourhoods of the two candidates are summed, plus the nearby chain whose mean ownership changes most. Distant areas only show where each line spends its free moves and are left out. This is a network estimate, not a territory count or a life-and-death verdict.
- AI 一选来自未限制搜索的 `order=0`，而不是直接取原始胜率最大值。补搜后数值或排序可能不同，工具会保留原始排序与实测数值。
  The AI first choice is `order=0` from the unrestricted search, rather than the highest raw winrate. Deeper candidate evaluations may differ; the original ranking and observed values are retained.

## 当前讲解能力 / Current explanation scope

已实现：SGF 主线导入、初始摆子和完整历史重放、提子/打吃/连接/气的规则核验、按相邻关系判别的棋形名称（断、扳、长、顶、尖顶、托、靠、尖、肩冲、跳、小飞、大飞、挂角、占角；同一手只给一个名称）、有限位置性解读、原始一选与候选补搜、结论分档、脱先对比、主要变化逐手播放、逐节点胜率评估、精选定式前缀参考、中文专业术语释义、中英切换。

Implemented: SGF mainline import, setup and full-history replay, rule-verified captures/atari/connections/liberties, adjacency-based shape names (cut, hane, extension, push, kick, attachment, diagonal, shoulder hit, jumps, knight moves, approach, corner point; one name per move), limited positional interpretations, original recommendation and candidate re-searches, verdict tiers, tenuki comparison, principal-variation playback, per-position evaluation, curated joseki-prefix references, Chinese professional terminology, and Chinese/English switching.

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

四个路径参数都可以省略。省略时依次使用：命令行参数、环境变量 `KATAGO_EXPLAINER_ENGINE`／`MODEL`／`CONFIG`／`TUNER`、自动查找。自动查找会在项目同级目录寻找 `KaTrain*` 文件夹里的引擎、配置和模型，并在 `~/.katrain/opencltuning` 里选取 19 路、与模型通道数相符的最新调优文件，不依赖具体显卡名称。找不到调优文件时不指定该项，由 KataGo 自行处理（首次运行可能需要较长的调优时间）。

本版本的启动配置针对 OpenCL。一批查询最长等待 40 秒（每多一个局面加 5 秒），一次讲解整体分析期限 150 秒。后台一次只运行一个分析任务。引擎进程在两次讲解之间保持运行，连续讲解不必重新加载模型；空闲 5 分钟后或某次讲解失败后自动关闭。结果、原始请求和响应保存到 `runs/<时间>-<任务号>/`，只保留最近 30 次，更早的这类文件夹会自动删除（`runs/` 里的其他文件不受影响）。目前结果不自动保存到云端。

All four path arguments are optional. The order is: command-line argument, environment variable `KATAGO_EXPLAINER_ENGINE` / `MODEL` / `CONFIG` / `TUNER`, then discovery. Discovery looks for the engine, config, and model in a `KaTrain*` folder beside the project, and picks the newest 19×19 tuning file in `~/.katrain/opencltuning` that matches the model's channel count, without relying on a GPU name. With no tuning file the option is left unset and KataGo handles tuning itself (the first run may take much longer).

The current launch settings target OpenCL. A batch of queries waits at most 40 seconds (plus 5 seconds per extra position), within a 150-second analysis deadline per explanation. One analysis job runs at a time. The engine process stays running between explanations, so consecutive explanations do not reload the model; it is closed after five idle minutes or after a failed explanation. Results and raw protocol data are stored in `runs/<time>-<job-id>/`; only the latest 30 are kept and older folders of this kind are deleted automatically (other files in `runs/` are untouched). Results are not automatically sent to a cloud service.

```powershell
python -m unittest discover -s tests -v
```

上述单元测试无需 GPU；实际引擎验证需通过页面运行。发生错误时保留页面错误提示，检查本轮 `engine.log` 和 `error.json`。

Unit tests require no GPU. Use the page for real engine validation. On error, retain the message and check that run's `engine.log` and `error.json`.
