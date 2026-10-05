# 使用指南 / User guide

主入口是 KaTrain 插件；辅助网页共用同一讲解流程，适合演示与开发。

KaTrain is the primary interface; the web demo shares the explanation core.

## KaTrain

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
