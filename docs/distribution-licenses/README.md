# Distribution notices / 分发声明

The portable release preserves KaTrain's official Windows folder build and
installs the project's explanation plugin into its UI. The host executable,
bundled Python/Kivy runtime, KataGo OpenCL executable and model are upstream
components, not independently developed by this project.

便携版保留 KaTrain 官方 Windows 文件夹版，在其界面中安装本项目的着法解释插件。
宿主程序、Python/Kivy 环境、KataGo OpenCL 引擎及模型均来自上游。

The builder copies this directory and the project's `THIRD_PARTY_NOTICES.md`
into the archive. It also preserves notices already in the official host,
including the font `OFL.txt` and runtime `LICENSE.*` / `COPYING.txt` files.
KaTrain's complete license includes icon attributions and the digital clock
font's non-commercial use condition; read `KaTrain-LICENSE.txt` for those terms.

打包时随附本目录和项目第三方声明，并保留官方包内已有的字体、运行库许可。
KaTrain 完整许可含图标署名和数字时钟字体的非商业用途条款，见 `KaTrain-LICENSE.txt`。

| File | Upstream source |
| --- | --- |
| KaTrain-LICENSE.txt | [KaTrain v1.20.0 LICENSE](https://github.com/sanderland/katrain/blob/v1.20.0/LICENSE) |
| KataGo-LICENSE.txt | [KataGo v1.18.1 LICENSE](https://github.com/lightvector/KataGo/blob/v1.18.1/LICENSE) |
| KataGo-Network-LICENSE.txt | [Official network license](https://katagotraining.org/network_license/) |
| CLBlast / Half / Filesystem / Httplib / Tclap notices | Respective files in [KataGo v1.18.1 cpp/external](https://github.com/lightvector/KataGo/tree/v1.18.1/cpp/external) |
| Nlohmann-JSON-LICENSE.txt | License header of [vendored json.hpp](https://github.com/lightvector/KataGo/blob/v1.18.1/cpp/external/nlohmann_json/json.hpp) |
| SHA2-LICENSE.txt | License header of [sha2.cpp](https://github.com/lightvector/KataGo/blob/v1.18.1/cpp/core/sha2.cpp) |
| Python-LICENSE.txt | [CPython 3.11 license](https://github.com/python/cpython/blob/v3.11.9/LICENSE) |
| Kivy-LICENSE.txt | [Kivy 2.3.0 license](https://github.com/kivy/kivy/blob/2.3.0/LICENSE) |

This is a provenance and notice collection, not a claim that all upstream
components share one license. Original component terms continue to apply.

本目录记录来源并汇集许可声明，各组件继续适用其原始许可。
