---
tags: [slm, llm, qwen, llama-cpp, gguf, linguagem-natural, xai]
aliases: [Modelos de Linguagem Pequenos, LLM Local, Transdutor Semântico, IA Offline]
---

# 🤖 Modelos de Linguagem Locais (SLM) e Integração Offline

Este documento especifica o subsistema de Modelos de Linguagem Pequenos (*Small Language Models* - SLM) do CARINA localizado em `src/slm/`. Ele detalha como o CARINA gera justificativas textuais técnicas e periciais a partir de tensores de atribuição neural brutos utilizando modelos locais de linguagem (prioritariamente **Qwen3.5 2B** via `Qwen3.5-2B-UD-Q6_K_XL.gguf`, com suporte de contingência a **Qwen2.5 1.5B/3B** ou **Llama-3.2 3B**) sem chamadas de API externas e sem qualquer dependência de nuvem.

⬅️ [Central de Documentação](README.md) | 🔍 [IA Explicável e SAS](xai_and_sas.md) | 📄 [Motor de Laudos Word ABNT](report_blocks_and_templates.md)

---

## 1. Filosofia de Arquitetura: Privacidade Forense 100% Offline

Na administração pública municipal e no gerenciamento de tráfego urbano crítico, enviar telemetria, históricos de incidentes ou planos semafóricos para APIs comerciais na nuvem (OpenAI, Anthropic, Google Cloud) viola políticas públicas de segurança da informação, leis de proteção de dados (LGPD/GDPR) e a soberania operacional do município.

O CARINA executa toda a síntese de relatórios em linguagem natural **100% localmente no servidor municipal**:
- Executado via bindings de alta performance em C++ (`llama-cpp-python`).
- Suporte a modelos quantizados GGUF (ex: `Q6_K_XL`, `Q4_K_M`, `Q8_0`).
- Baixo consumo de memória: entre **1,5 GB e 3,5 GB de VRAM** (ou em CPU com aceleração vetorial AVX-512).
- Saída estritamente determinística através de decodificação gulosa com temperatura zero ($\tau = 0.0$, `repeat_penalty = 1.05`).

```text
 Gradientes Integrados do Captum & Telemetria
                  │
                  ▼
      ┌───────────────────────┐
      │  semantic_transducer  │
      └───────────┬───────────┘
                  │
       ┌──────────┴──────────┐
       ▼                     ▼
┌──────────────┐      ┌──────────────┐
│prompt_builder│      │device_manager│ (Calcula VRAM / Camadas de offload)
└──────┬───────┘      └──────┬───────┘
       │                     │
       └──────────┬──────────┘
                  ▼
      ┌───────────────────────┐
      │local_llama_transducer │ (Executa modelo Qwen GGUF via llama.cpp)
      └───────────┬───────────┘
                  │
       ┌──────────┴──────────┐
       ▼                     ▼
┌───────────────┐     ┌───────────────┐
│output_sanitizer│    │revision_engine│ (Valida texto contra valores SQL)
└───────────────┘     └───────────────┘
```

---

## 2. Módulos Centrais em `src/slm/`

### 2.1 Transdutor Semântico (`semantic_transducer.py`)
Localizado em `src/slm/semantic_transducer.py`:
- Interface pública principal para a geração de laudos em texto natural.
- Configurado por padrão para `Model_Vault/Qwen3.5-2B-UD-Q6_K_XL.gguf` com contexto `n_ctx = 8192`.
- Converte tuplas numéricas `(tamanho_fila=18, velocidade=12.4 km/h, veto=True)` em prompts contextualizados de engenharia de tráfego.
- Possui motor heurístico de contingência (*fallback*): caso o hardware não possua GPU/RAM disponível ou os pesos GGUF não estejam instalados, gera textos determinísticos baseados em regras sem interromper a execução do sistema.

### 2.2 Transdutor Llama Local (`local_llama_transducer.py`)
Localizado em `src/slm/local_llama_transducer.py`:
- Encapsula `llama_cpp.Llama` com travas de concorrência thread-safe.
- Gerencia o offload de camadas para GPU (`n_gpu_layers = -1` para aceleração integral via CUDA).
- Executa amostragem determinística (`temperature = 0.0`, `repeat_penalty = 1.05`) com limites dinâmicos de tokens para mitigar alucinações e repetições.

### 2.3 Gerenciamento de Recursos (`device_manager.py` e `resource_manager.py`)
- `src/slm/device_manager.py`: Mapeia o hardware disponível (NVIDIA CUDA, ROCm, Apple Metal ou threads de CPU).
- `src/slm/resource_manager.py`: Gerencia alocações de contexto dinâmicas e purga a memória do cache KV imediatamente após a síntese dos relatórios.

### 2.4 Motor de Revisão Factual (`revision_engine.py` e `output_sanitizer.py`)
- `src/slm/revision_engine.py`: Extrai entidades numéricas e percentuais da prosa gerada e valida contra as tabelas do PostgreSQL para evitar desvios métricos.
- `src/slm/output_sanitizer.py`: Remove formatações residuais de markdown, espaços extras e repetições cíclicas.

---

## 3. Configuração e Cofre de Modelos (Model Vault)

Pesos pré-treinados em formato GGUF são armazenados no diretório local `Model_Vault/`:

```text
Model_Vault/
└── Qwen3.5-2B-UD-Q6_K_XL.gguf
```

Configuração em `config/settings.ini`:
```ini
[REPORT_FORMATTING]
report_slm_device = auto
report_slm_gpu_layers = -1
xai_slm_device = auto
xai_slm_gpu_layers = -1
```

Parâmetros de inferência configurados em `src/slm/semantic_transducer.py`:
- **Caminho do Modelo:** `Model_Vault/Qwen3.5-2B-UD-Q6_K_XL.gguf`
- **Janela de Contexto (`n_ctx`):** `8192`
- **Temperatura:** `0.0` (determinístico / guloso)
- **Penalidade de Repetição (`repeat_penalty`):** `1.05`
- **Teto Máximo de Tokens:** Calculado dinamicamente (`512` a `4096`)

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Modelos de Linguagem On-Premise • CARINA CORE v1.2.0</i>
</div>
