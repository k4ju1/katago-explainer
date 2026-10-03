# KataGo Explainer

基于反事实搜索与证据约束的围棋着法解释研究项目。

目标：用户导入 SGF 棋谱，比较 AI 推荐手与自己的着法，阅读能够通过棋盘事实和变化图复查的中文讲解。

**当前阶段：毕业设计实施方案 + 已运行的 KataGo Analysis Engine 接口探针。** SGF 复盘界面、语言模型讲解、主张验证器和完整 Agent 将按方案逐步开发。

## 现有成果

- [详细毕业设计方案](docs/围棋解释Agent_毕业设计方案.md)：范围、架构、候选比较、证据约束、数据集、基线实验和 12 周计划。
- [真实接口验证报告](docs/feasibility.md)：KataGo v1.18.1 / OpenCL 的实际分析字段、计时与限制。
- [接口探针](scripts/smoke_probe.py)：仅依赖 Python 标准库，运行一条 19 路局面并分别补搜两个候选。
- [真实请求](examples/probe_input.jsonl)、[真实响应](examples/probe_output.jsonl)、[结果摘要](examples/probe_summary.json)：三条实际请求及对应输出。

示例环境：RTX 5070 Laptop GPU、KataGo v1.18.1、`b10c384h6nbttflrs.bin.gz`。根搜索目标为 256 visits，两候选各 512 visits；整次探针约 8.344 秒。这个单局面低预算样例证明接口可用，不能代表产品延迟、最优着法或解释质量。

发布版替换了机器上的个人绝对路径；原始引擎响应和分析数值保留。

## 方法

```text
SGF/局面 → 未限制的根搜索 → 候选分别补搜 → 棋盘事实和变化差异
                                            ↓
中文讲解 ← 主张验证与关键反击复查 ← 结构化证据包
```

一选读取 `order=0`，不能自行按胜率排序。候选独立搜索只约束第一手，后续允许对手自由应对。每条棋理主张绑定证据，证据不足时降低表述强度或保留结论。

## 运行接口探针

开发验证环境为 Python 3.12。需要自行准备：

1. 可运行的 KataGo OpenCL 引擎。
2. 与引擎兼容的模型和 Analysis Engine 配置。
3. 与自己的 GPU、模型和棋盘尺寸匹配的 OpenCL 调优缓存。

引擎、模型和调优缓存由使用者在本机提供。本仓库不包含这些大文件；上游下载和配置说明见 [KataGo](https://github.com/lightvector/KataGo)。

Windows PowerShell 示例，替换成自己的真实路径：

```powershell
python scripts/smoke_probe.py `
  --engine 'C:\path\to\katago.exe' `
  --model 'C:\path\to\model.bin.gz' `
  --config 'C:\path\to\analysis.cfg' `
  --tuner 'C:\path\to\matching-opencl-tuning.txt'
```

输出默认写入 `runs/`，可通过 `--output-dir` 指定其他目录。每阶段最多 40 秒，分析整体有截止时间；结束或失败时清理引擎进程。探针不安装依赖、不下载模型、不修改提供的配置。

该探针面向当前验证过的 OpenCL 路线；CUDA/TensorRT 等后端需要另做适配。新的运行结果可能因搜索随机性、线程调度和硬件不同而变化。

## 研究计划

| 阶段 | 成果 |
| --- | --- |
| 1–3 周 | SGF 主线浏览、候选表、PV 播放 |
| 4–6 周 | 候选独立比较、棋盘事实、中文讲解 |
| 7–8 周 | 主张验证、追问、固定评测集 |
| 9–10 周 | 冻结版本、基线与消融实验、专家评审 |
| 11–12 周 | 工程修复、报告导出、论文和演示 |

研究重点：候选补搜和主张验证是否减少无依据讲解，以及效果改善增加多少计算成本。先做 30 个试标局面，再建立固定评测集；测试后修改的版本与论文冻结结果分开记录。

## 参考

- [KataGo Analysis Engine v1.18.1](https://github.com/lightvector/KataGo/blob/v1.18.1/docs/Analysis_Engine.md)
- [KaTrain](https://github.com/sanderland/katrain)
- [Streamlit](https://docs.streamlit.io/)
- [sgfmill](https://mjw.woodcraft.me.uk/sgfmill/doc/1.1.1/)
