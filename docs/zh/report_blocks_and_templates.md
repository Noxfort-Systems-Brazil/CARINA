---
tags: [reports, abnt, docx, omml, latex, blocks, xai]
aliases: [报告生成引擎, 文档生成器, ABNT NBR 14724, OMML数学公式]
---

# 📄 报告模块引擎与 ABNT 规范 Word 文档生成器

本文档详尽规范了 CARINA 位于 [`src/blocks/`](../../src/blocks) 与 [`src/xai/`](../../src/xai) 的自动化文档排版生成生产线。深入阐述了如何将实时运行遥测、Captum 特征归因张量以及高阶神经网络数学公式，直接转换为符合巴西国家标准 **ABNT NBR 14724** 的出版级 **Microsoft Word (`.docx`)** 司法审计技术报表。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🔍 查阅 [可解释人工智能与SAS](xai_and_sas.md) | 🤖 查阅 [端侧轻量大模型 (SLM)](slm_and_local_llm.md)

---

## 1. 文档生成生产管线架构

传统工业监控软件通常仅能导出纯文本日志、未格式化的粗糙 HTML 或无法二次编辑和盖章签署的静态 PDF。CARINA 采用模块化排版构建引擎，直接生成具备原生 Office 数学标记语言（OMML）可编辑公式以及标准化样式的结构化 `.docx` 文档。

```text
 Markdown 文本与时序遥测源
             │
             ▼
 ┌──────────────────────┐      转换 Markdown 抽象语法树   ┌──────────────────────┐
 │   markdown_to_docx   │ ──────────────────────────────> │   docx_text_builder  │
 └──────────┬───────────┘                                 └──────────────────────┘
            │
            ├──> [数学公式 ($..$)] ──> math_cleaner.py ──> 原生 OMML XML (<m:oMath>)
            │
            ├──> [数据表格]         ──> docx_table_builder.py ──> ABNT 规范边框与排版样式
            │
            └──> [可视化图表]       ──> chart.py ──> 高 DPI 矢量图元内嵌
```

---

## 2. `src/blocks/` 核心功能模块

### 2.1 LaTeX 转原生 OMML 公式转换器 (`math_cleaner.py`)
位于 [`src/blocks/math_cleaner.py`](../../src/blocks/math_cleaner.py)：
- 自动识别行内数学公式（`$...$`）与独立行居中公式（`$$...$$`）语法。
- 将原始 LaTeX 表达式实时编译转换为严格遵循 **Office Math Markup Language (OMML)** 国际标准的数学 XML 节点。
- 将公式以原生 Word 可编辑数学对象的形态直接内嵌至文档中，彻底告别模糊易失真的位图公式渲染。

### 2.2 Markdown 文档结构装配器 (`markdown_to_docx.py`)
位于 [`src/blocks/markdown_to_docx.py`](../../src/blocks/markdown_to_docx.py)：
- 递归解析各级层级标题（`#`、`##`、`###`）、有序/无序列表、引用块及高亮警告框。
- 自动套用出版级排版规范（字体族：*Arial*、正文字号、1.5 倍行距、标准段前段后间距）。

### 2.3 语义净化、清洗器与缓存格式化器 (`report_semantic_cleaner.py` & `report_number_formatter.py`)
位于 [`src/blocks/report_semantic_cleaner.py`](../../src/blocks/report_semantic_cleaner.py) 与 [`src/blocks/report_number_formatter.py`](../../src/blocks/report_number_formatter.py)：
- 在文档组装前剔除大模型生成的幻觉标记、残留标记符或未闭合的代码标签。
- 在 `ReportNumberFormatter` 中采用经 `stat` 校验的配置缓存来格式化单位（`metros`、`segundos`）以及本地化小数/千分位分隔符（例如 `pt_BR` 使用 `,`，`en_US` 使用 `.`），避免按单元格重复解析 `settings.ini`。
- 在 [`slm_process_lock()`](../../src/slm/slm_lock.py)（`slm_gguf.lock`）的保护下协调 `XAI_Worker`、`MFD_Worker` 与 `AnalysisService` 之间的离线 LLM 文本合成，并通过 `ReportTransducerFactory.release_transducer()` 执行确定性模型卸载。

---

## 3. 模块化报告块注册表 (`src/xai/`)

CARINA 在 [`src/xai/report_block_registry.py`](../../src/xai/report_block_registry.py) 中基于 **注册表模式（Registry Pattern）** 管理各审计报表组件：

| 报告块渲染器 | 对应核心类 / 模块 | 负责业务与呈现目标 |
| :--- | :--- | :--- |
| **执行摘要 (Executive Summary)** | `ReportExecutiveSummaryRenderer` | 全局高度概括全城路网通行效率、车均延误降低比例以及通行能力增益。 |
| **形式化数学公式 (Formal Equations)** | `ReportEquationsRenderer` | 精美渲染支配各神经网络层的 5 大形式化数学公式（TCN、GATv2、PAE、D3QN、Captum）。 |
| **特征归因卡片 (Attribution Cards)** | `ReportAnnexCardsRenderer` | 逐路口详细呈现关键微观特征的敏感度归因排名（排队长度、道路占有率、平均车速）。 |
| **Guardian 安全否决审计 (Guardian Veto)** | `ReportGuardianTableRenderer` | 查询 PostgreSQL 数据库，结构化输出所有符号安全否决与神经溢流否决的明细记录。 |
| **综合指标汇总 (Consolidated Summary)** | `ReportConsolidatedSummaryRenderer` | 生成全面对比传统基准配时与 AI 自适应配时的综合统计评估对比表。 |

---

## 4. 多语言报告模板与本地化配置

报告模板与章节片段按技术领域规范化保存在 [`config/templates/`](../../config/templates) 目录中：
- **基础数学物理方程：**
  - `config/templates/omml_equation_templates.json`：OMML 数学公式基础模板（PPO, TCN, ST-GATv2, PAE, D3QN, Captum）。
- **可解释人工智能 (XAI) 模板 (`config/templates/xai/`)：**
  - `xai_report_sections.json`、`xai_categories.json`、`xai_equations.json`、`xai_card_templates.json`、`xai_table_templates.json`。
- **宏观基本图 (MFD) 模板 (`config/templates/mfd/`)：**
  - `mfd_report_sections.json`、`mfd_table_templates.json`、`mfd_audit_sheet_templates.json`、`mfd_classification_thresholds.json`、`mfd_prompts.json`、`mfd_summary_directives.json`、`mfd_fallback_defaults.json`。
- **智能分析系统 (SAS) 模板 (`config/templates/sas/`)：**
  - `sas_report_sections.json`、`sas_intersection_templates.json`、`sas_recommendation_labels.json`、`sas_summary_directives.json`。

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
