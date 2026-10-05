# KaTrain integration / 原生集成

固定目标为 **KaTrain v1.20.0 Windows 文件夹版**。通过外部 `gui.kv` 与独立 Python 包接入，
复用宿主的 KataGo 引擎，不依赖后台服务。操作流程见[使用指南](USAGE.md)。

The version-pinned integration attaches through external KV resources and a
separate package, sharing the host engine without a web service.

## Install / 安装

安装前关闭 KaTrain。安装器校验原始文件及已安装状态，备份布局，复制插件、核心与棋盘素材。
不修改可执行文件；重复安装用于更新，失败恢复之前的文件。

Close KaTrain first. The installer validates the layout and install state,
backs it up and copies the package. Executables are unchanged; failed updates roll back.

```powershell
python scripts/install_katrain_plugin.py --katrain-dir 'C:\path\to\KaTrain'
python scripts/launch_katrain.py --katrain-dir 'C:\path\to\KaTrain'
```

安装后可直接打开 KaTrain，原生运行不需要额外 Python 环境。

After installation, native execution does not need an external Python runtime.

## Restore / 恢复

```powershell
python scripts/install_katrain_plugin.py --katrain-dir 'C:\path\to\KaTrain' --uninstall
```

保留 `_internal/katrain/gui.kv.explainer-original` 和安装清单
`_internal/katrain-explainer-install.json`。其他工具修改过的界面不会被自动覆盖。
支持的原始布局 SHA-256：

Keep the backup and manifest. Later external UI edits are not overwritten.
The supported original layout's SHA-256 is:

```text
0c015263cd52305c9d64812c1d013173e69a4e4a131f40847d9bbe455936e9df
```

## Engine and board / 引擎与棋盘

桥接读取当前节点的真实祖先，保留规则、贴目、摆子与轮次，不混入兄弟分支。
分析请求使用高优先级、独立回调与期限，出错仅取消插件自己的查询。
变化使用只读快照，不向棋谱树追加演示着法；指纹拒绝局面改变后的过期结果。

The bridge exports selected ancestry with settings intact. High-priority requests
have independent callbacks and deadlines; failure cancels only owned queries.
Snapshot previews preserve the game tree; fingerprints reject stale results.

原生视图包含棋盘、播放、胜率曲线和五个讲解标签。主窗口皮肤与落子响应依赖版本限定的
布局和运行时适配，暂不承诺其他 KaTrain 版本。上游布局声明见[第三方说明](../THIRD_PARTY_NOTICES.md)。

The viewer includes replay, a curve and five inspector tabs. The main-window
skin and placement adapters are version-specific; other versions are not claimed.
