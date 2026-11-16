---
tags: [reports, abnt, docx, omml, latex, blocks, xai]
aliases: [Движок отчетов, Генератор документов, ABNT NBR 14724, Формулы OMML]
---

# 📄 Генератор аналитических отчетов и модуль Word по стандарту ABNT

Данный документ описывает конвейер автоматизированной генерации отчетных документов CARINA, расположенный в каталогах [`src/blocks/`](../../src/blocks) и [`src/xai/`](../../src/xai). В нем подробно рассматривается преобразование оперативной телеметрии, тензоров атрибуции Captum и математических формул в готовые к публикации экспертные аудиторские отчеты формата **Microsoft Word (`.docx`)**, полностью соответствующие стандарту **ABNT NBR 14724**.

⬅️ Назад в [Главный хаб документации](carina_moc.md) | 🔍 См. [Объяснимый ИИ и SAS](xai_and_sas.md) | 🤖 См. [Компактные языковые модели](slm_and_local_llm.md)

---

## 1. Архитектурный конвейер

Традиционные инструменты отчетности генерируют простой текст, неформатированный HTML или статичные файлы PDF, которые трудно поддаются редактированию и заверению подписями муниципальных инженеров. CARINA применяет модульную блочную архитектуру для построения структурированных документов `.docx`, содержащих нативные формулы стандарта Office Math Markup Language (OMML) и стилизованные таблицы.

```text
 Источники Markdown и телеметрии
             │
             ▼
 ┌──────────────────────┐    Преобразование AST Markdown    ┌──────────────────────┐
 │   markdown_to_docx   │ ────────────────────────────────> │   docx_text_builder  │
 └──────────┬───────────┘                                   └──────────────────────┘
            │
            ├──> [Уравнения ($..$)] ──> math_cleaner.py ──> OMML XML (<m:oMath>)
            │
            ├──> [Таблицы]          ──> docx_table_builder.py ──> Стили и границы ABNT
            │
            └──> [Графики/Диаграммы]──> chart.py ──> Векторные вставки высокого разрешения
```

---

## 2. Базовые модули каталога `src/blocks/`

### 2.1 Конвертер LaTeX в OMML (`math_cleaner.py`)
Расположен в [`src/blocks/math_cleaner.py`](../../src/blocks/math_cleaner.py):
- Обнаруживает внутристрочный (`$...$`) и выносной (`$$...$$`) синтаксис формул LaTeX.
- Преобразует исходные строки LaTeX в чистые фрагменты XML стандарта **Office Math Markup Language (OMML)**.
- Вставляет формулы в документ `.docx` как редактируемые нативные математические объекты Word, а не растровые изображения.

### 2.2 Сборщик документов из Markdown (`markdown_to_docx.py`)
Расположен в [`src/blocks/markdown_to_docx.py`](../../src/blocks/markdown_to_docx.py):
- Разбирает иерархические заголовки (`#`, `##`, `###`), нумерованные/маркированные списки, цитаты и выноски (callouts).
- Применяет регламентированные типографические стили (гарнитура шрифта: *Arial*, кегль, полуторный межстрочный интервал: 1.5, отступы абзацев).

### 2.3 Семантические очистители, фильтры и кэшированное форматирование (`report_semantic_cleaner.py` и `report_number_formatter.py`)
Расположен в [`src/blocks/report_semantic_cleaner.py`](../../src/blocks/report_semantic_cleaner.py) и [`src/blocks/report_number_formatter.py`](../../src/blocks/report_number_formatter.py):
- Удаляет артефакты генерации LLM, галлюцинированные токены или сырые теги кода перед сборкой документа.
- Использует кэширование конфигурации с проверкой `stat` в `ReportNumberFormatter` для форматирования единиц измерения (`metros`, `segundos`) и локализованных десятичных разделителей и разделителей разрядов (например, `,` для `pt_BR` и `ru_RU`, `.` для `en_US`) без повторного парсинга `settings.ini` для каждой ячейки.
- Координирует офлайн-синтез текстовых обоснований LLM между `XAI_Worker`, `MFD_Worker` и `AnalysisService` под блокировкой [`slm_process_lock()`](../../src/slm/slm_lock.py) (`slm_gguf.lock`) с детерминированной выгрузкой модели через `ReportTransducerFactory.release_transducer()`.

---

## 3. Модульный реестр блоков отчета (`src/xai/`)

CARINA структурирует экспертные аудиторские отчеты с использованием паттерна **Реестр (Registry Pattern)** через [`src/xai/report_block_registry.py`](../../src/xai/report_block_registry.py):

| Генератор блока | Класс / Модуль | Назначение |
| :--- | :--- | :--- |
| **Резюме для руководства** | `ReportExecutiveSummaryRenderer` | Высокоуровневая сводка эффективности сети, снижение средних задержек и рост пропускной способности. |
| **Формальные уравнения** | `ReportEquationsRenderer` | Отрисовка формальных нейросетевых уравнений (TCN, GATv2, PAE, D3QN, Captum). |
| **Карточки атрибуции** | `ReportAnnexCardsRenderer` | Ранжирование важности признаков по каждому перекрёстку (длина очереди, занятость, скорость). |
| **Аудит вето Guardian** | `ReportGuardianTableRenderer` | Таблица аудита из PostgreSQL со всеми символическими и нейросетевыми вето безопасности. |
| **Консолидированная сводка**| `ReportConsolidatedSummaryRenderer` | Статистическое сопоставление базовых метрик жестких программ с адаптивным ИИ. |

---

## 4. Многоязычные шаблоны отчетов

Шаблоны отчетов и типовые текстовые блоки организованы по предметным областям в [`config/templates/`](../../config/templates):
- **Базовые математические формулы:**
  - `config/templates/omml_equation_templates.json`: Базовые шаблоны формул OMML (PPO, TCN, ST-GATv2, PAE, D3QN, Captum).
- **Шаблоны объяснимого ИИ (XAI) (`config/templates/xai/`):**
  - `xai_report_sections.json`, `xai_categories.json`, `xai_equations.json`, `xai_card_templates.json`, `xai_table_templates.json`.
- **Шаблоны макроскопической диаграммы (MFD) (`config/templates/mfd/`):**
  - `mfd_report_sections.json`, `mfd_table_templates.json`, `mfd_audit_sheet_templates.json`, `mfd_classification_thresholds.json`, `mfd_prompts.json`, `mfd_summary_directives.json`, `mfd_fallback_defaults.json`.
- **Шаблоны интеллектуального анализа (SAS) (`config/templates/sas/`):**
  - `sas_report_sections.json`, `sas_intersection_templates.json`, `sas_recommendation_labels.json`, `sas_summary_directives.json`.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Инженерия Интеллектуальной Мобильности • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Лицензия AGPLv3 или более поздней версии (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
