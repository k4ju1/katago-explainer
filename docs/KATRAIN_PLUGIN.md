# KaTrain 原生集成 / Native KaTrain integration

这是面向 **KaTrain v1.20.0 Windows 文件夹版**的实验性扩展。它借助外部 `gui.kv` 资源与冻结程序的 Python 导入机制接入讲解面板，并非 KaTrain 官方提供的稳定插件 API。

This experimental extension targets the **KaTrain v1.20.0 Windows folder distribution**. It uses the external `gui.kv` resource and the frozen application's Python import mechanism to attach an explanation panel. It is not an official, stable KaTrain plugin API.

此前的原生版本已通过用户协助的操作验收：原有 KaTrain v1.20.0 冻结程序成功启动，用户确认棋盘与两个讲解按钮可见；发起原生讲解请求后，弹窗显示讲解、棋盘和胜率。源码、安装目录及冻结归档检查用于验证接入机制，核心流程也已运行真实 KataGo 并通过自动测试。这些记录不等同于自动化的原生界面验收，不包含随后新增的定式参考显示等功能的人工验收，也不代表讲解已完成专家评测。

An earlier native build passed a user-assisted acceptance check: the original frozen KaTrain v1.20.0 executable opened, the user confirmed the board and two explanation buttons, and a native explanation request displayed an explanation, board, and winrate in the popup. Source, installation layout, and archive checks establish the integration mechanism; the core also ran against the real KataGo engine and passed automated tests. These records are not automated native-UI acceptance tests, do not include manual acceptance of later additions such as the joseki reference display, and are not an expert evaluation of explanation quality.

本次保存的原生请求结果为 9 路实战手 C8，耗时 12.875 秒；两条分支各保存 7 个棋盘快照（含初始局面），引擎进程与读取线程均已结束。这条记录对应实战手讲解路径；平均性能和讲解质量仍需更广泛的评测。

The saved native-request result explains the played move C8 on a 9×9 board in 12.875 seconds. Each of two branches contains seven board snapshots, including the starting position; the engine and reader threads were stopped. This record covers the played-move explanation path. Average performance and explanation quality still require broader evaluation.

## 使用流程 / User workflow

1. 首次安装或卸载前，先关闭正在运行的 KaTrain。集成启动器会调用安装器；需要单独安装时，在项目目录运行 `python scripts/install_katrain_plugin.py`。
   Close KaTrain before installing or uninstalling. The integrated launcher calls the installer. To install separately, run `python scripts/install_katrain_plugin.py` from the project folder.
2. 双击项目根目录的 `START_KATRAIN_EXPLAINER.cmd` 启动集成入口。扩展使用本机 `127.0.0.1:8788` 上的讲解服务，并按需自动启动后台服务。
   Double-click `START_KATRAIN_EXPLAINER.cmd` in the project root. The extension uses the local explanation service at `127.0.0.1:8788` and starts the backend automatically when needed.
3. 在 KaTrain 中打开棋谱、选择一手，使用原生讲解面板解释这手实战着法；也可以解释当前局面的 AI 一选。当前节点的真实历史直接传给讲解服务，无需再次上传 SGF。
   Open a game and select a move in KaTrain. Use the native explanation panel to explain that recorded move, or request the AI first choice for the current position. The selected node's real history is passed directly to the service; no SGF re-upload is needed.
4. 等待 KataGo 分析，在 KaTrain 的原生弹窗中阅读中英讲解，切换候选分支，逐手播放变化并查看曲线。
   Wait for KataGo analysis, then read the bilingual explanation in a native KaTrain popup. Switch candidate branches, advance through the variation, and inspect its evaluation curve.

右侧两个讲解按钮跟随 KaTrain 当前选择的界面语言。弹窗提供独立的中文／英文切换；切换语言时，搜索结果、棋盘快照和数值不变。

The two dock buttons follow KaTrain's selected interface language. The popup has a separate Chinese/English switch; changing language retains the same search results, board snapshots, and values.

19 路局面匹配参考目录中的角部手顺时，弹窗增加“定式关联”和专业术语释义：包括名称、本手角色与有条件的目的说明、参考手顺、出处和上下文说明，★ 标注本次讲解手。真实落子顺序与仅有相同棋形的初始摆子分别标注；参考手顺与引擎候选变化分开。当前收录七项精选参考，包括秀策尖、尖顶、托退和芈氏飞刀的一个外扳分支，支持旋转、镜像与黑白互换；未匹配时不显示该区块。来源与限制见[定式参考说明](JOSEKI_REFERENCES.md)。

When a 19×19 position matches a cataloged corner sequence, the popup adds a joseki reference and professional terminology: its name, move role and conditional purpose, reference sequence, sources, and context notes. ★ marks the explained move. Actual move order is labeled separately from an equivalent setup diagram; reference sequences stay separate from engine candidate variations. The catalog has seven curated entries, including Shusaku kosumi, kick, attachment and retreat, and one Mi flying dagger outside-hane branch, with rotations, reflections, and color reversal. The block is hidden when there is no match. See [Joseki references](JOSEKI_REFERENCES.md) for sources and limits.

定式测试步骤：在 KaTrain 打开项目的 `examples/joseki-demo.sgf`，前进到第 5 手黑 E3 落下后的节点，再点击“解释刚才一手”。应出现“星位点三三：传统扳长前缀”，E3 以二子头扳的角色给出有条件的作用说明，并显示参考出处与术语。★ 应标在参考第 5 手；第 6、7 手仅是后续参照。本例不要求 E3 成为 KataGo 一选，也不表示这项新增功能已经完成人工原生验收。

For a joseki test, open the project's `examples/joseki-demo.sgf` in KaTrain, advance to the node after move five, Black E3, and click “Explain last move”. Expect the traditional star-point 3-3 prefix, a conditional explanation of E3's hane role at the head of two stones, sources, and terms. ★ should mark reference move five; moves six and seven are later reference steps. The test does not require E3 to be KataGo's first choice and does not constitute completed manual native acceptance of this addition.

其他经典样例：打开 `examples/shusaku-demo.sgf` 后选第 3 手黑 D5；`kick-demo.sgf` 选第 3 手黑 E3；`attach-retreat-demo.sgf` 选第 5 手黑 D3；`mi-flying-dagger-demo.sgf` 选第 17 手黑 G6。每次选中目标手落下后的节点，再点“解释刚才一手”。网页也可通过“经典棋形”下拉框与“定式示例”按钮自动定位。完整测试表见[使用说明](USAGE.md)。芈氏飞刀只覆盖所列外扳分支，征子和全局适用性仍需实际分析。

Other classic samples: select move three, Black D5, in `examples/shusaku-demo.sgf`; move three, Black E3, in `kick-demo.sgf`; move five, Black D3, in `attach-retreat-demo.sgf`; and move seventeen, Black G6, in `mi-flying-dagger-demo.sgf`. Select the node after the target move and click “Explain last move” each time. The web “Classic pattern” dropdown and “Joseki example” button locate these targets automatically. See the full [testing table](USAGE.md). The Mi entry covers only its listed outside-hane branch; ladder and whole-board suitability still require actual analysis.

实际搜索变化的后续手若精确匹配，也可获得自己的角色说明；未走的参考手不作为本局证据。这些新增功能的测试说明与此前提子界面的原生验收记录分开。

Later moves in an actual searched variation can receive their own role explanation if they match exactly; unplayed reference moves are not evidence for this game. These new-feature testing instructions are separate from the earlier native capture-UI acceptance record.

实战手讲解以该着落下前的局面为起点；AI 一选讲解以发起分析时选中的局面为起点。弹窗回放使用这次结果保存的确切棋盘快照；每个节点的曲线值来自该局面的独立搜索，并固定为被讲解着法的执棋方视角。切换 KaTrain 当前节点后，原有结果仍对应发起分析时的局面，应重新发起请求以讲解新局面。

A recorded-move explanation starts from the position immediately before that move; an AI-choice explanation starts from the position selected when the request is made. Popup playback uses the exact board snapshots saved with that result. Each curve point comes from a separate search of that position and keeps the explained player's perspective fixed. After selecting a different KaTrain node, an existing result still belongs to its original position; start a new request for the new position.

## 安装与恢复 / Installation and restoration

安装器备份原始 `gui.kv` 并记录安装状态，然后加入固定位置的 KV 导入与界面接入内容，将名称唯一的纯 Python 扩展包放到 KaTrain 的 `_internal` 下。`KaTrain.exe` 本身保持原样。重复安装应通过安装器处理，不要手动叠加 KV 修改。

The installer backs up the original `gui.kv` and records installation state. It adds the pinned KV import and UI hook, and copies a uniquely named pure-Python extension package beneath KaTrain's `_internal` directory. `KaTrain.exe` remains unchanged. Use the installer for repeated installation instead of manually stacking KV edits.

卸载时关闭 KaTrain，并在项目目录运行：

Close KaTrain, then uninstall from the project folder:

```powershell
python scripts/install_katrain_plugin.py --uninstall
```

卸载器根据备份与安装记录恢复原始 KV 并移除扩展。保留安装器创建的备份，避免直接覆盖其他人后来修改过的界面文件。若版本或文件校验不符，先查看安装器提示，不要绕过检查强行应用补丁。

The uninstaller uses the backup and installation record to restore the original KV and remove the extension. Keep the installer's backup and avoid overwriting later UI edits. If the version or checksum does not match, inspect the installer message instead of forcing the patch.

兼容检查针对原始 `_internal/katrain/gui.kv` 的 SHA-256：

Compatibility is pinned to the original `_internal/katrain/gui.kv` SHA-256:

```text
0c015263cd52305c9d64812c1d013173e69a4e4a131f40847d9bbe455936e9df
```

此值在本机 KaTrain 安装目录和 v1.20.0 源码中的 KV 文件一致。更新 KaTrain 后应重新审核资源与接入位置，不能将该补丁直接视为适用于其他版本。

The installed KV and the v1.20.0 source KV have this same hash on this computer. Re-audit the resources and hook locations after upgrading KaTrain; this patch is not automatically compatible with other versions.

## 开发说明 / Developer notes

- KaTrain 的 `build()` 使用 `find_package_resource("katrain/gui.kv")` 与 `Builder.load_file()` 读取文件；构建配置将它作为外部数据放在 `katrain/` 中。文件夹版对应 `_internal/katrain/gui.kv`。
  KaTrain's `build()` resolves `katrain/gui.kv` and loads it through `Builder.load_file()`. Its build specification collects it as external data under `katrain/`, which maps to `_internal/katrain/gui.kv` in this distribution.
- 已安装 EXE 的冻结归档包含 `PyiFrozenFinder` 及文件系统 fallback。名称不与冻结包冲突的新扩展包可以通过 `_internal/<package>/__init__.py` 导入；KV 使用 `#:import Alias <package>.<attribute>` 引用桥接对象。
  The installed executable contains `PyiFrozenFinder` with a filesystem fallback. A new package with a unique name can be imported from `_internal/<package>/__init__.py`; KV can reference its bridge object using `#:import Alias <package>.<attribute>`.
- KV 导入指令在界面实例建立前执行。导入模块本身应轻量，界面接入需等待对象就绪，例如通过 Kivy `Clock` 调度；不要在导入时直接假设 `app.gui` 已存在。
  KV imports run before UI instances are created. Keep module imports lightweight and wait for the target object before attaching widgets, for example through Kivy `Clock`; do not assume `app.gui` already exists at import time.
- 冻结程序使用 Python 3.11，Kivy 扩展为 `cp311`。桥接代码应兼容 Python 3.11，并复用冻结程序已有模块。不能用 Python 3.12 直接导入这些 Kivy 二进制扩展来验证界面。
  The frozen runtime uses Python 3.11 and Kivy binaries use the `cp311` ABI. Keep bridge code compatible with Python 3.11 and reuse available modules. Directly importing those Kivy binaries into Python 3.12 does not validate the native UI.

原生集成与网页入口共用讲解后端和同一证据格式。当前讲解由棋盘规则与证据模板生成；提子、气、连接和打吃可直接重放核对，位置性解读标为推测。主要变化是代表路径，有限预算下的胜率曲线不构成因果证明。深入棋理、语言模型推理和完整评测仍待开发；适用范围与限制见[使用说明](USAGE.md)。

The native integration and web entry share the explanation backend and evidence format. Explanations currently use board rules and evidence templates. Captures, liberties, connections, and atari can be verified through replay; positional interpretations are tentative. Principal variations are representative lines, and finite-budget curves are not causal proof. Deeper Go reasoning, language-model reasoning, and comprehensive evaluation remain future work. See the [User Guide](USAGE.md) for scope and limitations.

定式匹配使用当前节点的实际历史和棋盘状态，不需要另传棋谱。它提供知识参照，不修改 KataGo 一选排序或固定执棋方视角的评估。术语表也不是自动棋形分类器：提子与打吃可由规则核验，先手、厚势等词的释义不能直接证明本局取得了相应效果。当前没有完整定式数据库，也没有语言模型讲解。

Joseki matching uses the selected node's history and board state without another SGF upload. It supplies reference knowledge and does not alter KataGo's first-choice ranking or the fixed-player evaluation perspective. The glossary is not an automatic shape classifier: rules can verify captures and atari, while definitions of sente or thickness do not prove those effects in this game. There is no comprehensive joseki database or language-model explanation yet.

实现依据 / Implementation references: [PyInstaller frozen importer](https://github.com/pyinstaller/pyinstaller/blob/v6.14.1/PyInstaller/loader/pyimod02_importers.py), [Kivy KV parser](https://github.com/kivy/kivy/blob/2.3.1/kivy/lang/parser.py)。对应冻结归档的实际内容也已在本机检查；这些机制来源与上述用户协助的原生交互验收分开记录。

These sources explain the mechanism, alongside inspection of the actual local frozen archive; they are recorded separately from the user-assisted native interaction check above.
