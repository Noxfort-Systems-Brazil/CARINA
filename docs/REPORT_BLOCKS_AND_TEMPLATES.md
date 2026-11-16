---
tags: [reports, abnt, docx, omml, latex, blocks, xai]
aliases: [Report Engine, Document Generator, ABNT NBR 14724, OMML Math]
---

# 📄 Report Blocks Engine & ABNT Word Generator

This document specifies CARINA's automated document generation pipeline located in [`src/blocks/`](../src/blocks) and [`src/xai/`](../src/xai). It details the transformation of real-time telemetry, Captum attribution tensors, and mathematical formulations into publication-ready **Microsoft Word (`.docx`)** forensic audit reports compliant with the Brazilian standard **ABNT NBR 14724**.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🔍 See [Explainable AI & SAS](XAI_AND_SAS.md) | 🤖 See [Small Language Models](SLM_AND_LOCAL_LLM.md)

---

## 1. Architectural Pipeline

Traditional reporting tools generate plain text, unformatted HTML, or static PDFs that cannot be easily signed or edited by municipal engineers. CARINA uses a modular block architecture to construct structured `.docx` files containing native Office Math Markup Language (OMML) formulas and styled tables.

```text
 Markdown & Telemetry Sources
             │
             ▼
 ┌──────────────────────┐      Converts Markdown AST      ┌──────────────────────┐
 │   markdown_to_docx   │ ──────────────────────────────> │   docx_text_builder  │
 └──────────┬───────────┘                                 └──────────────────────┘
            │
            ├──> [Equations ($..$)] ──> math_cleaner.py ──> OMML XML (<m:oMath>)
            │
            ├──> [Tables]           ──> docx_table_builder.py ──> ABNT Borders & Styles
            │
            └──> [Charts / Plots]   ──> chart.py ──> High-DPI Vector Embeddings
```

---

## 2. Core Modules in `src/blocks/`

### 2.1 LaTeX to OMML Converter (`math_cleaner.py`)
Located in [`src/blocks/math_cleaner.py`](../src/blocks/math_cleaner.py):
- Detects inline (`$...$`) and display (`$$...$$`) LaTeX syntax.
- Converts raw LaTeX strings into clean XML fragments complying with the **Office Math Markup Language (OMML)** standard.
- Inserts equations directly into the `.docx` document as editable native Word formulas rather than rasterized images.

### 2.2 Markdown Document Assembler (`markdown_to_docx.py`)
Located in [`src/blocks/markdown_to_docx.py`](../src/blocks/markdown_to_docx.py):
- Parses hierarchical headings (`#`, `##`, `###`), ordered/unordered lists, blockquotes, and callouts.
- Applies standard typographic styles (font family: *Arial*, font sizes, line spacing: 1.5, paragraph spacing).

### 2.3 Semantic Cleaners, Sanitizers & Cached Formatting (`report_semantic_cleaner.py` & `report_number_formatter.py`)
Located in [`src/blocks/report_semantic_cleaner.py`](../src/blocks/report_semantic_cleaner.py) and [`src/blocks/report_number_formatter.py`](../src/blocks/report_number_formatter.py):
- Removes LLM artifacts, hallucinated tokens, or raw code tags before document assembly.
- Uses `stat`-validated config caching in `ReportNumberFormatter` to format units (`metros`, `segundos`) and localized decimal/thousands delimiters (e.g., `,` for `pt_BR`, `.` for `en_US`) without re-parsing `settings.ini` per cell.
- Coordinates offline LLM narrative synthesis across `XAI_Worker`, `MFD_Worker`, and `AnalysisService` under [`slm_process_lock()`](../src/slm/slm_lock.py) (`slm_gguf.lock`) with deterministic model unloading via `ReportTransducerFactory.release_transducer()`.

---

## 3. Modular Report Blocks Registry (`src/xai/`)

CARINA structures forensic audit reports using the **Registry Pattern** via [`src/xai/report_block_registry.py`](../src/xai/report_block_registry.py):

| Block Renderer | Class / Module | Purpose |
| :--- | :--- | :--- |
| **Executive Summary** | `ReportExecutiveSummaryRenderer` | High-level synthesis of network performance, average delay reductions, and throughput. |
| **Formal Equations** | `ReportEquationsRenderer` | Renders the formal neural equations (TCN, GATv2, PAE, D3QN, Captum). |
| **Attribution Cards** | `ReportAnnexCardsRenderer` | Per-intersection feature attribution rankings (queue length, occupancy, speed). |
| **Guardian Veto Audit** | `ReportGuardianTableRenderer` | Audit table querying PostgreSQL for all symbolic and neural safety vetoes. |
| **Consolidated Summary**| `ReportConsolidatedSummaryRenderer` | Statistical overview comparing baseline vs AI performance metrics. |

---

## 4. Multi-Language Report Templates

Report templates and section boilerplates are organized by domain in [`config/templates/`](../config/templates):
- **Base Mathematical Formulas:**
  - `config/templates/omml_equation_templates.json`: Base templates for OMML equations (PPO, TCN, ST-GATv2, PAE, D3QN, Captum).
- **Explainable AI (XAI) Templates (`config/templates/xai/`):**
  - `xai_report_sections.json`, `xai_categories.json`, `xai_equations.json`, `xai_card_templates.json`, `xai_table_templates.json`.
- **Macroscopic Fundamental Diagram (MFD) Templates (`config/templates/mfd/`):**
  - `mfd_report_sections.json`, `mfd_table_templates.json`, `mfd_audit_sheet_templates.json`, `mfd_classification_thresholds.json`, `mfd_prompts.json`, `mfd_summary_directives.json`, `mfd_fallback_defaults.json`.
- **Smart Analysis System (SAS) Templates (`config/templates/sas/`):**
  - `sas_report_sections.json`, `sas_intersection_templates.json`, `sas_recommendation_labels.json`, `sas_summary_directives.json`.

---

<div align="center">
  <img src="assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
