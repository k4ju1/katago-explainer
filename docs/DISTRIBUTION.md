# Downloadable software / 可下载软件

First target: **Windows 10/11 x64 portable beta v0.2.0-beta.1**. This packages the
native integration rather than asking users to install Python and run a server.

首个目标为 Windows 64 位便携测试版，完整解压后直接打开原生棋盘和讲解功能。

## User entry / 用户入口

Download the product ZIP from the [release](https://github.com/k4ju1/katago-explainer/releases/tag/v0.2.0-beta.1)'s
**Assets**, extract all files and open `START_KATAGO_EXPLAINER.cmd`. Read the
bundled `QUICK_START.md`; sample SGFs are in `examples/`. The model and KataGo
engine are already present. A compatible OpenCL graphics driver is required.

下载产品 ZIP，不是 `Source code`；完整解压后双击启动器。无需安装 Python。
本仓库是私有仓库，当前 GitHub 下载需要有仓库访问权限；发布包不会改变仓库可见性。

The private repository's downloads require repository access. The launcher uses
`portable-config.json` in the extracted folder, independent of an older KaTrain
configuration. The original executable remains in `KaTrain/` for attribution
and upstream compatibility. Launch through the provided entry to use portable settings.

配置独立保存在包内。启动器会进入正确目录；宿主及驱动仍会在用户目录建立缓存或日志，
这不是完全无痕的运行环境。

## Build / 构建

The standard-library builder accepts only an exact clean copy of the official
KaTrain v1.20.0 Windows folder archive. It validates the archive SHA256, each
host file, pinned GUI, x64 executables and model format. Installation modifies
a temporary staging copy, leaving the source folder unchanged.

构建器核对官方 ZIP 和每个原始文件，只修改临时副本；不能使用本机已经装过插件的文件夹。

```powershell
Invoke-WebRequest 'https://github.com/sanderland/katrain/releases/download/v1.20.0/KaTrain.zip' -OutFile KaTrain.zip
Expand-Archive -LiteralPath KaTrain.zip -DestinationPath clean
python scripts/build_portable.py --katrain-dir clean/KaTrain --source-archive KaTrain.zip `
  --version 0.2.0-beta.1 --output-dir dist --commit YOUR_COMMIT_SHA
```

Expected upstream SHA256:
`2f74b00790e3c5ef424c19db92f5a94cb95dd109322b7ad052394c9e80d2fb22`.

The builder includes the current plugin/core, portable configuration, bilingual
quick start, examples, upstream notices and `build-manifest.json` with component
and file hashes. ZIP ordering/timestamps are fixed; repeated builds with the
same inputs produce the same bytes. Outputs include a `.zip.sha256` sidecar.

输出包含来源和逐文件校验信息，固定 ZIP 排序及时间戳；相同输入可得到相同字节的包。
不覆盖已有包，更新时选择新的版本号或输出目录。

## GitHub release pipeline / 发布流程

The [workflow](../.github/workflows/release.yml) first runs source checks and the
GPU-free suite, downloads and verifies the official host, then builds the ZIP.
A version tag publishes the ZIP and checksum as release assets only after those
steps succeed. Manual workflow dispatch builds an Actions artifact without
publishing a release. Release publication preserves the private repository's visibility.

版本标签触发构建并发布；手动运行只生成构建产物。测试或校验失败时不发布下载包。
源代码回归继续覆盖 Windows/Linux 与 Python 3.11/3.12。

## Acceptance scope / 验收范围

Automated checks validate provenance, packaging completeness, isolated settings,
checksums, rejected modifications and installer rollback. Real-engine validation
checks the bundled executable/model after extraction. These checks do not replace
manual native-window acceptance or testing on multiple graphics drivers.

自动验证覆盖文件完整性、独立配置、篡改拒绝和安装恢复；本机另行检查解压后真实引擎。
这是首个测试版，尚未完成不同电脑和显卡驱动的兼容性验收，也未制作安装向导或自动更新。
可优先请测试者完成“启动—打开棋谱—讲解—逐手回放—退出”后记录具体问题。

2026-10-04 本机从生成的 ZIP 解压后，直接使用包内引擎与模型分析秀策尖第 3 手 D5：
12.219 秒，返回两条 5/6 手变化和秀策尖参照；引擎正常退出，读取线程停止。
这是单一样例的引擎验证，不是原生窗口验收或跨硬件性能测试。

The extracted bundle's real KataGo/model completed the Shusaku move-three
pipeline in 12.219 seconds, returning five/six-ply lines and the sourced
reference. Engine exit code was zero and reader threads stopped. This single
sample proves engine integration, not manual GUI or cross-device acceptance.
