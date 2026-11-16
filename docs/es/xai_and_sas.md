---
tags: [xai, sas, captum, abnt, auditoria-forense, veto-guardian, atribucion]
aliases: [IA Explicable, Analítica SAS, Canalización XAI, Auditoría Forense]
---

# 🔍 IA Explicable (XAI), Auditoría Forense y Analítica SAS

Este documento especifica la canalización de explicabilidad forense de CARINA ubicada en [`src/xai/`](../../src/xai) y [`src/sas/`](../../src/sas). Detalla los **Gradientes Integrados de Google Captum**, las 5 ecuaciones neuronales formales, las tablas de auditoría de vetos de seguridad del Agente Guardian y la generación de informes técnicos bajo la norma ABNT NBR 14724.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 📄 Ver [Bloques de Informes y Word](report_blocks_and_templates.md) | 🤖 Ver [Modelos de Lenguaje Reducidos (SLM)](slm_and_local_llm.md)

---

## 1. Arquitectura de Explicabilidad Forense (`src/xai/`)

En la gestión semafórica municipal, las decisiones de IA de tipo "caja negra" son legalmente inadmisibles ante fiscalías públicas, tribunales de cuentas e ingenieros de tráfico certificados. CARINA proporciona **explicabilidad matemática 100% determinista** mediante:

```text
 ┌─────────────────────────┐          ┌───────────────────────────┐          ┌────────────────────────┐
 │ Red Neuronal Profunda   │ ───────> │ Gradientes Integrados     │ ───────> │ Informe ABNT NBR 14724 │ ───> xai_forense.docx
 │ (TCN + ST-GATv2 + D3QN) │          │ Captum (0% a 100%)        │          │ 5 Ecuaciones Formals + │      (Informe de Auditoría)
 └─────────────────────────┘          └───────────────────────────┘          │ Tabla Vetos Guardian   │
                                                                             └────────────────────────┘
```

La canalización XAI implementa una arquitectura modular de constructores multiagente:
- [`src/xai/xai_worker.py`](../../src/xai/xai_worker.py) y [`report_pipeline.py`](../../src/xai/report_pipeline.py): Ejecutan la atribución de Captum por agente una sola vez y reutilizan la caché `captum_result` resultante (`precomputed_analyses`) en la generación de informes consolidados multiagente, restringiendo la síntesis textual pesada del SLM (`run_slm`) estrictamente al agente objetivo primario bajo `slm_process_lock()` y accediendo a la BD mediante `DatabaseManager.get_instance(..., enable_step_worker=False)`.
- [`src/xai/multi_agent_report_builder.py`](../../src/xai/multi_agent_report_builder.py): Coordina la generación de informes municipales a través de todas las intersecciones.
- [`src/xai/captum_attribution_engine.py`](../../src/xai/captum_attribution_engine.py): Calcula atribuciones de gradiente a lo largo del camino de interpolación desde la línea base hasta la entrada actual con los gradientes de parámetros del modelo envuelto congelados (`requires_grad_(False)`).
- [`src/xai/network_attribution_aggregator.py`](../../src/xai/network_attribution_aggregator.py): Agrega la importancia de características a lo largo de avenidas arteriales.
- [`src/xai/report_block_registry.py`](../../src/xai/report_block_registry.py): Despacha secciones del informe a renderizadores especializados (con renderizado de gráficos fuera de pantalla mediante `mpl_utils.py`).
- [`src/sas/sas_helpers.py`](../../src/sas/sas_helpers.py) y [`sas_historical_data_processor.py`](../../src/sas/sas_historical_data_processor.py): Calculan 100 cuantiles en una sola pasada mediante `TrafficMetricsCalculator.compute_percentiles` y evitan la expansión redundante de muestras sintéticas (`SyntheticSampleGenerator`).

---

## 2. Las 5 Ecuaciones Neuronales Formales (Sección 2 del Informe)

Para cumplir con los estándares administrativos de auditabilidad, el informe de CARINA incluye 5 ecuaciones formales en LaTeX que rigen cada capa neuronal:

### 2.1 Convolución Causal Dilatada (LocalAgent TCN)
$$\mathbf{y}(t) = (x *_d f)(t) = \sum_{i=0}^{k-1} f(i) \cdot x(t - d \cdot i)$$

### 2.2 Atención en Grafos Espacio-Temporal (ST-GATv2 Lite)
$$\alpha_{ij}(t) = \frac{\exp\left(\mathbf{a}^T \text{LeakyReLU}\left(\mathbf{W} [\mathbf{h}_i \parallel \mathbf{h}_j]\right)\right)}{\sum_{k \in \mathcal{N}_i} \exp\left(\mathbf{a}^T \text{LeakyReLU}\left(\mathbf{W} [\mathbf{h}_i \parallel \mathbf{h}_k]\right)\right)}$$

### 2.3 Formulación del Autoencoder Predictivo (PAE)
$$\mathcal{L}_{\text{PAE}}(\phi, \theta) = \frac{1}{N} \sum_{k=1}^N \| x_k(t + \Delta t) - g_\theta(f_\phi(x_k(t))) \|^2$$

### 2.4 Valor Q Dueling de Seguridad del Guardian (Veto D3QN)
$$Q(s, a) = V(s) + \left( A(s, a) - \frac{1}{|\mathcal{A}|} \sum_{a'} A(s, a') \right)$$

### 2.5 Gradientes Integrados de Captum (Axioma de Completitud)
$$\text{IntegratedGradients}_i(x) = (x_i - x'_i) \times \int_0^1 \frac{\partial F(x' + \alpha(x - x'))}{\partial x_i} d\alpha$$

$$\sum_{i=1}^n \text{IntegratedGradients}_i(x) = F(x) - F(x')$$

---

## 3. Tabla de Auditoría de Vetos del Agente Guardian

El informe consulta la tabla `step_decisions` de PostgreSQL para generar la **Tabla Oficial de Auditoría de Vetos de Seguridad del Agente Guardian**:

| ID de Intersección | Decisiones Evaluadas | Acciones Aprobadas | Vetos de Seguridad | Tasa de Cumplimiento (%) | Causa Raíz Primaria del Veto |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Junction ID 1193472566** | 1,420 | 1,396 | 24 | **98.3%** | Protección de Tiempo Verde Mínimo (7s) |
| **Junction ID 2281940123** | 1,420 | 1,418 | 2 | **99.8%** | Aplicación de Despeje de Amarillo (3s) |

Para detalles de formato de documento y renderizado matemático OMML, consulte [Bloques de Informes y Word](report_blocks_and_templates.md).
Para la síntesis pericial de justificaciones en lenguaje natural offline, consulte [Modelos de Lenguaje Reducidos (SLM)](slm_and_local_llm.md).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
