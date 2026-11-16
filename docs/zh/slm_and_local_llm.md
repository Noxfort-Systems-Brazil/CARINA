---
tags: [slm, llm, qwen, llama-cpp, gguf, natural-language, xai]
aliases: [端侧轻量大语言模型, 本地大模型, 语义转换器, 离线人工智能]
---

# 🤖 端侧轻量大语言模型 (SLM) 与本地大模型集成

本文档详尽规范了 CARINA 位于 [`src/slm/`](../../src/slm) 的端侧轻量大语言模型（Small Language Model, SLM）子系统。深入阐述了 CARINA 如何利用本地离线开源大语言模型（主要为 **Qwen3.5 2B**，通过 `Qwen3.5-2B-UD-Q6_K_XL.gguf` 驱动，备用支持 **Qwen2.5 1.5B/3B** 或 **Llama-3.2 3B**），在完全无需调用任何外部商业云端 API、零外部网络依赖的前提下，将底层神经网络敏感归因张量转化为符合法庭质证标准的出版级自然语言文本阐述。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🔍 查阅 [可解释人工智能与SAS](xai_and_sas.md) | 📄 查阅 [报告生成引擎](report_blocks_and_templates.md)

---

## 1. 架构核心理念：100% 离线私有化与司法数据主权

在市政公共交通治理与机要指挥调度领域，将城市道路路况遥测、交通硬件故障日志或信号控制决策数据发送至第三方公有商业云平台（如 OpenAI、Anthropic、Google Cloud 等），严重违反了公共数据主权治理法规、个人隐私保护法（LGPD / GDPR）以及国家关键基础设施安全准则。

CARINA 将所有报告自然语言文字论述的推理生成任务 **100% 约束在现场边缘物理服务器本地执行**：
- 基于经过高度汇编优化的 C++ 推理运行时（`llama-cpp-python`）。
- 全面支持 **GGUF 模型量化技术**（如 `Q6_K_XL`, `Q4_K_M`, `Q8_0`）。
- 仅需占用低至 **约 1.5 GB 至 3.5 GB 的显存 (VRAM)**（或在无独立显卡时通过 AVX-512 指令集直接在 CPU 内存中极速推理）。
- 采用贪婪零采样温度（$\tau = 0.0$、`repeat_penalty = 1.05`）实现严格确定性、可复现的工程论述输出。

```text
 Captum 积分梯度归因张量与微观遥测
                  │
                  ▼
       ┌───────────────────────┐
       │  semantic_transducer  │
       └───────────┬───────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
 ┌──────────────┐      ┌──────────────┐
 │prompt_builder│      │device_manager│ (动态计算显存占用 / 评估 GPU 卸载层数)
 └──────┬───────┘      └──────┬───────┘
        │                     │
        └──────────┬──────────┘
                   ▼
       ┌───────────────────────┐
       │local_llama_transducer │ (通过 llama.cpp 执行 Qwen GGUF 本地推理)
       └───────────┬───────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
 ┌───────────────┐     ┌───────────────┐
 │output_sanitizer│    │revision_engine│ (交叉核验大模型文本是否与 SQL 遥测数值完全吻合)
 └───────────────┘     └───────────────┘
```

---

## 2. `src/slm/` 核心功能模块

### 2.1 交通领域语义转换器 (`semantic_transducer.py`)
位于 [`src/slm/semantic_transducer.py`](../../src/slm/semantic_transducer.py)：
- 作为自然语言文本生成的主调度统一门面。
- 默认采用 `Model_Vault/Qwen3.5-2B-UD-Q6_K_XL.gguf` 模型，配置上下文窗口 `n_ctx = 8192`。
- 将微观数值元组 `(queue_length=18, speed=12.4 km/h, veto=True)` 转化为交通工程领域专用的结构化上下文提示词。
- 内置保底启发式引擎：若现场服务器显存不足或未挂载大模型权重文件，系统自动降级启用确定性规则专家库生成规范文本，绝不抛出异常。

### 2.2 本地 Llama 推理引擎 (`local_llama_transducer.py`)
位于 [`src/slm/local_llama_transducer.py`](../../src/slm/local_llama_transducer.py)：
- 封装 `llama_cpp.Llama` 运行时，提供严格的线程安全执行互斥锁。
- 自动化管理 GPU 算力层卸载（`n_gpu_layers = -1` 实现全量 CUDA 显存卸载）。
- 执行贪婪解码策略（`temperature = 0.0`、`repeat_penalty = 1.05`），配合动态限制的最大 token 输出，有效防止大模型幻觉与车轱辘话重复死循环。

### 2.3 设备、文件锁与资源管理层 (`device_manager.py`, `slm_lock.py`, `resource_manager.py`)
- [`src/slm/device_manager.py`](../../src/slm/device_manager.py)：优先通过轻量级 `pynvml` 查询空闲/总计 GPU 显存，随后再回退至 `torch.cuda`，避免各工作进程（`XAI_Worker`、`MFD_Worker`、`AnalysisService`）仅为探测显存而额外分配约 ~400 MB 的 PyTorch CUDA 上下文。
- [`src/slm/slm_lock.py`](../../src/slm/slm_lock.py)：提供可重入的跨进程建议性文件锁（`slm_process_lock()`，通过 `fcntl.flock` 作用于 `locks/slm_gguf.lock`），在 `XAI_Worker`、`MFD_Worker` 与 `AnalysisService` 之间串行化重型 2B GGUF 模型加载与推理，确保并发工作进程绝不争抢显存/内存。
- [`src/slm/model_loader.py`](../../src/slm/model_loader.py) 与 [`src/slm/resource_manager.py`](../../src/slm/resource_manager.py)：管理 GGUF 上下文配额分配、KV 缓存清理，并通过 `ReportTransducerFactory.release_transducer()` 执行确定性 `unload()`。在 `pytest` 测试环境下默认跳过真实 GGUF 加载，除非显式导出 `CARINA_ALLOW_REAL_SLM=1`。

### 2.4 文本真实性交叉审查引擎 (`revision_engine.py` 与 `output_sanitizer.py`)
- [`src/slm/revision_engine.py`](../../src/slm/revision_engine.py)：提取大模型输出中的所有数值实体，并与底层 SQL 数据库中的真实物理指标进行二次交叉核对。
- [`src/slm/output_sanitizer.py`](../../src/slm/output_sanitizer.py)：清洗输出文本，剔除冗余 Markdown 标记、非法空白字符与重复循环碎片。

---

## 3. 模型金库与系统配置 (`Model_Vault/`)

预训练权重文件统一存放在本地 `Model_Vault/` 目录：

```text
Model_Vault/
└── Qwen3.5-2B-UD-Q6_K_XL.gguf
```

在 `config/settings.ini` 中的配置项：
```ini
[REPORT_FORMATTING]
report_slm_device = auto
report_slm_gpu_layers = -1
xai_slm_device = auto
xai_slm_gpu_layers = -1
```

在 [`semantic_transducer.py`](../../src/slm/semantic_transducer.py) 中配置的推理超参数：
- **模型文件路径：** `Model_Vault/Qwen3.5-2B-UD-Q6_K_XL.gguf`
- **上下文窗口 (`n_ctx`)：** `8192`
- **采样温度：** `0.0`（确定性贪婪采样）
- **重复惩罚系数：** `1.05`
- **动态最大输出 Token：** 动态计算（`512` 至 `4096`）

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智慧交通移动工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本开源 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
