---
tags: [slm, llm, qwen, llama-cpp, gguf, natural-language, xai]
aliases: [Small Language Models, Local LLM, Semantic Transducer, Offline AI]
---

# 🤖 Small Language Models (SLM) & Local LLM Integration

This document specifies CARINA's Small Language Model (SLM) subsystem located in [`src/slm/`](../src/slm). It details how CARINA generates forensic, publication-ready textual justifications from raw neural attribution tensors using localized, offline Large Language Models (e.g., **Qwen3 1.7B**, **Qwen2.5 1.5B/3B**, or **Llama-3.2 3B**) without external API calls or cloud dependencies.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🔍 See [Explainable AI & SAS](XAI_AND_SAS.md) | 📄 See [Report Blocks & Word](REPORT_BLOCKS_AND_TEMPLATES.md)

---

## 1. Architectural Philosophy: 100% Offline Forensic Privacy

In public municipal administration, sending traffic telemetry, incident logs, or intersection control data to commercial cloud APIs (OpenAI, Anthropic, Google Cloud) violates public data governance, privacy laws (LGPD/GDPR), and municipal sovereignty.

CARINA executes all natural language report synthesis **100% locally on-premise**:
- Runs via optimized C++ bindings (`llama-cpp-python`).
- Supports **4-bit and 8-bit GGUF quantization** (`Q4_K_M`, `Q8_0`).
- Consumes as little as **~1.5 GB to 3.5 GB of VRAM** (or CPU RAM with AVX-512 acceleration).
- Fully deterministic output via low-temperature sampling ($\tau \le 0.2$).

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
- Transforms numerical tuples `(queue_length=18, speed=12.4 km/h, veto=True)` into domain-specific traffic engineering prompts.
- Employs a fallback heuristic engine: if hardware lacks GPU/RAM or LLM weights are missing, generates deterministic rule-based engineering text without crashing.

### 2.2 Local Llama Transducer (`local_llama_transducer.py`)
Located in [`src/slm/local_llama_transducer.py`](../src/slm/local_llama_transducer.py):
- Wraps `llama_cpp.Llama` with thread-safe execution locks.
- Manages GPU layer offloading (`n_gpu_layers = -1` for full CUDA offload).
- Restricts generation length and temperature to prevent hallucinations.

### 2.3 Device & Resource Management (`device_manager.py` & `resource_manager.py`)
- [`src/slm/device_manager.py`](../src/slm/device_manager.py): Profiles available hardware (NVIDIA CUDA, ROCm, Apple Metal, or CPU threads).
- [`src/slm/resource_manager.py`](../src/slm/resource_manager.py): Automatically manages context windows ($2048$ to $4096$ tokens) and purges KV cache between report generation episodes.

### 2.4 Factual Revision Engine (`revision_engine.py` & `output_sanitizer.py`)
- [`src/slm/revision_engine.py`](../src/slm/revision_engine.py): Extracts numerical entities from generated prose and verifies that they strictly match the underlying SQL database values.
- [`src/slm/output_sanitizer.py`](../src/slm/output_sanitizer.py): Strips markdown tokens, extra whitespace, and repetitive loop artifacts.

---

## 3. Configuration & Model Vault Setup

Pretrained weights are stored in the local `Model_Vault/` directory:

```text
Model_Vault/
└── qwen3-1.7b-instruct-q4_k_m.gguf
```

Configuration in `config/settings.ini`:
```ini
[XAI]
enable_xai = true
model_name = Model_Vault/qwen3-1.7b-instruct-q4_k_m.gguf
vram_allocation_gb = 3.5
temperature = 0.15
context_window = 3072
```
