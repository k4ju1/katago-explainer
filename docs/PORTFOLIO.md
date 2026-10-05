# 简历与演示 / Portfolio

**KataGo Explainer — 基于 KataGo 的围棋着法解释与复盘插件**

**Evidence-driven Go review embedded in KaTrain**

## Resume / 简历表述

以下描述已实现功能；作者与职责请按自己的实际参与情况调整。

These describe implemented work; attribute responsibilities according to your actual contribution.

- 基于 KataGo JSON 分析协议实现着法解释层，结合候选补搜、假设停一手对比与逐节点评估，
  输出附可播放变化的双语讲解。
  / Built a KataGo explanation layer combining re-search, pass comparisons and position evaluation with bilingual replay.
- 接入 KaTrain 原生界面并复用宿主引擎，通过祖先导出与结果指纹保留棋谱分支、拒绝过期分析，
  实现版本校验与事务回滚安装。
  / Integrated host-engine reuse, ancestry preservation, stale-result checks and reversible installation.
- 实现棋盘事实核验和七项有来源的定式前缀，支持八种对称变换及黑白交换；提供双语棋语、
  原生与网页演示、回归测试及跨平台 CI 配置。
  / Added rule-checked evidence, sourced symmetry-aware references, bilingual terms, demos, tests and CI configuration.

## Three-minute demo / 三分钟演示

1. **秀策尖**：解释黑 D5，先读结论，再看定式，说明传统名称与当前一选提供不同信息。
   / Start with Shusaku kosumi and distinguish a reference name from the engine recommendation.
2. **芈氏飞刀**：解释第 17 手 G6，播放实际应手，点击打吃或连接依据定位棋盘。
   / Replay the searched continuation and inspect rule-verified atari or connection evidence.
3. **复现**：切换替代分支与英文，展示曲线、验证摘要、共享核心与安装回滚测试。
   / Compare alternatives, switch language and show reproducible validation and integration tests.

应手与评估随搜索改变，演示以当轮输出为准。

Replies and values can vary; present the current result.

## Interview / 面试要点

解释工程取舍：一选来自 `order=0`，候选只限制首着，曲线固定同一方视角，弱访问尾部截断，
定式参照独立于搜索。失败仅取消自己的查询，预览不污染棋谱树，安装失败恢复原文件。

Discuss retaining the original ranking, first-move restrictions, fixed perspective,
PV trust and reference separation, plus cancellation, immutable preview and rollback.

避免声称训练模型、已证明解释准确率、完整定式库或通用低延迟；完成专家评测后再补质量指标。

Avoid claims of training, proven accuracy, complete reference coverage or general latency.
