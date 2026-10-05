# KataGo Explainer

**看懂这一手，走完这条变化。**

基于 KataGo 的围棋着法解释与复盘插件。在 KaTrain 内比较实战手与 AI 一选，
用可重放的棋盘事实、搜索变化和定式参考回答“为什么这样下”。

**Understand the move. Follow the line.** An evidence-driven Go review plugin
embedded in KaTrain, with an interactive web demo sharing the same core.

[使用 / User guide](docs/USAGE.md) · [架构 / Architecture](docs/ARCHITECTURE.md) ·
[验证 / Validation](docs/EVALUATION.md) · [简历与演示 / Portfolio](docs/PORTFOLIO.md)

**[下载 Windows 便携测试版 / Download the Windows portable beta](https://github.com/k4ju1/katago-explainer/releases/tag/v0.2.0-beta.1)**

![Interactive web demo / 交互演示](docs/assets/preview.png)

*辅助网页演示；主入口为原生 KaTrain 插件。 / The web demo is shown here; the primary interface is the native KaTrain plugin.*

## Features / 核心体验

| 功能 / Feature | 实现 / Behavior |
| --- | --- |
| 先给结论 / Verdict first | 比较实战手与原始 AI 一选，显示胜率、目差及近似等价。 / Compare the played move and original first choice, including near-equal evaluations. |
| 逐手讲解 / Replay | 切换两条搜索变化，逐手播放棋盘与固定视角的评估。 / Replay both continuations with fixed-player evaluations. |
| 棋理有依据 / Evidence | 规则核验提子、打吃、连接和气数；区分搜索判断与推测。 / Rule-checked facts are separated from search assessments and tentative interpretations. |
| 定式与棋语 / Joseki & terms | 七项精选参考，包含尖顶、秀策尖、托退、芈氏飞刀外扳入口；附中文棋语、手顺与出处。 / Seven sourced references with Chinese terminology and sequences. |
| 原生集成 / Native | 复用 KaTrain 的引擎，保留棋谱树，安装可恢复。 / Share the host engine, preserve the game tree and support restoration. |

支持中英讲解；原生入口按钮跟随 KaTrain 界面语言。网页支持 SGF 上传、自选候选与经典样例。

Chinese/English explanations share the same evidence. Native buttons follow
KaTrain's language; the web demo supports SGF import, custom candidates and samples.

## Start / 开始使用

下载上述发布页 **Assets** 中的 `KataGo-Explainer-v0.2.0-beta.1-win64.zip`，完整解压，
双击 `START_KATAGO_EXPLAINER.cmd`。已包含 KaTrain、KataGo、模型和插件，无需安装 Python。
需要 Windows 10/11 64 位和支持 OpenCL 的显卡驱动；首次启动可能需要调优。

Download the ZIP from the release's **Assets**, extract it completely and double-click
the launcher. The Windows x64 beta includes the host, engine, model and plugin;
no separate Python installation is required. An OpenCL-capable driver is needed.

以下为源码开发与手动安装方式。 / For source development or manual installation:

需要 Python 3.11+ 进行安装；原生运行使用 KaTrain 自带环境。固定支持
**KaTrain v1.20.0 Windows 文件夹版**，程序与模型自行准备。

Python 3.11+ is needed for installation; native execution uses KaTrain's bundled
environment. The target is the **KaTrain v1.20.0 Windows folder build**.

```powershell
python scripts/launch_katrain.py --katrain-dir 'C:\path\to\KaTrain'
```

本机已配置时可双击 `START_KATRAIN_EXPLAINER.cmd`。打开
`examples/shusaku-demo.sgf`，走到第 3 手黑 D5，点击“解释刚才一手”。

On the configured computer, use the `.cmd` launcher. Open the Shusaku sample,
advance to Black D5 at move three, and select “Explain last move”.

辅助网页：`python -m explainer.server --open-browser`。引擎配置与所有样例见[使用指南](docs/USAGE.md)。

For the optional web demo, run the command above. The guide covers engine paths and samples.

## Design / 设计

```mermaid
flowchart LR
  UI[KaTrain / Web] --> Position[SGF & position history]
  Position --> Search[KataGo analysis]
  Search --> Compare[Candidate & pass comparison]
  Compare --> Replay[Rules replay & position evaluation]
  Replay --> Evidence[Evidence + joseki reference]
  Evidence --> UI
```

核心仅用 Python 标准库；原生视图使用 KaTrain 自带 Kivy；网页采用 HTML、CSS、JavaScript，
无需构建工具。两种入口共用请求协议与解释流程。

The core uses the Python standard library, the native view uses KaTrain's Kivy,
and the web uses plain HTML/CSS/JavaScript without a build step.

## Verify / 验证

```powershell
python -m unittest discover -s tests -v
python scripts/validate_demo.py examples/mi-flying-dagger-demo.sgf --move 17 --repeat 2
```

单元测试无需 GPU；真实验证保存请求、响应和结果到 `runs/`。CI 配置覆盖 Windows/Linux
和 Python 3.11/3.12，实测范围与复现方法见[验证文档](docs/EVALUATION.md)。

Tests require no GPU. Real validation retains logs and results. The CI
configuration covers Windows/Linux and Python 3.11/3.12.

便携版由[发布工作流](.github/workflows/release.yml)从固定 SHA256 的官方包构建，
附来源记录和文件校验；[打包说明](docs/DISTRIBUTION.md)说明复现方法。

Portable builds verify the pinned official archive, retain provenance and checksums,
and can be reproduced using the distribution guide.

讲解由规则和证据模板生成，未接入语言模型。定式目录覆盖有限，搜索变化是参考路线，
有限预算的评估差异不能作为严格因果证明。原生接入依赖固定版本的界面资源。

Explanations use rules and evidence templates. Reference coverage is curated;
search lines are illustrative and finite-search differences are not causal proof.
Native integration is version-pinned.

[定式来源 / Joseki sources](docs/JOSEKI_REFERENCES.md) · [第三方声明 / Notices](THIRD_PARTY_NOTICES.md)
