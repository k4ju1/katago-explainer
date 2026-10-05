# Validation / 验证

自动回归、真实引擎样例和人工界面验收分别记录；接口可用不等于解释质量已被证明。

Regression, real-engine demos and manual UI acceptance are separate evidence.
Protocol success is not an explanation-quality score.

## Regression / 自动回归

```powershell
python -m unittest discover -s tests -v
```

无需 GPU 或额外 Python 依赖。覆盖规则与棋谱、评估视角、候选限制、PV 信任门槛、双语依据、
定式历史与对称、超时清理、原生分支导出与查询取消、安装校验回滚、网页资源契约。

GPU-free tests cover rules/SGF, metric perspective, restrictions, PV trust,
bilingual evidence, references, engine lifetime, native ancestry/cancellation,
installation transactions and web resources.

CI 覆盖 Windows/Linux 与 Python 3.11/3.12。
提交 `71193f2` 的[远端检查](https://github.com/k4ju1/katago-explainer/actions/runs/37251223040)
四项均通过，共 158 项测试。初次 Windows 检查曾因临时目录的短路径与完整路径比较不一致，
使模拟故障未触发；已用真实 Windows 短路径复现并修正测试目录解析。

All four remote jobs passed for that commit. The initial Windows failure was
in fault-injection tests: short temporary paths and canonical paths referred
to the same files but failed the comparison. It was reproduced and corrected.
The portable-release branch adds packaging checks; see [distribution](DISTRIBUTION.md).

便携测试版新增 10 项打包测试；整套 168 项本机回归通过。覆盖干净来源校验、
无私人文件、配置隔离、来源清单、失败清理和相同输入的字节一致性。

The portable beta adds ten packaging tests; all 168 tests passed locally,
including source integrity, isolated configuration, provenance, cleanup and reproducibility.

安装版 `0.2.0-beta.2` 再新增 10 项校验测试，本机完整回归 **178 项通过**。
真实安装器的静默安装、重复安装和卸载检查通过：388 个安装文件的 SHA256 与清单一致，
中文初始配置、桌面与开始菜单快捷方式正确；重复安装保留设置，卸载保留用户配置与自建棋谱。
这项检查不包含安装向导或当前原生棋盘的人工视觉验收。

The installer beta adds ten validation tests; all **178 tests passed locally**.
The compiled installer passed a real silent install/update/uninstall check: 388 installed
files matched their manifest hashes, Chinese configuration and both shortcuts were correct,
updates preserved preferences, and uninstall retained configuration and a user-created SGF.
This lifecycle check does not constitute visual acceptance of the wizard or current native board.

## Real engine / 真实引擎

```powershell
python scripts/validate_demo.py examples/mi-flying-dagger-demo.sgf --move 17 --repeat 2
```

可传入 `--engine`、`--model`、`--config`、`--tuner`。首次加载与热复用分别记录，
输出完整请求、响应、解释和简洁摘要到 `runs/`，默认不提交。

Explicit paths are supported. First-load and warm requests retain full protocol
data, explanations and a compact summary, ignored by Git by default.

2026-10-04 本机验证：Python 3.12.14、KataGo v1.18.1 OpenCL、
`b10c384h6nbttflrs.bin.gz`、RTX 5070 Laptop GPU。158 项自动测试通过。

Local validation on that date used the versions/model above and passed 158 tests.

| 样例 / Sample | 首次加载 / First load | 热复用 / Warm reuse | 结果 / Result |
| --- | --- | --- | --- |
| 芈氏飞刀，第 17 手黑 G6 / Mi, move 17 | 7.907 s | 0.860 s | 两条六手变化、外扳入口参照、原始一选 B5 / Two six-ply lines, the reference, original choice B5 |

这是一条固定样例的两次运行，不是平均性能指标。各轮根搜索与候选补搜使用当前架构预算；
结束后确认引擎退出码为 0、进程与读取线程均停止。摘要保存在本机
`runs/portfolio-validation/summary.json`，公开摘要见[验证记录](assets/validation.json)。

These are two runs of one fixed sample, not average latency. Engine exit code 0
and stopped process/readers were confirmed. The public summary retains the
measurements without machine-specific paths.

## Interface / 界面

网页使用实际浏览器检查中英切换、样例定位、异步状态、标签、逐手播放和窄屏布局；
`docs/assets/preview.png` 保存当前交互演示。

Browser checks cover languages, sample positions, async status, tabs, replay
and narrow-screen layout. The preview image records the current demo.

此前用户确认过原生棋盘、按钮和讲解弹窗可用；后续皮肤与参考功能的代码检查不能替代当前
版本的完整人工验收。原生自动检查覆盖桥接与安装，不包含专业棋手对解释质量的评分。

Earlier user-assisted checks confirmed the native board, buttons and viewer.
Later code checks do not replace full current-version manual acceptance;
native automated coverage targets integration, not expert explanation ratings.
