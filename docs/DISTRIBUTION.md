# Downloadable software / 可下载软件

**Windows 10/11 x64 · v0.2.0-beta.2**

## Download and install / 下载与安装

1. 打开[软件页面](https://k4ju1.github.io/katago-explainer/)，点击 Windows 下载。
   / Open the software page and select the Windows download.
2. 双击安装包，选择中文或 English，完成安装。
   / Open the installer, choose a language and complete the wizard.
3. 从桌面 **KataGo Explainer** 图标启动；安装向导最后的“打开”选项可直接载入秀策尖样例。
   / Start from the desktop icon. The post-install launch opens the Shusaku sample.

[直接下载 EXE / Direct installer download](https://github.com/k4ju1/katago-explainer/releases/download/v0.2.0-beta.2/KataGo-Explainer-Setup-v0.2.0-beta.2-win64.exe)
· [发布页与便携包 / Release and portable archive](https://github.com/k4ju1/katago-explainer/releases/tag/v0.2.0-beta.2)

下载无需 GitHub 账号。安装包包括 KaTrain、KataGo、模型、讲解插件及经典棋谱，
无需配置 Python。需要支持 OpenCL 的显卡驱动；首次调优可能需要几分钟。
当前测试版尚未签名，Windows 可能显示发布者未知。

Downloads do not require a GitHub account. The installer includes the host,
engine, model, plugin and samples. No Python setup is needed. An OpenCL-capable
graphics driver is required; first-time tuning may take several minutes.
This unsigned beta may be shown as an unknown publisher.

## Installation behavior / 安装行为

安装范围为当前用户，默认路径为用户目录下的 `Programs/KataGo Explainer`，
不要求管理员权限。桌面和开始菜单快捷方式直接启动原生程序，不打开命令行窗口。
设置独立保存在 `portable-config.json`；首次语言跟随向导选择，更新保留已有设置。
宿主及显卡驱动仍可能在用户目录创建缓存和日志。

The per-user installer defaults to LocalAppData's Programs folder and does not
request administrator rights. Shortcuts launch the native app directly.
Preferences use an independent configuration and survive upgrades. The initial
language follows the wizard. Host/driver caches and logs may use the user profile.

Windows“已安装的应用”提供卸载入口。卸载保留设置及未由安装器创建的棋谱，
只清理安装器登记的文件。便携 ZIP 完整解压后使用包内启动器运行。

Uninstall through Windows' installed-apps list. Preferences and games not created
by the installer remain; only registered installation files are removed.
The portable ZIP is an alternative: extract it fully and use its launcher.

## Build from source / 从源码构建

便携构建器只接受官方 KaTrain v1.20.0 Windows 文件夹版的干净副本，核对
官方 ZIP SHA256、全部原始文件、界面资源、x64 程序和模型格式，只修改临时副本。

The standard-library builder verifies the official archive and every clean host
file, then installs the plugin into a staging copy. The source is never patched.

```powershell
Invoke-WebRequest 'https://github.com/sanderland/katrain/releases/download/v1.20.0/KaTrain.zip' -OutFile KaTrain.zip
Expand-Archive -LiteralPath KaTrain.zip -DestinationPath clean
python scripts/build_portable.py --katrain-dir clean/KaTrain --source-archive KaTrain.zip `
  --version 0.2.0-beta.2 --output-dir dist --commit YOUR_COMMIT_SHA
```

官方包预期 SHA256 / Expected official archive SHA256:
`2f74b00790e3c5ef424c19db92f5a94cb95dd109322b7ad052394c9e80d2fb22`.

安装器使用 **Inno Setup 6.4.3**。准备 `ISCC.exe` 后运行：

The GUI installer uses Inno Setup 6.4.3. With its compiler available:

```powershell
python scripts/build_installer.py `
  --portable-zip dist/KataGo-Explainer-v0.2.0-beta.2-win64.zip `
  --version 0.2.0-beta.2 --output-dir dist --iscc 'C:\path\to\ISCC.exe'
```

安装器构建前核对 ZIP 全部文件的 SHA256、版本、路径、宿主架构和独立配置。
简体中文向导使用仓库中固定的上游翻译。输出 `.exe`、`.exe.sha256` 和
`.exe.build.json`，后者记录来源提交、编译器、脚本及初始中英设置的哈希。

Before compilation, every recorded payload hash, layout, version and configuration
is verified. Outputs include the executable, checksum and build metadata with
source/compiler/script hashes and initial language variants.

便携 ZIP 的排序和时间戳固定，相同输入可得到相同字节。安装器记录可追溯来源，
不声称不同时间或不同编译器生成的 EXE 字节一致。构建器不覆盖已有产物。

Portable ZIPs are byte-reproducible for the same inputs. Installer metadata records
provenance; executable byte reproducibility across compilers/build times is not claimed.
Existing outputs are never overwritten by the builders.

## Release pipeline / 发布流程

[发布工作流](../.github/workflows/release.yml)先执行源代码检查和无需 GPU 的测试，
下载并校验官方宿主，构建便携包，再下载并校验固定版本的 Inno Setup，编译安装器。
版本标签发布安装包、便携包、校验文件和来源记录；手动运行只生成构建产物。
测试或来源校验失败时不发布。

The workflow checks sources and GPU-free tests, verifies the host and compiler,
then builds both formats. Tags publish download assets; manual runs produce
artifacts without a release. Failed checks stop publication.

## Validation scope / 验证范围

本机 **178 项测试通过**，真实 Inno Setup 安装器编译成功。真实静默安装测试通过：
388 个安装文件 SHA256 一致，中文初始配置与快捷方式参数正确；重复安装保留用户设置，
卸载清理程序、快捷方式和登记项，并保留设置与自建 SGF。

All 178 local tests passed and the real installer compiled. Silent installation
verified 388 installed-file hashes, language configuration and shortcut arguments.
Reinstallation preserved preferences; uninstall removed the runtime, shortcuts
and registration while retaining the user's configuration and SGF.

初始中英设置由安装器生成，哈希记录在 `.exe.build.json`。包内 `build-manifest.json`
记录便携来源；用户设置变化后，不应把配置差异误报为静态程序文件损坏。

Installer build metadata records the initial language variants. The bundled
portable manifest describes its source; a mutable preference file is not a
static runtime-integrity check.

此前从便携包解压后，包内真实 KataGo 与模型完成秀策尖第 3 手 D5 讲解：
12.219 秒，返回两条 5/6 手变化和秀策尖参考，引擎与读取线程正常停止。
这是一条固定样例的引擎验证，不代表平均性能。上述安装验证是静默生命周期检查；
原生窗口视觉验收和多台不同显卡电脑的兼容性测试尚未完成。

The extracted bundle's real engine/model completed one Shusaku sample in 12.219
seconds, returning five/six-ply lines and the reference, then shutting down cleanly.
This is one sample, not average latency. Installer validation covers the silent
lifecycle; native visual acceptance and broad GPU compatibility remain unverified.

## Notices / 许可与来源

安装器和便携包保留上游声明；完整来源见[分发许可说明](distribution-licenses/README.md)。
Inno Setup 6.4.3 许可随包附在 `licenses/Inno-Setup-LICENSE.txt`；
简体中文翻译来自官方仓库对应标签的
[ChineseSimplified.isl](https://github.com/jrsoftware/issrc/blob/is-6_4_3/Files/Languages/Unofficial/ChineseSimplified.isl)，保留原作者说明。

Both formats preserve upstream notices. The Inno Setup license is included;
the Simplified Chinese translation is pinned to the official repository's 6.4.3 tag
and retains its translator attribution.
