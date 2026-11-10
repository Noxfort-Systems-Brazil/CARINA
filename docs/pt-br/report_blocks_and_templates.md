---
tags: [relatorios, abnt, docx, omml, latex, blocos, xai]
aliases: [Motor de Relatórios, Gerador de Laudos, ABNT NBR 14724, Matemática OMML]
---

# 📄 Motor de Blocos de Relatório e Gerador de Laudos Word ABNT

Este documento especifica o pipeline automatizado de geração documental do CARINA localizado em `src/blocks/` e `src/xai/`. Ele detalha a transformação de telemetria em tempo real, tensores de atribuição do Captum e formulações matemáticas em relatórios periciais prontos para assinatura e publicação em formato **Microsoft Word (`.docx`)** rigorosamente compatíveis com a norma **ABNT NBR 14724**.

⬅️ [Central de Documentação](README.md) | 🔍 [IA Explicável e SAS](xai_and_sas.md) | 🤖 [Modelos de Linguagem Locais (SLM)](slm_and_local_llm.md)

---

## 1. Pipeline Arquitetural

Ferramentas tradicionais de relatórios geram textos planos, HTMLs desformatados ou PDFs estáticos que não podem ser editados ou assinados por engenheiros municipais. O CARINA adota uma arquitetura modular de blocos para construir arquivos `.docx` estruturados com fórmulas nativas em Office Math Markup Language (OMML) e tabelas padronizadas.

```text
 Fontes de Markdown e Telemetria
             │
             ▼
 ┌──────────────────────┐      Converte AST Markdown      ┌──────────────────────┐
 │   markdown_to_docx   │ ──────────────────────────────> │   docx_text_builder  │
 └──────────┬───────────┘                                 └──────────────────────┘
            │
            ├──> [Equações ($..$)] ──> math_cleaner.py ──> XML OMML nativo (<m:oMath>)
            │
            ├──> [Tabelas]         ──> docx_table_builder.py ──> Bordas e Estilos ABNT
            │
            └──> [Gráficos]        ──> chart.py ──> Vetores de Alta Resolução (DPI)
```

---

## 2. Módulos Centrais em `src/blocks/`

### 2.1 Conversor LaTeX para OMML (`math_cleaner.py`)
Localizado em `src/blocks/math_cleaner.py`:
- Detecta sintaxes LaTeX em linha (`$...$`) e em bloco (`$$...$$`).
- Converte strings LaTeX puras em fragmentos XML em conformidade com o padrão **Office Math Markup Language (OMML)**.
- Insere as equações diretamente no documento `.docx` como fórmulas editáveis nativas do Word (em vez de imagens rasterizadas que perdem resolução).

### 2.2 Montador de Documentos Markdown (`markdown_to_docx.py`)
Localizado em `src/blocks/markdown_to_docx.py`:
- Realiza o parse de títulos hierárquicos (`#`, `##`, `###`), listas numeradas/não-ordenadas, citações e caixas de destaque.
- Aplica estilos tipográficos formais (família tipográfica: *Arial*, tamanhos padronizados, espaçamento entrelinhas 1,5 e recuos de parágrafo ABNT).

### 2.3 Sanitizadores Semânticos (`report_semantic_cleaner.py`)
Localizado em `src/blocks/report_semantic_cleaner.py`:
- Remove alucinações de LLMs, tokens residuais ou tags de código bruto antes da montagem final.
- Garante consistência numérica e formata separadores decimais localizados (ex.: vírgula `,` para `pt_BR`, ponto `.` para `en_US`).

---

## 3. Registro Modular de Blocos de Relatório (`src/xai/`)

O CARINA estrutura laudos periciais de auditoria utilizando o padrão **Registry Pattern** via `src/xai/report_block_registry.py`:

| Renderizador de Bloco | Classe / Módulo | Finalidade |
| :--- | :--- | :--- |
| **Sumário Executivo** | `ReportExecutiveSummaryRenderer` | Síntese de alto nível de desempenho da malha, redução média de atraso e vazão. |
| **Equações Formais** | `ReportEquationsRenderer` | Renderiza as 5 equações formais da IA (TCN, GATv2, Cross-Attention, D3QN, Captum). |
| **Cartões de Atribuição** | `ReportAnnexCardsRenderer` | Ranqueamento de importância de atributos por cruzamento (fila, ocupação, velocidade). |
| **Auditoria de Vetos do Guardião** | `ReportGuardianTableRenderer` | Tabela pericial consultando no PostgreSQL todos os vetos de segurança simbólicos e neurais. |
| **Resumo Consolidado** | `ReportConsolidatedSummaryRenderer` | Visão estatística comparando métricas de referência (baseline) vs IA autônoma. |

---

## 4. Templates Multilíngues de Laudos

Templates e seções padronizadas ficam centralizados em `config/templates/`:
- `config/templates/xai/xai_report_sections.json`: Definições estruturadas de seções do relatório.
- `config/templates/xai/xai_categories.json`: Rótulos categorizados localizados.
- `config/templates/omml_equation_templates.json`: Templates base para equações OMML.
- `config/templates/xai/xai_table_templates.json`: Cabeçalhos e definições de formatação de tabelas.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Laudos Forenses • CARINA CORE v1.2.0</i>
</div>
