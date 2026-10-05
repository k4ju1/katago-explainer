# Third-party notices / 第三方说明

KataGo and KaTrain are separate upstream projects. Their executables, models,
fonts and icons are not committed to this source repository. The Windows
portable release includes a verified copy of KaTrain's official folder build,
with the project's plugin installed. Complete upstream notices accompany that
release in `licenses/`; their sources are recorded in
[distribution notices](docs/distribution-licenses/README.md). The generated wooden
board and stone assets in `plugins/katrain/` are reproduced by
`scripts/build_skin_assets.py`.

KataGo 与 KaTrain 是独立的上游项目，程序、模型、字体和图标不提交到源码仓库。
Windows 便携发布包包含经校验的官方宿主文件夹版和本项目插件，完整第三方声明
随包保存在 `licenses/`，来源见上述说明。
插件的木棋盘与棋子图片可通过 `scripts/build_skin_assets.py` 重新生成。

`tests/fixtures/katrain-1.20.0-gui.kv` is KaTrain v1.20.0's original layout,
used to verify the version-pinned, reversible integration. It is covered by
the following upstream notice. The integration's restyling in
`scripts/katrain_gui_patch.py` uses this layout.

测试中的 KV 文件是 KaTrain v1.20.0 的原始布局，用于验证版本固定、可恢复的
集成；下述上游声明适用于该文件及以其为基础的布局调整。

> Copyright 2020 Sander Land and/or other authors of the content in this repository.
> (See 'CONTRIBUTIONS.md' file for a list of authors as well as other indirect contributors).
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
> associated documentation files (the "Software"), to deal in the Software without restriction,
> including without limitation the rights to use, copy, modify, merge, publish, distribute,
> sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or
> substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
> NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
> NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
> DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Joseki terminology and short coordinate sequences are curated with source
links in [Joseki references](docs/JOSEKI_REFERENCES.md). External diagrams and
articles are not bundled.

定式术语和短坐标手顺的来源见[定式参考](docs/JOSEKI_REFERENCES.md)，不随仓库
分发外部棋图和文章。
