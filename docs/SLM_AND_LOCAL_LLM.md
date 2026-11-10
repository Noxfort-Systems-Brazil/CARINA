---
tags: [slm, llm, qwen, llama-cpp, gguf, natural-language, xai]
aliases: [Small Language Models, Local LLM, Semantic Transducer, Offline AI]
---

# 🤖 Small Language Models (SLM) & Local LLM Integration

This document specifies CARINA's Small Language Model (SLM) subsystem located in [`src/slm/`](../src/slm). It details how CARINA generates forensic, publication-ready textual justifications from raw neural attribution tensors using localized, offline Large Language Models (primarily **Qwen3.5 2B** via `Qwen3.5-2B-UD-Q6_K_XL.gguf`, with fallback support for **Qwen2.5 1.5B/3B** or **Llama-3.2 3B**) without external API calls or cloud dependencies.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🔍 See [Explainable AI & SAS](XAI_AND_SAS.md) | 📄 See [Report Blocks & Word](REPORT_BLOCKS_AND_TEMPLATES.md)

---

## 1. Architectural Philosophy: 100% Offline Forensic Privacy

In public municipal administration, sending traffic telemetry, incident logs, or intersection control data to commercial cloud APIs (OpenAI, Anthropic, Google Cloud) violates public data governance, privacy laws (LGPD/GDPR), and municipal sovereignty.

CARINA executes all natural language report synthesis **100% locally on-premise**:
- Runs via optimized C++ bindings (`llama-cpp-python`).
- Supports **quantized GGUF models** (e.g. `Q6_K_XL`, `Q4_K_M`, `Q8_0`).
- Consumes as little as **~1.5 GB to 3.5 GB of VRAM** (or CPU RAM with AVX-512 acceleration).
- Fully deterministic output via greedy zero-temperature decoding ($\tau = 0.0$, `repeat_penalty = 1.05`).

```text
 Captum Integrated Gradients & Telemetry
                  │
                  ▼
      ┌───────────────────────┐
      │  semantic_transducer  │
      └───────────┬───────────┘
                  │
       ┌──────────┴──────────┐
       ▼                     ▼
┌──────────────┐      ┌──────────────┐
│prompt_builder│      │device_manager│ (Calculates VRAM / Offloading layers)
└──────┬───────┘      └──────┬───────┘
       │                     │
       └──────────┬──────────┘
                  ▼
      ┌───────────────────────┐
      │local_llama_transducer │ (Executes Qwen GGUF model via llama.cpp)
      └───────────┬───────────┘
                  │
       ┌──────────┴──────────┐
       ▼                     ▼
┌───────────────┐     ┌───────────────┐
│output_sanitizer│    │revision_engine│ (Cross-validates text against telemetry)
└───────────────┘     └───────────────┘
```

---

## 2. Core Modules in `src/slm/`

### 2.1 Semantic Transducer (`semantic_transducer.py`)
Located in [`src/slm/semantic_transducer.py`](../src/slm/semantic_transducer.py):
- Serves as the primary public interface for textual explanation generation.
- Defaults to `Model_Vault/Qwen3.5-2B-UD-Q6_K_XL.gguf` with context window `n_ctx = 8192`.
- Transforms numerical tuples `(queue_length=18, speed=12.4 km/h, veto=True)` into domain-specific traffic engineering prompts.
- Employs a fallback heuristic engine: if hardware lacks GPU/RAM or LLM weights are missing, generates deterministic rule-based engineering text without crashing.

### 2.2 Local Llama Transducer (`local_llama_transducer.py`)
Located in [`src/slm/local_llama_transducer.py`](../src/slm/local_llama_transducer.py):
- Wraps `llama_cpp.Llama` with thread-safe execution locks.
- Manages GPU layer offloading (`n_gpu_layers = -1` for full CUDA offload).
- Executes greedy decoding (`temperature = 0.0`, `repeat_penalty = 1.05`) with dynamically clamped token limits to prevent hallucinations and repetition loops.

### 2.3 Device & Resource Management (`device_manager.py` & `resource_manager.py`)
- [`src/slm/device_manager.py`](../src/slm/device_manager.py): Profiles available hardware (NVIDIA CUDA, ROCm, Apple Metal, or CPU threads).
- [`src/slm/resource_manager.py`](../src/slm/resource_manager.py): Automatically manages context allocations and purges KV cache between report generation episodes.

### 2.4 Factual Revision Engine (`revision_engine.py` & `output_sanitizer.py`)
- [`src/slm/revision_engine.py`](../src/slm/revision_engine.py): Extracts numerical entities from generated prose and verifies that they strictly match the underlying SQL database values.
- [`src/slm/output_sanitizer.py`](../src/slm/output_sanitizer.py): Strips markdown tokens, extra whitespace, and repetitive loop artifacts.

---

## 3. Configuration & Model Vault Setup

Pretrained weights are stored in the local `Model_Vault/` directory:

```text
Model_Vault/
└── Qwen3.5-2B-UD-Q6_K_XL.gguf
```

Configuration in `config/settings.ini`:
```ini
[REPORT_FORMATTING]
report_slm_device = auto
report_slm_gpu_layers = -1
xai_slm_device = auto
xai_slm_gpu_layers = -1
```

Inference parameters configured in [`semantic_transducer.py`](../src/slm/semantic_transducer.py):
- **Model Path:** `Model_Vault/Qwen3.5-2B-UD-Q6_K_XL.gguf`
- **Context Window (`n_ctx`):** `8192`
- **Temperature:** `0.0` (deterministic / greedy)
- **Repeat Penalty:** `1.05`
- **Max Output Tokens:** Dynamically calculated (`512` to `4096`)

---

<div align="center">
  <img src="assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
