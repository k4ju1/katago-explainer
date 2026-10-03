# KataGo 解释 Agent：真实接口可行性验证

本报告只展示真实引擎输出和接口能力，没有调用语言模型，也没有生成或推断棋理。

状态：success。总耗时：8.3440 秒（包括环境查询、启动、搜索和进程清理）。

首轮在启动阶段发现 `-analysis-threads` 与配置中的 `numAnalysisThreads` 重复。已改为只通过 `-override-config` 设置 `numAnalysisThreads=1`，原配置保持原样。本文状态、计时和原始输出均来自修正后的本轮运行。

## 环境与输入

```text
KataGo v1.18.1
Git revision: 92ee95c0a4b25fec214da00951ab69e97e207729
Compile Time: Aug 23 2026 23:32:20
Using OpenCL backend
Compiled to support contributing to online distributed selfplay
NVIDIA GeForce RTX 5070 Laptop GPU, 8151 MiB, 582.05
```

模型：`<LOCAL_WORKSPACE>\KaTrain-1.20.0\KaTrain\_internal\katrain\models\b10c384h6nbttflrs.bin.gz`。
模型 SHA-256：`0ba27eced5180b3e3d0b898b280c541112989765e789d1eb6cd0d31b2b2c1229`。
配置：`<LOCAL_WORKSPACE>\KaTrain-1.20.0\KaTrain\_internal\katrain\KataGo\analysis_config.cfg`。
只读使用调优缓存：`<USER_PROFILE>\.katrain\opencltuning\tune13_gpuNVIDIAGeForceRTX5070LaptopGPU_x19_y19_c384_m192_h32_mv15.txt`。

19×19，Chinese 规则，贴目 7.5；所有胜率和目差均为黑方视角。
开局：黑 Q16、白 D4、黑 Q4、白 D16、黑 R14、白 C6、黑 F3、白 C14；当前黑方走。

单分析线程、4 搜索线程、最大 batch 8。根搜索 256 visits；取引擎 order=0 与 order=1，分别做 512 visits 的根节点单候选搜索。
`allowMoves` 的 `untilDepth=1` 只限制当前第一手，后续双方应手正常搜索。两个候选使用独立搜索树，但复用同一引擎的神经网络缓存。

## 原始排序与等预算候选验证

`order=0` 是引擎给出的第一选择；不可直接定义为原始 winrate 最大的候选。原始根搜索在候选之间分配的 visits 不相等。

| 手 | 原始 order | 原始 visits | 原始黑胜率 | 原始黑目差 | 独立 visits | 独立黑胜率 | 独立黑目差 |
|---|---:|---:|---:|---:|---:|---:|---:|
| O3 | 0 | 84 | 36.4982% | -0.7869 | 513 | 36.4671% | -0.7778 |
| R6 | 1 | 56 | 36.1269% | -0.8111 | 513 | 35.6072% | -0.8814 |

原始一选 O3 减二选 R6：
原始黑胜率差 0.3714 个百分点；等预算候选搜索后的黑胜率差 0.8599 个百分点。
原始黑目差之差 0.0242 目；等预算候选搜索后的黑目差之差 0.1035 目。

这些差异只描述本次低预算搜索结果；不能据此证明最优性、估计置信区间或解释因果棋理。

## 已实际取得的输出字段

顶层：`id`, `isDuringSearch`, `moveInfos`, `ownership`, `policy`, `rootInfo`, `turnNumber`。
候选：`edgeVisits`, `edgeWeight`, `lcb`, `move`, `order`, `ownership`, `playSelectionValue`, `prior`, `pv`, `pvEdgeVisits`, `pvVisits`, `scoreLead`, `scoreMean`, `scoreSelfplay`, `scoreStdev`, `utility`, `utilityLcb`, `visits`, `weight`, `winrate`。
根局面：`currentPlayer`, `rawLead`, `rawNoResultProb`, `rawScoreSelfplay`, `rawScoreSelfplayStdev`, `rawStScoreError`, `rawStWrError`, `rawVarTimeLeft`, `rawWinrate`, `scoreLead`, `scoreSelfplay`, `scoreStdev`, `symHash`, `thisHash`, `utility`, `visits`, `weight`, `winrate`。

目标根预算为 256，本轮实际 rootInfo.visits=259；单候选目标预算均为 512。表格记录实际候选 visits，probe_summary.json 也保留了各次实际 rootInfo.visits；请求上限与实际返回值不能直接视为完全相等。
policy 长度：362（361 个交叉点及 pass）；根 ownership 长度：361。
一选和二选的 ownership 长度：`{"O3": 361, "R6": 361}`。
PV 和 pvVisits 可以提供变化图与逐手搜索支持量；ownership 可以提供黑白归属预测的区域比较。它们还需要规则核验和反事实验证，才能支持自然语言棋理。

## 测得时长与适用范围

| 阶段 | 秒 |
|---|---:|
| root_including_cold_start | 4.1410 |
| forced_O3 | 1.8590 |
| forced_R6 | 1.8600 |

首个阶段包含冷启动；后续阶段复用进程和缓存。这是单个开局局面的接口验证，不能当作产品性能、平均延迟或复杂中盘耗时。
每阶段最多 40 秒，整体上限 90 秒；不会自动安装、下载或长时间调优。

进程清理：`{"method": "stdin_eof_graceful", "returncode": 0, "process_stopped": true, "reader_threads_stopped": true}`。
引擎 warning 数量：0。Warning 被记录，但不会被误当作最终分析响应。

## 文件

- `smoke_probe.py`：标准库探针，可通过 CLI 覆盖引擎、模型、配置、缓存和输出目录。
- `probe_input.jsonl`：真实请求；每行一条 JSON。
- `probe_output.jsonl`：未经改写的引擎标准输出；每行一条 JSON。
- `probe_summary.json`：环境、统计比较、计时、警告及清理状态。

## 引擎 stderr

```text
2026-10-03 17:50:47-0400: Running with following config:
conservativePass = true
maxVisits = 500
nnCacheSizePowerOfTwo = 18
nnMaxBatchSize = 8
nnMutexPoolSizePowerOfTwo = 16
nnRandomize = true
numAnalysisThreads = 1
numSearchThreads = 4
openclTunerFile = <USER_PROFILE>\.katrain\opencltuning\tune13_gpuNVIDIAGeForceRTX5070LaptopGPU_x19_y19_c384_m192_h32_mv15.txt
reportAnalysisWinratesAs = BLACK

2026-10-03 17:50:47-0400: Analysis Engine starting...
2026-10-03 17:50:47-0400: KataGo v1.18.1
2026-10-03 17:50:47-0400: nnRandSeed0 = 3793225005768187687
2026-10-03 17:50:47-0400: After dedups: nnModelFile0 = <LOCAL_WORKSPACE>\KaTrain-1.20.0\KaTrain\_internal\katrain\models\b10c384h6nbttflrs.bin.gz useFP16 auto
2026-10-03 17:50:47-0400: Initializing neural net buffer to be size 19 * 19 allowing smaller boards
2026-10-03 17:50:48-0400: Found OpenCL Platform 0: NVIDIA CUDA (NVIDIA Corporation) (OpenCL 3.0 CUDA 13.0.97)
2026-10-03 17:50:48-0400: Found 1 device(s) on platform 0 with type CPU or GPU or Accelerator
2026-10-03 17:50:48-0400: Found OpenCL Platform 1: AMD Accelerated Parallel Processing (Advanced Micro Devices, Inc.) (OpenCL 2.1 AMD-APP (3652.0))
2026-10-03 17:50:48-0400: Found 1 device(s) on platform 1 with type CPU or GPU or Accelerator
2026-10-03 17:50:48-0400: Found OpenCL Device 0: NVIDIA GeForce RTX 5070 Laptop GPU (NVIDIA Corporation) (score 11000300)
2026-10-03 17:50:48-0400: Found OpenCL Device 1: gfx1036 (Advanced Micro Devices, Inc.) (score 11000200)
2026-10-03 17:50:48-0400: Creating context for OpenCL Platform: NVIDIA CUDA (NVIDIA Corporation) (OpenCL 3.0 CUDA 13.0.97)
2026-10-03 17:50:48-0400: Using OpenCL Device 0: NVIDIA GeForce RTX 5070 Laptop GPU (NVIDIA Corporation) OpenCL 3.0 CUDA (Extensions: cl_khr_global_int32_base_atomics cl_khr_global_int32_extended_atomics cl_khr_local_int32_base_atomics cl_khr_local_int32_extended_atomics cl_khr_fp64 cl_khr_3d_image_writes cl_khr_byte_addressable_store cl_khr_icd cl_khr_gl_sharing cl_nv_compiler_options cl_nv_device_attribute_query cl_nv_pragma_unroll cl_nv_d3d10_sharing cl_khr_d3d10_sharing cl_nv_d3d11_sharing cl_nv_copy_opts cl_nv_create_buffer cl_khr_int64_base_atomics cl_khr_int64_extended_atomics cl_khr_device_uuid cl_khr_pci_bus_info cl_khr_external_semaphore cl_khr_external_memory cl_khr_external_semaphore_win32 cl_khr_external_memory_win32 cl_khr_semaphore)
2026-10-03 17:50:48-0400: Loaded tuning parameters from: <USER_PROFILE>\.katrain\opencltuning\tune13_gpuNVIDIAGeForceRTX5070LaptopGPU_x19_y19_c384_m192_h32_mv15.txt
2026-10-03 17:50:50-0400: OpenCL backend thread 0: Model version 15
2026-10-03 17:50:50-0400: OpenCL backend thread 0: Model name: b10c384h6nbttflrs (nbt transformer, 10545753 params)
2026-10-03 17:50:50-0400: OpenCL backend thread 0: FP16Storage true FP16Compute false FP16TensorCores true FP16TensorCoresFor1x1 true
2026-10-03 17:50:50-0400: Loaded config <LOCAL_WORKSPACE>\KaTrain-1.20.0\KaTrain\_internal\katrain\KataGo\analysis_config.cfg and/or command-line and query overrides
2026-10-03 17:50:50-0400: Loaded model <LOCAL_WORKSPACE>\KaTrain-1.20.0\KaTrain\_internal\katrain\models\b10c384h6nbttflrs.bin.gz
2026-10-03 17:50:50-0400: Config override: nnCacheSizePowerOfTwo = 18
2026-10-03 17:50:50-0400: Config override: nnMaxBatchSize = 8
2026-10-03 17:50:50-0400: Config override: numAnalysisThreads = 1
2026-10-03 17:50:50-0400: Config override: numSearchThreads = 4
2026-10-03 17:50:50-0400: Config override: openclTunerFile = <USER_PROFILE>\.katrain\opencltuning\tune13_gpuNVIDIAGeForceRTX5070LaptopGPU_x19_y19_c384_m192_h32_mv15.txt
2026-10-03 17:50:50-0400: Analyzing up to 1 positions at a time in parallel
2026-10-03 17:50:50-0400: Started, ready to begin handling requests
2026-10-03 17:50:55-0400: <LOCAL_WORKSPACE>\KaTrain-1.20.0\KaTrain\_internal\katrain\models\b10c384h6nbttflrs.bin.gz
2026-10-03 17:50:55-0400: NN rows: 1110
2026-10-03 17:50:55-0400: NN batches: 557
2026-10-03 17:50:55-0400: NN avg batch size: 1.99282
2026-10-03 17:50:55-0400: GPU -1 finishing, processed 1110 rows 557 batches
2026-10-03 17:50:55-0400: All cleaned up, quitting
```


发布说明：以上本机绝对路径已替换为环境占位符；真实分析数值和测试条件保留。
