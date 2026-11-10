---
tags: [slm, llm, qwen, llama-cpp, gguf, lenguaje-natural, xai]
aliases: [Modelos de Lenguaje Reducidos, LLM Local, Transductor Semántico, IA Offline]
---

# 🤖 Modelos de Lenguaje Reducidos (SLM) e Integración de LLM Local

Este documento especifica el subsistema de Modelos de Lenguaje Reducidos (SLM) de CARINA ubicado en [`src/slm/`](../../src/slm). Detalla cómo CARINA sintetiza justificaciones textuales periciales listas para publicación a partir de tensores de atribución neuronal mediante modelos de lenguaje locales y desconectados (principalmente **Qwen3.5 2B** mediante `Qwen3.5-2B-UD-Q6_K_XL.gguf`, con soporte de reserva para **Qwen2.5 1.5B/3B** o **Llama-3.2 3B**) sin realizar llamadas a APIs externas ni depender de servicios en la nube.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🔍 Ver [IA Explicable y SAS](xai_and_sas.md) | 📄 Ver [Bloques de Reporte y Word](report_blocks_and_templates.md)

---

## 1. Filosofía Arquitectónica: Privacidad Forense 100% Offline

En la administración pública municipal, transmitir telemetría de tráfico, registros de incidentes o datos de control de intersecciones a nubes comerciales (OpenAI, Anthropic, Google Cloud) vulnera la gobernanza de datos públicos, normativas de privacidad y soberanía de la infraestructura.

CARINA ejecuta toda la síntesis de reportes en lenguaje natural **100% de manera local**:
- Se ejecuta mediante enlaces optimizados de C++ (`llama-cpp-python`).
- Soporta **modelos GGUF cuantizados** (ej., `Q6_K_XL`, `Q4_K_M`, `Q8_0`).
- Requiere únicamente entre **~1.5 GB y 3.5 GB de VRAM** (o RAM de CPU con aceleración AVX-512).
- Salida totalmente determinista mediante decodificación voraz (greedy) con temperatura cero ($\tau = 0.0$, `repeat_penalty = 1.05`).

```text
 Gradientes Integrados Captum y Telemetría
                   │
                   ▼
       ┌───────────────────────┐
       │  semantic_transducer  │
       └───────────┬───────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
 ┌──────────────┐      ┌──────────────┐
 │prompt_builder│      │device_manager│ (Calcula VRAM / capas GPU offloaded)
 └──────┬───────┘      └──────┬───────┘
        │                     │
        └──────────┬──────────┘
                   ▼
       ┌───────────────────────┐
       │local_llama_transducer │ (Ejecuta modelo Qwen GGUF vía llama.cpp)
       └───────────┬───────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
 ┌───────────────┐     ┌───────────────┐
 │output_sanitizer│    │revision_engine│ (Cruza texto contra telemetría SQL)
 └───────────────┘     └───────────────┘
```

---

## 2. Módulos Principales en `src/slm/`

### 2.1 Transductor Semántico (`semantic_transducer.py`)
Ubicado en [`src/slm/semantic_transducer.py`](../../src/slm/semantic_transducer.py):
- Actúa como la interfaz pública principal para la generación de explicaciones textuales.
- Utiliza por defecto `Model_Vault/Qwen3.5-2B-UD-Q6_K_XL.gguf` con ventana de contexto `n_ctx = 8192`.
- Transforma tuplas numéricas `(queue_length=18, speed=12.4 km/h, veto=True)` en prompts especializados de ingeniería de tráfico.
- Dispone de motor heurístico de respaldo: si el hardware carece de GPU/RAM o faltan los pesos del LLM, genera explicaciones deterministas basadas en reglas sin interrumpir la ejecución.

### 2.2 Transductor Local Llama (`local_llama_transducer.py`)
Ubicado en [`src/slm/local_llama_transducer.py`](../../src/slm/local_llama_transducer.py):
- Envuelve `llama_cpp.Llama` con bloqueos seguros de concurrencia de hilos.
- Administra la descarga de capas a GPU (`n_gpu_layers = -1` para descarga completa a CUDA).
- Aplica decodificación voraz (`temperature = 0.0`, `repeat_penalty = 1.05`) con límites dinámicos de tokens para evitar bucles repetitivos y alucinaciones.

### 2.3 Gestión de Dispositivos y Recursos (`device_manager.py` y `resource_manager.py`)
- [`src/slm/device_manager.py`](../../src/slm/device_manager.py): Detecta y perfila el hardware disponible (NVIDIA CUDA, ROCm, Apple Metal o hilos de CPU).
- [`src/slm/resource_manager.py`](../../src/slm/resource_manager.py): Administra la asignación de contexto y purga la memoria de claves/valores (KV cache) entre episodios de reporte.

### 2.4 Motor de Revisión Factual (`revision_engine.py` y `output_sanitizer.py`)
- [`src/slm/revision_engine.py`](../../src/slm/revision_engine.py): Extrae entidades numéricas del texto generado y comprueba su concordancia estricta con los valores de la base de datos SQL.
- [`src/slm/output_sanitizer.py`](../../src/slm/output_sanitizer.py): Remueve etiquetas de markdown, espacios espurios y artefactos de repetición.

---

## 3. Configuración y Bóveda de Modelos (`Model_Vault/`)

Los pesos preentrenados se almacenan en el directorio local `Model_Vault/`:

```text
Model_Vault/
└── Qwen3.5-2B-UD-Q6_K_XL.gguf
```

Configuración en `config/settings.ini`:
```ini
[REPORT_FORMATTING]
report_slm_device = auto
report_slm_gpu_layers = -1
xai_slm_device = auto
xai_slm_gpu_layers = -1
```

Parámetros de inferencia configurados en [`semantic_transducer.py`](../../src/slm/semantic_transducer.py):
- **Ruta del Modelo:** `Model_Vault/Qwen3.5-2B-UD-Q6_K_XL.gguf`
- **Ventana de Contexto (`n_ctx`):** `8192`
- **Temperatura:** `0.0` (determinista / voraz)
- **Penalización por Repetición:** `1.05`
- **Tokens Máximos de Salida:** Calculados dinámicamente (`512` a `4096`)

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
