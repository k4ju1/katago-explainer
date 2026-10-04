# 定式参考与专业术语 / Joseki references and terminology

当前版本用七项精选角部参考，为讲解补充定式名称、着法术语和来源，包括秀策尖、尖顶、托退及芈氏飞刀的一个外扳分支。匹配所列手顺不表示该家族的全部变化或完整定式已经结束，也不证明这手是 AI 一选。KataGo 排序、候选胜率与棋盘核验仍使用本次真实分析结果。

The current version has seven curated corner references, including Shusaku kosumi, kick, attachment and retreat, and one Mi flying dagger outside-hane branch. Matching a stored line does not establish every variation in that family, a completed joseki, or an AI first choice. KataGo ranking, candidate evaluations, and board checks still use the actual analysis for this position.

## 收录范围与来源 / Catalog and sources

以下坐标统一写为 **19 路左下角、黑方先占角**的 GTP 坐标，省略字母 I；每一项从黑方开始交替落子。实际显示会转换到匹配的角部与颜色。数字为当前收录的前缀长度，不代表完整定式长度。

The coordinates below use **the lower-left corner of a 19×19 board, with Black taking the corner first**, in GTP notation without the letter I. Colors alternate from Black. Displayed references are transformed to the matched corner and colors. Lengths describe the stored prefixes, not complete joseki.

| 名称 / Name | 前缀 / Prefix | 来源 / Source |
| --- | --- | --- |
| 星位点三三：传统扳长前缀 / Star-point 3-3 invasion: traditional hane prefix | 7 手 / plies: `D4 C3 C4 D3 E3 E2 F3` | [Nordic Go Dojo：Antti，Sunday Problem #41](https://www.nordicgodojo.eu/post/693/sunday-problem-41)。依据作者评论中的常见点三三手顺取其开头；该死活题后来的棋形与劫结果不作为本项匹配结论。 / Uses the start of the author's listed 3-3 sequence; the later problem shape and ko outcome are not recognition claims. |
| 星位点三三：小飞分支前缀 / Star-point 3-3 invasion: knight-move branch prefix | 6 手 / plies: `D4 C3 C4 D3 F3 E3` | [OGS 定式探索器，节点 22017](https://online-go.com/joseki/22017)。该节点标注来源为 Yeonwoo Cho；这里只收录所列路线开头。 / The node attributes its source to Yeonwoo Cho; only the opening prefix is stored. |
| 尖顶定式：星位小飞挂角代表线 / Kick joseki: representative star-point low-approach line | 6 手 / plies: `D4 F3 E3 F4 D6 K3` | [OGS 定式探索器，节点 17781](https://online-go.com/joseki/17781)。该节点标注来源为曹薰铉《Lectures on Go Techniques》；当前项提供手顺和术语参照，不直接继承页面的先手或地域评价。 / The node attributes its source to Cho Hunhyun's *Lectures on Go Techniques*; its outcome labels are not inherited as claims about this game. |
| 小目小飞挂角入口 / 3-4 point knight-approach opening | 2 手 / plies: `C4 E3` | [英国围棋协会：Even Game Joseki, Part 1，图 2](https://britgo.org/bgj/00221.html)。仅识别小目与小飞挂角的入口，不收录后续夹击分支，也不将历史文章的评语视为现代引擎结论。 / Recognizes only the opening corner point and approach, without later pincer branches or treating historical commentary as a modern engine verdict. |
| 秀策尖：小目小飞挂角后的尖应法 / Shusaku kosumi: diagonal response to a 3-4 low approach | 3 手 / plies: `C4 E3 D5` | [日本棋院：寺山怜的古棋探访（1），图 1](https://www.nihonkiin.or.jp/etc/writer/column20250630.html)，并参考 [British Go Journal 105，页 19、图 16](https://www.britgo.org/files/bgj/bgj105.pdf) 的术语讲解。仅识别局部秀策尖，不识别完整秀策流布局。 / Nihon Ki-in's diagram 1 establishes the named move; BGJ 105, printed page 19, diagram 16 supplies teaching context. This is a local response, not recognition of a complete Shusaku opening. |
| 托退定式：实粘低拆分支 / Attachment-and-retreat joseki: solid connection and low extension | 8 手 / plies: `C4 E4 E3 F3 D3 F4 C6 K3` | [Pandanet《围棋笔记》：小目一间高挂，图 3](https://www.pandanet.co.jp/igonyumon/11-05.htm)，并参考 [日本棋院《围棋初心者 1：19 路盘》，页 100、图 4（PDF 第 6 页）](https://www.nihonkiin.or.jp/member/pdf/5-4_igoshoshin_1_19ro.pdf)。这里只收录实粘、拆一与低拆三代表线；虎接、高拆、脱先及侵入属其他分支。 / Pandanet diagram 3 and Nihon Ki-in's beginner guide, printed page 100, diagram 4 (PDF page 6), support this representative solid-connection and low-extension line. Hanging connection, high extension, tenuki, and invasions are other branches. |
| 芈氏飞刀：外扳分支入口 / Mi's Flying Dagger: outward-hane branch entry | 17 手 / plies: `D4 C3 D3 C4 C6 B6 B7 C5 D6 D5 E5 E4 E2 F4 F5 G5 G6` | [卢珂老师：芈氏飞刀，图 1、2](https://blog.newtonchineseschool.org/luke/2025/01/20/%E8%8A%88%E6%B0%8F%E9%A3%9E%E5%88%80/)；[《芈式飞刀》：芈昱廷九段／讲解，若水／文，页 76–83、图 17](https://ks3-cn-beijing.ksyun.com/attachment/fe692f120e2d926b033c440696074ee4)。只收录该外扳分支入口，不涵盖全家族；征子及全局条件不能由手顺匹配保证。 / Lu Ke's teaching diagrams and the authored article support this particular outside-hane branch entry, not the entire family or a favorable ladder/full-board judgment. |

以上中文名称与逐手作用说明是本项目的简短教学表述，不是来源页面的原文转载。没有抓取完整定式库、转载图表或复制长篇讲解。OGS 条目以其官方页面可索引的手顺与来源字段核对；直接打开页面需要 JavaScript，本次未作该站棋图截图核验。

The Chinese names and move-role descriptions are original short teaching labels. The project does not scrape a complete dictionary, reproduce diagrams, or copy long commentary. OGS entries were checked against the indexed move and source fields of their official pages; direct page loading requires JavaScript, and their board diagrams were not verified through screenshots in this check.

## 匹配与证据边界 / Matching and evidence limits

- **限定棋盘与局部配置。** 只用于 19 路棋盘。程序检查落子前后带颜色的局部棋子，要求与所列手顺完全一致；检查区域内多出配合子或其他棋子时不忽略它们。尖顶与托退代表线使用角部 11×11 检查区域，其余项使用 8×8 区域。仅下一颗星位或小目不足以命名定式；秀策尖与尖顶要走到第 3 手，托退要走到第 5 手，所列芈氏外扳分支要走到第 17 手才命名。提子手不属于当前目录。
  **Board and local configuration.** Only 19×19 boards are eligible. Colored local stones before and after the move must match the stored line exactly; extra support stones or other stones inside the checked area are not ignored. Kick and attachment-and-retreat entries use an 11×11 corner area; other entries use 8×8. A single opening stone is insufficient. Shusaku kosumi and kick are identified from move three, attachment and retreat from move five, and the listed Mi outside-hane branch only at move seventeen. Capturing moves are outside this catalog.
- **旋转、镜像与颜色。** 八种棋盘对称变换覆盖四角和两种方向，再整体交换黑白与逐手角色。变换只作用于参照坐标和颜色，不反转评估视角、不改变引擎排序。
  **Symmetry and colors.** Eight board symmetries cover the corners and orientations; complete color reversal changes every referenced player and role together. These transforms affect reference coordinates and colors, not evaluation perspective or engine ranking.
- **顺序与棋形分别标注。** 有完整局部历史时，同时核对落子顺序与棋形；未提供历史，或初始摆子使开头若干手未记录时，只标注棋形对应。提供的局部历史被重排、含额外落子或与前缀不一致时，抑制匹配，即使最终摆出的棋形相似。
  **Order and shape are separate.** A complete local history is checked for both move order and shape. With no history, or initial setup stones omitting the start of the sequence, the result is labeled as a shape match only. Supplied local history that is reordered, contains extra moves, or conflicts with the prefix suppresses recognition even if the final shape resembles it.
- **脱先与全局影响。** 停一手和检查区域外的着法不计入局部顺序，因此顺序吻合不表示全局每手连续发生。区域外棋子、征子条件和全局方向仍可能改变取舍；匹配器不据此前缀判断做活、先手、厚势、最终实地或征子结果。
  **Tenuki and whole-board context.** Passes and plays outside the checked corner area are omitted from local ordering, so a matching local order does not mean consecutive whole-board moves. Outside stones, ladder conditions, and direction of play can change the choice. The matcher does not infer life, sente, thickness, final territory, or ladder outcomes from a prefix.
- **共同开头不替未来选分支。** 两条点三三路线共享前四手，早期结果可能同时列出两个参考。★ 之后的参考手尚未因此被证明发生，也不代表 KataGo 推荐它们；实际应手看本轮候选变化。
  **A shared opening does not choose a future branch.** The two 3-3 references share their first four moves, so early results can list both. Reference moves after ★ are not established as played or recommended by KataGo; use this run's candidate variations for actual replies.

没有匹配只表示当前局面不在这个小目录中；不是“不是定式”或“下错了”的结论。当前没有完整定式数据库、定式优劣自动判定或语言模型讲解。

No match means the position is outside this small catalog, not that the move is non-joseki or wrong. There is no comprehensive joseki database, automatic joseki-quality judgment, or language-model explanation yet.

## 如何读讲解 / Reading the explanation

| 信息 / Information | 依据与用途 / Evidence and use |
| --- | --- |
| 棋盘事实与模板 / Board facts and templates | 规则重放核对提子、气、打吃和直接连接，再由模板组织中英文字。 / Rule replay checks captures, liberties, atari, and direct connections; templates organize the bilingual wording. |
| KataGo 搜索 / KataGo search | 原始 `order=0` 定义一选，独立候选搜索给出比较；逐局面重新评估得到曲线，视角固定为被讲解方。 / Original `order=0` defines the recommendation; separate candidate searches compare moves, and per-position searches supply the curve from the explained player's fixed perspective. |
| 定式参考 / Joseki reference | 已有角部手顺的名称、作用、来源及历史或棋形对应；不附本轮胜率，不与引擎 PV 混用。 / Names, roles, sources, and history or shape correspondence from reference sequences; no run-specific winrates or substitution for engine PVs. |
| 专业术语 / Terminology | 帮助读懂文字；术语定义本身不验证当前着法的效果。 / Definitions help read the explanation but do not verify the current move's effects. |

界面显示名称、角部、阶段、关联类型、本手作用、参考手顺、出处与说明。★ 表示当前讲解手；“前缀第几手”是局部参考编号，不是棋谱总手数。参考手顺与候选播放／胜率曲线是不同来源的数据。

The interface shows the name, corner, stage, relation, move role, reference sequence, sources, and notes. ★ marks the explained move; its prefix number is a local reference number, not the game move number. Reference sequences and candidate playback/winrate curves come from different sources.

实际搜索变化中的后续手可按累计历史精确匹配自己的角色，如变化真实走到 E2 才解释反扳；未走的参考步骤不作为本局证据。

Later moves in an actual searched variation may receive their own exact role match using accumulated history, such as a counter-hane explanation when E2 is actually played. Unplayed reference steps are not evidence for this game.

秀策尖与尖顶分别处理：`C4 E3 D5` 中，黑 D5 与己方 C4 成尖形，但不紧贴白 E3；`D4 F3 E3` 中，黑 E3 与己方 D4 成斜角关系，同时紧贴白 F3，才构成此代表线的尖顶。不能因为一手与己子斜接，就自动套用任一经典名称。日本棋院图 1 中，局部 `R16 P17 Q15` 对应全盘第 1、4、7 手；旋转后就是本项目的秀策尖三手。古棋中的无贴目背景与现代规则、贴目下的一选判断分别处理。

Shusaku kosumi and kick are handled separately. In `C4 E3 D5`, Black D5 is diagonal to friendly C4 without touching White E3. In `D4 F3 E3`, Black E3 is diagonal to friendly D4 and directly beside White F3, making the representative kick. Diagonal adjacency alone cannot assign either classic name. Nihon Ki-in's local `R16 P17 Q15` occurs at whole-board moves 1, 4, and 7 and rotates to the stored three-move Shusaku reference. Historical no-komi context is separate from recommendation under today's actual rules and komi.

芈氏飞刀的第 13 手 E2 是参照手顺中的尖入步骤，不能据此断言已经走出所收录的第 17 手外扳分支。匹配器要求辨识手已经落下；复杂变化的征子条件、断点和全局配合仍须通过实际变化或专项计算核对。托退也只代表所列一条路线；对方采用不同扳法、连接或外围配置时，不沿用这一分支的效果判断。

Move thirteen, E2, is the Mi reference's diagonal-entry step; it does not establish the stored move-seventeen outside-hane branch. The identifying move must be present. Ladder conditions, cuts, and whole-board support still require actual variations or dedicated reading. The attachment-and-retreat entry likewise represents one line; different hane replies, connections, or surrounding stones do not inherit that branch's outcomes.

`examples/joseki-demo.sgf` 提供传统点三三的 7 手样例。网页先在“经典棋形”下拉框选择“点三三”，再点击“定式示例”，自动选择第 5 手黑 E3；最后点击“解释这一步”。KaTrain 则打开该文件，选择第 5 手落下后的节点并点击“解释刚才一手”。应匹配传统扳长前缀，说明 E3 是二子头扳；AI 一选和实际数值仍由本轮引擎决定。秀策尖、尖顶、托退和芈氏外扳的样例文件与目标手数见[使用说明](USAGE.md)。

`examples/joseki-demo.sgf` provides a seven-move traditional 3-3 sample. On the web, choose “3-3 invasion” under “Classic pattern”, click “Joseki example” to select move five, Black E3, then click “Explain this move”. In KaTrain, open the file, select the node after move five, and click “Explain last move”. Expect the traditional hane prefix and E3's role at the head of two stones; the AI first choice and values still come from this engine run. The [User Guide](USAGE.md) lists files and targets for Shusaku kosumi, kick, attachment and retreat, and the Mi branch.

## 术语来源 / Glossary sources

专业中文名称包括定式、星位、小目、挂角、夹击、点三三、靠、扳、长、粘、尖、小飞、拆边、挡、反扳、尖顶、一间跳、拆三、打吃、气、劫、提子、先手、厚势及经典参考关联的术语。中文优先保留专业名称，英文提供对应词。释义为本项目的简短原创表述，参考以下协会资料及上列教学来源核对概念；涉及效果时保留条件，例如先手必须核对对手脱先的后果，厚势必须结合弱点与全局。

The glossary retains the Chinese professional names and supplies English equivalents. Definitions are original concise summaries checked against the association material below. Effect-based terms remain conditional: sente requires checking tenuki consequences, and thickness depends on weaknesses and whole-board context.

- [日本棋院：基本围棋术语 / Nihon Ki-in: Basic Go Terms](https://www.nihonkiin.or.jp/teach/lesson/school/yogo.html)
- [日本棋院：角部第一手 / Nihon Ki-in: Opening Corner Points](https://www.nihonkiin.or.jp/teach/lesson/school/joban01.html)
- [日本棋院：打吃与提子 / Nihon Ki-in: Atari and Capture](https://www.nihonkiin.or.jp/teach/lesson/school/atari.html)
- [日本棋院：劫 / Nihon Ki-in: Ko](https://www.nihonkiin.or.jp/teach/lesson/school/ko.html)
- [英国围棋协会：术语表 / British Go Association: Glossary](https://www.britgo.org/bgj/glossary.html)
- [英国围棋协会：术语释义 / British Go Association: Term Definitions](https://www.britgo.org/general/definitions.html)

## 开发字段 / Developer fields

`find_joseki(before, player, move, history=None)` 不修改棋盘或历史，接收落子前棋盘、当前执棋方、GTP 着点和该手之前的历史；历史可用 `[player, move]` 对或 `{player, move}` 字典表示。返回最多三项，按匹配前缀长度和 ID 稳定排序。

`find_joseki(before, player, move, history=None)` leaves the board and history unchanged. It takes the pre-move board, player, GTP move, and history before that move, as `[player, move]` pairs or `{player, move}` dictionaries. It returns at most three entries, ordered deterministically by matched prefix length and ID.

`explanation.joseki` 中每项含 `id`、双语 `name` / `corner` / `stage` / `relation` / `move_role` / `move_explanation`、`reference_line`、`sources`、`notes` 和 `term_ids`。`move_explanation` 是当前角色有条件的目的说明，同时加入 `explanation.reasons` 并标为 `level="reference"`；它不是规则核验或搜索结论。每个参考手含 `ply`、`player`、`move`、双语 `role` 与 `selected`；来源含双语 `title` 与 `url`。定式字段不含胜率或搜索次数。

Each `explanation.joseki` entry contains `id`, bilingual `name` / `corner` / `stage` / `relation` / `move_role` / `move_explanation`, `reference_line`, `sources`, `notes`, and `term_ids`. `move_explanation` conditionally describes the current reference role's purpose and is also included in `explanation.reasons` with `level="reference"`; it is not a rule-verified fact or search conclusion. Each reference move has `ply`, `player`, `move`, bilingual `role`, and `selected`; sources have bilingual `title` and `url`. Joseki fields contain no winrates or visit counts.

`explanation.terms` 使用 `get_terms(ids)` 的结果：`[{id, term: {zh, en}, definition: {zh, en}}]`。只解释请求且已收录的 ID，跳过未知项与重复项，保持首次出现顺序；不自动推断棋形。

`explanation.terms` uses `get_terms(ids)` output: `[{id, term: {zh, en}, definition: {zh, en}}]`. Only known requested IDs are included, unknown and duplicate IDs are skipped, and first occurrence order is retained. The glossary does not classify shapes automatically.
