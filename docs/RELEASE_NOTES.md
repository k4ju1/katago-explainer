# KataGo Explainer v0.2.0-beta.1

Windows 64 位便携测试版 / Windows 64-bit portable beta

## Download and start / 下载与启动

1. Download `KataGo-Explainer-v0.2.0-beta.1-win64.zip` from **Assets** below.
   下载下方 **Assets** 中的同名 ZIP；`Source code` 是源码，不能直接运行。
2. Extract the whole archive into a writable folder; do not run it inside the ZIP.
   将整个压缩包解压到可写目录。
3. Double-click `START_KATAGO_EXPLAINER.cmd` inside the extracted folder.
   双击该文件，打开内置讲解功能的 KaTrain。
4. Open `examples/shusaku-demo.sgf`, go to move 3 (Black D5), then choose
   “Explain last move”. 打开秀策尖样例，走到第 3 手黑 D5，点击“解释刚才一手”。

Includes KaTrain v1.20.0, KataGo v1.18.1 OpenCL, the official transformer model,
the explanation plugin and classic SGF samples. No separate Python installation,
server or account is required. 内置宿主、引擎、模型、插件和经典棋谱，无需安装 Python。

## What this beta includes / 本版功能

- Compare the played move with AI's first choice; replay both continuations and
  their win-rate / score changes. 比较实战手与 AI 一选，逐手查看变化、胜率和目差。
- Chinese/English explanation and KaTrain-language-aware entry buttons.
  中英讲解，入口按钮跟随 KaTrain 选定语言。
- Sourced references for 尖顶、秀策尖、托退 and the 芈氏飞刀 outside-hane entry.
  经典棋形附手顺和出处；定式目录为精选参考。
- A separate portable configuration; existing KaTrain settings are preserved.
  使用独立设置文件，保留原有 KaTrain 的配置。

## Requirements and scope / 环境与范围

Windows 10/11 x64 and an OpenCL-capable graphics driver. Initial engine tuning
may take longer. If the board opens but the engine fails, update the graphics
driver and check KaTrain's engine settings. Only Windows is packaged in this beta.

需要 Windows 10/11 64 位和支持 OpenCL 的显卡驱动；首次启动可能需要引擎调优。
本版打包目标为 Windows，尚未完成多台不同配置电脑的兼容性验收。

`QUICK_START.md` covers usage and troubleshooting. The ZIP includes component
notices in `licenses/`, provenance and per-file checksums in `build-manifest.json`,
and a downloadable SHA256 sidecar. This is an independent integration based on
KaTrain and KataGo, not an official upstream release.

包内含中英说明、第三方声明和文件校验信息；本项目为独立集成版本。
