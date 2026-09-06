---
tags: [reports, abnt, docx, omml, latex, blocks, xai]
aliases: [Report Engine, Document Generator, ABNT NBR 14724, OMML Math]
---

# 📄 Report Blocks Engine & ABNT Word Generator

This document specifies CARINA's automated document generation pipeline located in [`src/blocks/`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/blocks) and [`src/xai/`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/xai). It details the transformation of real-time telemetry, Captum attribution tensors, and mathematical formulations into publication-ready **Microsoft Word (`.docx`)** forensic audit reports compliant with the Brazilian standard **ABNT NBR 14724**.

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
Located in [`src/blocks/math_cleaner.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/blocks/math_cleaner.py):
- Detects inline (`$...$`) and display (`$$...$$`) LaTeX syntax.
- Converts raw LaTeX strings into clean XML fragments complying with the **Office Math Markup Language (OMML)** standard.
- Inserts equations directly into the `.docx` document as editable native Word formulas rather than rasterized images.

### 2.2 Markdown Document Assembler (`markdown_to_docx.py`)
Located in [`src/blocks/markdown_to_docx.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/blocks/markdown_to_docx.py):
- Parses hierarchical headings (`#`, `##`, `###`), ordered/unordered lists, blockquotes, and callouts.
- Applies standard typographic styles (font family: *Arial*, font sizes, line spacing: 1.5, paragraph spacing).

### 2.3 Semantic Cleaners & Sanitizers (`report_semantic_cleaner.py`)
Located in [`src/blocks/report_semantic_cleaner.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/blocks/report_semantic_cleaner.py):
- Removes LLM artifacts, hallucinated tokens, or raw code tags before document assembly.
- Ensures numerical consistency and formats localized decimal delimiters (e.g., `,` for `pt_BR`, `.` for `en_US`).

---

## 3. Modular Report Blocks Registry (`src/xai/`)

CARINA structures forensic audit reports using the **Registry Pattern** via [`src/xai/report_block_registry.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/xai/report_block_registry.py):

| Block Renderer | Class / Module | Purpose |
| :--- | :--- | :--- |
| **Executive Summary** | `ReportExecutiveSummaryRenderer` | High-level synthesis of network performance, average delay reductions, and throughput. |
| **Formal Equations** | `ReportEquationsRenderer` | Renders the 5 formal neural equations (TCN, GATv2, Cross-Attention, D3QN, Captum). |
| **Attribution Cards** | `ReportAnnexCardsRenderer` | Per-intersection feature attribution rankings (queue length, occupancy, speed). |
| **Guardian Veto Audit** | `ReportGuardianTableRenderer` | Audit table querying PostgreSQL for all symbolic and neural safety vetoes. |
| **Consolidated Summary**| `ReportConsolidatedSummaryRenderer` | Statistical overview comparing baseline vs AI performance metrics. |

---

## 4. Multi-Language Report Templates

Report templates and section boilerplates are stored in [`config/`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/config):
- `config/xai_report_sections.json`: Structured section definitions.
- `config/xai_categories.json`: Localized category tags.
- `config/omml_equation_templates.json`: Base templates for OMML equations.
- `config/xai_table_templates.json`: Table headers and formatting definitions.
