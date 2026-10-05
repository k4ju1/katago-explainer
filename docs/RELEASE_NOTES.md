# KataGo Explainer v0.2.0-beta.2

Windows 10/11 x64 安装测试版 / Windows installer beta

## Download and start / 下载与启动

1. 打开[软件页面](https://k4ju1.github.io/katago-explainer/)，或
   [直接下载安装包](https://github.com/k4ju1/katago-explainer/releases/download/v0.2.0-beta.2/KataGo-Explainer-Setup-v0.2.0-beta.2-win64.exe)。
   / Open the software page or use the direct installer download.
2. 双击 `.exe`，选择中文或 English，按向导安装。
   / Open the `.exe`, choose a language and follow the wizard.
3. 点击桌面 **KataGo Explainer** 图标。安装完成后可打开秀策尖样例，
   等待引擎就绪，点击“解释刚才一手”。
   / Open the desktop icon. The post-install launch loads the Shusaku sample;
   wait for the engine and select “Explain last move”.

下载无需 GitHub 账号，运行无需 Python、服务器或另行下载模型。
内含 KaTrain 1.20.0、其 KataGo OpenCL 引擎与模型、讲解插件和经典棋谱。

No GitHub account, Python setup, server or separate model download is needed.
The installer includes the host, engine, model, plugin and classic SGF samples.

## New in this release / 本版更新

- 中英安装向导、桌面与开始菜单快捷方式，直接打开原生程序。
  / Bilingual installer and native desktop/Start-menu shortcuts.
- 当前用户安装，独立设置；更新及卸载保留现有偏好和未由安装器创建的棋谱。
  / Per-user installation with independent settings and preservation of user data.
- 首次语言跟随安装向导，安装完成即可体验秀策尖第 3 手讲解。
  / The initial language follows the wizard; a ready-to-explain Shusaku sample launches after setup.
- 安装包、便携 ZIP、SHA256 校验文件与构建来源记录。
  / Installer, portable ZIP, checksums and build provenance.

保留实战手与 AI 一选比较、变化回放、胜率与目差、中英讲解，以及尖顶、秀策尖、
托退和芈氏飞刀外扳入口等精选定式参考。

The release retains move/AI comparison, replay, evaluation changes, bilingual
evidence and sourced classic-shape references.

## Requirements and validation / 环境与验证

需要 Windows 10/11 x64 和支持 OpenCL 的显卡驱动；首次调优可能需要几分钟。
本版尚未签名，Windows 可能显示发布者未知。当前只打包 Windows，未完成多显卡验收。

Requires Windows 10/11 x64 and an OpenCL-capable driver. Initial tuning may take
several minutes. This unsigned beta may appear as an unknown publisher.
Other operating systems and broad GPU compatibility have not been validated.

178 项本机测试通过，真实安装器编译及静默安装、重装、卸载验证通过；
真实 KataGo 样例验证已完成。原生窗口视觉验收尚未完成。

All 178 local tests passed, along with real compilation and silent install,
reinstall and uninstall checks. The bundled engine has completed a real analysis
sample. Native visual acceptance remains unverified.

许可证随包保存于 `licenses/`。安装器使用 Inno Setup 6.4.3，并保留上游许可和
简体中文翻译来源。本项目是基于 KaTrain 与 KataGo 的独立集成版本。

Notices accompany the package, including Inno Setup 6.4.3 and the translation
attribution. This is an independent integration, not an official upstream release.
