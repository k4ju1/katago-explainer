# 使用指南 / User guide

安装版把讲解功能放在 KaTrain 棋盘中。无需 GitHub 账号、Python 或命令行。

The app embeds the explanation viewer in KaTrain. No GitHub account, Python setup or terminal is needed.

## Install and start / 安装与启动

1. 打开[软件页面](https://k4ju1.github.io/katago-explainer/)，点击下载；也可以
   [直接下载安装包](https://github.com/k4ju1/katago-explainer/releases/download/v0.2.0-beta.2/KataGo-Explainer-Setup-v0.2.0-beta.2-win64.exe)。
   / Open the software page and download the installer, or use the direct download link.
2. 双击 `.exe`，选择中文或 English，完成安装。默认创建桌面快捷方式。
   / Open the `.exe`, choose a language and finish installation. A desktop shortcut is selected by default.
3. 点击桌面上的 **KataGo Explainer**，等待棋盘和引擎就绪。
   / Open **KataGo Explainer** from the desktop and wait for the board and engine.

安装向导最后的“打开 KataGo Explainer”会载入秀策尖第 3 手黑 D5。
首次引擎调优可能需要几分钟；就绪后点击“解释刚才一手”，查看讲解并逐手播放后续变化。
以后点击桌面图标可正常打开棋盘，载入自己的 SGF。

The post-install launch opens Shusaku's move-three Black D5 sample. Initial engine
tuning may take several minutes. Select “Explain last move” when ready and replay
the continuation. Later desktop launches open the normal app for your own SGFs.

支持 **Windows 10/11 x64**，需要支持 **OpenCL** 的显卡驱动。测试版尚未签名，
Windows 可能显示发布者未知。首次应用语言跟随安装向导；可在 KaTrain 设置中修改，
讲解窗口还可独立切换中英。更新安装会保留现有设置。

Requires Windows 10/11 x64 and an OpenCL-capable graphics driver. This unsigned beta
may be shown as an unknown publisher. The initial app language follows the wizard;
settings and the viewer allow language changes. Upgrades preserve existing preferences.

## Explain a move / 解释一手棋

1. 打开棋谱，选中目标手落下后的节点。
   / Load a game and select the position after the move you want to understand.
2. 点击“解释刚才一手”；“解释 AI 一选”则从当前局面分析引擎推荐。
   / Use “Explain last move”; “Explain AI choice” analyzes the current recommendation.
3. 左侧点击变化步骤或播放，右侧查看结论、依据、定式·术语与边界；依据可跳到对应棋盘。
   / Replay on the left and read the verdict, evidence, references and limits on the right.
4. 胜率和目差统一从窗口标注的棋手视角读取。
   / Read values from the fixed player perspective shown in the viewer.

若棋盘已打开但引擎无法启动，先更新显卡驱动，再查看 KaTrain 设置中的引擎状态。
卸载可从 Windows“已安装的应用”进入；用户设置和未由安装器创建的棋谱会保留。
打包与验证范围见[分发说明](DISTRIBUTION.md)。

If the board opens but the engine fails, update the graphics driver and check the
engine status in KaTrain settings. Uninstall through Windows' installed-apps list;
preferences and games not created by the installer are preserved.

## Portable option / 便携版选项

不希望安装时，可从[发布页](https://github.com/k4ju1/katago-explainer/releases/tag/v0.2.0-beta.2)
下载产品 ZIP，完整解压后双击 `START_KATAGO_EXPLAINER.cmd`。它读取包内设置。

For a portable copy, download the product ZIP from the release, extract the whole
archive and open its launcher. It uses its own configuration.

## Source development / 源码开发与手动集成

1. 准备 KaTrain v1.20.0 Windows 文件夹版与 Python 3.11+，安装前关闭 KaTrain。
   / Prepare the supported build and Python, then close KaTrain.
2. 运行 `python scripts/launch_katrain.py --katrain-dir 'C:\path\to\KaTrain'`。
   本机已配置时可双击 `START_KATRAIN_EXPLAINER.cmd`。
   / Run the launcher with your path; the configured computer also supports the `.cmd` entry.
3. 选中目标手落下后的节点，点击“解释刚才一手”；“解释 AI 一选”分析当前局面。
   / Select the node after the played move; AI choice analyzes the current position.
4. 左侧播放变化，右侧查看结论、依据、变化、定式·术语和边界。
   点击依据跳到对应棋盘；← → 逐手，Home/End 到两端，空格播放。
   / Replay on the left and inspect the tabs on the right. Reasons jump to evidence; arrows step and Space plays.

复用 KaTrain 的模型和引擎。两个入口按钮跟随应用语言；弹窗可独立切换中英。
更新代码后重新运行启动器。安装恢复见[集成说明](KATRAIN_PLUGIN.md)。

The plugin shares KaTrain's model and engine. Buttons follow the app language;
the viewer has its own Chinese/English switch. Re-run the launcher after updates.

## Web demo / 网页演示

```powershell
python -m explainer.server --open-browser
```

打开 `http://127.0.0.1:8788`。选择样例或上传 SGF，定位手数，选择实战手、AI 一选或空点候选，
点击分析。棋盘展示目标手之前的局面。引擎在连续讲解间保持运行，空闲五分钟或任务失败后关闭。

Open the local page, choose a sample or SGF, and select the move and analysis mode.
The board shows the pre-move position. The engine stays warm between requests and
closes after five idle minutes or failure.

```powershell
python -m explainer.server --engine 'C:\path\katago.exe' `
  --model 'C:\path\model.bin.gz' --config 'C:\path\analysis.cfg' `
  --tuner 'C:\path\tuning.txt' --open-browser
```

路径也可通过 `KATAGO_EXPLAINER_ENGINE`、`KATAGO_EXPLAINER_MODEL`、
`KATAGO_EXPLAINER_CONFIG`、`KATAGO_EXPLAINER_TUNER` 配置。省略时查找项目旁的
KaTrain 与用户调优目录。调优文件可省略，由 KataGo 处理；首次调优可能较慢。
独立引擎启动配置目前面向 OpenCL。

Paths can also use those environment variables. Discovery checks adjacent
KaTrain folders and user tuning files. Tuning is optional; first-time tuning
can be slow. Standalone launch settings currently target OpenCL.

## Demo positions / 演示棋谱

| 样例 / Sample | 文件 / File | KaTrain 目标节点 / Target node |
| --- | --- | --- |
| 提子 / Capture | [capture-demo.sgf](../examples/capture-demo.sgf) | 第 1 手黑 C8 / Move 1, Black C8 |
| 点三三 / Traditional 3-3 | [joseki-demo.sgf](../examples/joseki-demo.sgf) | 第 5 手黑 E3 / Move 5, Black E3 |
| 尖顶 / Kick | [kick-demo.sgf](../examples/kick-demo.sgf) | 第 3 手黑 E3 / Move 3, Black E3 |
| 秀策尖 / Shusaku kosumi | [shusaku-demo.sgf](../examples/shusaku-demo.sgf) | 第 3 手黑 D5 / Move 3, Black D5 |
| 托退 / Attach and retreat | [attach-retreat-demo.sgf](../examples/attach-retreat-demo.sgf) | 第 5 手黑 D3 / Move 5, Black D3 |
| 芈氏飞刀 / Mi's Flying Dagger | [mi-flying-dagger-demo.sgf](../examples/mi-flying-dagger-demo.sgf) | 第 17 手黑 G6 / Move 17, Black G6 |

网页样例自动选择对应实战手。芈氏飞刀仅覆盖外扳入口，秀策尖仅识别局部应对；
名称不证明完整定式、征子有利或当前最优。

Web samples select the intended move automatically. Mi covers one outside-hane
entry and Shusaku a local response; names do not establish optimal play.

## Reading the analysis / 如何读讲解

- **结论 / Verdict**：原始一选取自未限制搜索的 `order=0`；补搜可能显示近似等价或排序不稳定。
  / Retain the original first choice; re-search may reveal near-equality or unstable ranking.
- **数值 / Values**：固定被讲解方视角；候选差值与沿变化的重新评估分别展示。
  / Fix one player's perspective and separate candidate comparison from continuation changes.
- **依据 / Evidence**：棋盘事实可重放，搜索判断依赖当轮预算，推测有单独标记。
  / Board facts are replayable, search judgments are run-dependent and tentative interpretations are labeled.
- **变化 / Line**：每条最多六手，访问不足的尾部截断；换应手需重新分析。
  / Up to six plies, with weakly explored tails omitted; different replies need new analysis.
- **脱先对比 / Pass comparison**：假设停一手用于比较局部紧迫性，不是实战建议或先手证明。
  / Hypothetical passes probe urgency; they are neither advice nor proof of sente.
- **定式 / Joseki**：书本参照独立于实际搜索路线，详见[来源与匹配](JOSEKI_REFERENCES.md)。
  / Sourced reference sequences are separate from searched lines.

支持 9、13、19 路与 Chinese、Japanese、Korean、AGA 命名规则，最多 1000 手。
网页读取第一分支，KaTrain 读取选中分支；不支持的中途摆子修改或规则变体明确拒绝。
缺少规则或贴目会显示默认假设。

Supported board sizes and rules are listed above. Web imports follow the first
variation; KaTrain uses the selected ancestry. Unsupported edits/rules are rejected
and missing settings produce visible assumptions.

错误时检查引擎与模型。网页日志在 `runs/<时间>-<任务号>/`，保留最近 30 个任务目录；
其他文件不自动清理。原生错误在弹窗和 KaTrain 日志显示。

Check engine/model readiness on errors. Web logs retain the latest 30 job folders;
native errors appear in the viewer and KaTrain logs.
