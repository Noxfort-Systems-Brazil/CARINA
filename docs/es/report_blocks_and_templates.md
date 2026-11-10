---
tags: [informes, abnt, docx, omml, latex, bloques, xai]
aliases: [Motor de Informes, Generador de Documentos, ABNT NBR 14724, Matemática OMML]
---

# 📄 Motor de Bloques de Informes y Generador Word ABNT

Este documento especifica la canalización automatizada de generación de documentos de CARINA ubicada en [`src/blocks/`](../../src/blocks) y [`src/xai/`](../../src/xai). Detalla la transformación de telemetría en tiempo real, tensores de atribución de Captum y formulaciones matemáticas en informes de auditoría forense listos para publicación en formato **Microsoft Word (`.docx`)** conformes a normativas técnicas como la norma **ABNT NBR 14724**.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🔍 Ver [IA Explicable y SAS](xai_and_sas.md) | 🤖 Ver [Modelos de Lenguaje Reducidos](slm_and_local_llm.md)

---

## 1. Flujo Arquitectónico

Las herramientas tradicionales de generación de reportes producen texto plano, HTML sin formato o PDFs estáticos que no pueden ser firmados ni editados fácilmente por ingenieros municipales. CARINA emplea una arquitectura modular basada en bloques para construir archivos `.docx` estructurados que contienen fórmulas nativas en Office Math Markup Language (OMML) y tablas con estilo técnico.

```text
 Fuentes de Markdown y Telemetría
             │
             ▼
 ┌──────────────────────┐      Convierte AST de Markdown      ┌──────────────────────┐
 │   markdown_to_docx   │ ──────────────────────────────────> │   docx_text_builder  │
 └──────────┬───────────┘                                     └──────────────────────┘
            │
            ├──> [Ecuaciones ($..$)] ──> math_cleaner.py ──> OMML XML (<m:oMath>)
            │
            ├──> [Tablas]            ──> docx_table_builder.py ──> Bordes y Estilos ABNT
            │
            └──> [Gráficos / Curvas] ──> chart.py ──> Incrustaciones Vectoriales High-DPI
```

---

## 2. Módulos Centrales en `src/blocks/`

### 2.1 Convertidor de LaTeX a OMML (`math_cleaner.py`)
Ubicado en [`src/blocks/math_cleaner.py`](../../src/blocks/math_cleaner.py):
- Detecta sintaxis LaTeX en línea (`$...$`) y en bloque (`$$...$$`).
- Convierte cadenas de LaTeX sin procesar en fragmentos XML limpios que cumplen con el estándar **Office Math Markup Language (OMML)**.
- Inserta ecuaciones directamente en el documento `.docx` como fórmulas editables nativas de Word en lugar de imágenes rasterizadas.

### 2.2 Ensamblador de Documentos Markdown (`markdown_to_docx.py`)
Ubicado en [`src/blocks/markdown_to_docx.py`](../../src/blocks/markdown_to_docx.py):
- Analiza encabezados jerárquicos (`#`, `##`, `###`), listas ordenadas y desordenadas, citas en bloque y cuadros destacados.
- Aplica estilos tipográficos estándar (fuente: *Arial*, tamaños de fuente, interlineado: 1.5, espaciado de párrafos).

### 2.3 Saneadores y Limpiadores Semánticos (`report_semantic_cleaner.py`)
Ubicado en [`src/blocks/report_semantic_cleaner.py`](../../src/blocks/report_semantic_cleaner.py):
- Elimina artefactos de LLM, tokens alucinados o etiquetas de código sin procesar antes del ensamblaje del documento.
- Asegura la coherencia numérica y formatea separadores decimales localizados (ej., `,` para `es_ES` / `pt_BR`, `.` para `en_US`).

---

## 3. Registro Modular de Bloques de Informes (`src/xai/`)

CARINA estructura los informes de auditoría forense utilizando el **Patrón de Registro (Registry Pattern)** a través de [`src/xai/report_block_registry.py`](../../src/xai/report_block_registry.py):

| Renderizador de Bloque | Clase / Módulo | Propósito |
| :--- | :--- | :--- |
| **Resumen Ejecutivo** | `ReportExecutiveSummaryRenderer` | Síntesis de alto nivel del rendimiento de la red, reducción promedio de demoras y flujo total. |
| **Ecuaciones Formales** | `ReportEquationsRenderer` | Renderiza las ecuaciones neuronales formales (TCN, GATv2, PAE, D3QN, Captum). |
| **Tarjetas de Atribución** | `ReportAnnexCardsRenderer` | Clasificación de importancia de características por intersección (cola, ocupación, velocidad). |
| **Auditoría Vetos Guardian** | `ReportGuardianTableRenderer` | Tabla de auditoría que consulta PostgreSQL para todos los vetos de seguridad simbólicos y neuronales. |
| **Resumen Consolidado** | `ReportConsolidatedSummaryRenderer` | Cuadro estadístico comparativo entre métricas base de tiempo fijo y rendimiento de la IA. |

---

## 4. Plantillas de Informes Multilingües

Las plantillas de informes y fragmentos de sección se organizan por dominio en [`config/templates/`](../../config/templates):
- **Fórmulas Matemáticas Base:**
  - `config/templates/omml_equation_templates.json`: Plantillas base para ecuaciones OMML (PPO, TCN, ST-GATv2, PAE, D3QN, Captum).
- **Plantillas de IA Explicable (XAI) (`config/templates/xai/`):**
  - `xai_report_sections.json`, `xai_categories.json`, `xai_equations.json`, `xai_card_templates.json`, `xai_table_templates.json`.
- **Plantillas de Diagrama Fundamental Macroscópico (MFD) (`config/templates/mfd/`):**
  - `mfd_report_sections.json`, `mfd_table_templates.json`, `mfd_audit_sheet_templates.json`, `mfd_classification_thresholds.json`, `mfd_prompts.json`, `mfd_summary_directives.json`, `mfd_fallback_defaults.json`.
- **Plantillas de Smart Analysis System (SAS) (`config/templates/sas/`):**
  - `sas_report_sections.json`, `sas_intersection_templates.json`, `sas_recommendation_labels.json`, `sas_summary_directives.json`.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
