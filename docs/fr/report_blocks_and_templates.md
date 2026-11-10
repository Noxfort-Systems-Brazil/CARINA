---
tags: [reports, abnt, docx, omml, latex, blocks, xai]
aliases: [Report Engine, Document Generator, ABNT NBR 14724, OMML Math]
---

# 📄 Moteur de Blocs de Rapports & Générateur Word ABNT

Ce document spécifie le pipeline de génération automatisée de documents de CARINA situé dans [`src/blocks/`](../../src/blocks) et [`src/xai/`](../../src/xai). Il détaille la transformation de la télémétrie en temps réel, des tenseurs d'attribution Captum et des formulations mathématiques en rapports d'audit médico-légaux **Microsoft Word (`.docx`)** prêts pour publication et conformes à la norme brésilienne **ABNT NBR 14724**.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🔍 Voir [IA Explicable & SAS](xai_and_sas.md) | 🤖 Voir [Petits Modèles de Langage](slm_and_local_llm.md)

---

## 1. Pipeline Architectural

Les outils traditionnels de reporting génèrent du texte brut, du HTML non formaté ou des PDF statiques qui ne peuvent pas être facilement signés ou édités par les ingénieurs municipaux. CARINA utilise une architecture modulaire par blocs pour construire des fichiers `.docx` structurés contenant des formules natives en Office Math Markup Language (OMML) et des tableaux stylisés.

```text
 Sources Markdown & Télémétrie
             │
             ▼
 ┌──────────────────────┐      Convertit l'AST Markdown       ┌──────────────────────┐
 │   markdown_to_docx   │ ──────────────────────────────────> │   docx_text_builder  │
 └──────────┬───────────┘                                     └──────────────────────┘
            │
            ├──> [Équations ($..$)] ──> math_cleaner.py ──> OMML XML (<m:oMath>)
            │
            ├──> [Tableaux]         ──> docx_table_builder.py ──> Bordures & Styles ABNT
            │
            └──> [Graphiques]       ──> chart.py ──> Intégrations Vectorielles Haute Résolution
```

---

## 2. Modules Principaux dans `src/blocks/`

### 2.1 Convertisseur LaTeX vers OMML (`math_cleaner.py`)
Situé dans [`src/blocks/math_cleaner.py`](../../src/blocks/math_cleaner.py) :
- Détecte la syntaxe LaTeX en ligne (`$...$`) et en bloc (`$$...$$`).
- Convertit les chaînes LaTeX brutes en fragments XML propres conformes à la norme **Office Math Markup Language (OMML)**.
- Insère les équations directement dans le document `.docx` sous forme de formules Word natives éditables plutôt que d'images matricielles.

### 2.2 Assembleur de Documents Markdown (`markdown_to_docx.py`)
Situé dans [`src/blocks/markdown_to_docx.py`](../../src/blocks/markdown_to_docx.py) :
- Analyse les titres hiérarchiques (`#`, `##`, `###`), les listes ordonnées/non ordonnées, les citations et les encarts d'avertissement.
- Applique les styles typographiques standard (police de caractères : *Arial*, tailles de police, interligne : 1,5, espacement des paragraphes).

### 2.3 Nettoyeurs & Assainisseurs Sémantiques (`report_semantic_cleaner.py`)
Situé dans [`src/blocks/report_semantic_cleaner.py`](../../src/blocks/report_semantic_cleaner.py) :
- Supprime les artefacts de LLM, les jetons hallucinés ou les balises de code brut avant l'assemblage du document.
- Garantit la cohérence numérique et formate les séparateurs décimaux localisés (ex. `,` pour `fr_FR` ou `pt_BR`, `.` pour `en_US`).

---

## 3. Registre Modulaire des Blocs de Rapport (`src/xai/`)

CARINA structure les rapports d'audit médico-légaux selon le **patron de Registre** (*Registry Pattern*) via [`src/xai/report_block_registry.py`](../../src/xai/report_block_registry.py) :

| Moteur de Rendu de Bloc | Classe / Module | Finalité |
| :--- | :--- | :--- |
| **Résumé Exécutif** | `ReportExecutiveSummaryRenderer` | Synthèse de haut niveau des performances du réseau, réductions des retards moyens et débit. |
| **Équations Formelles** | `ReportEquationsRenderer` | Restitue les équations formelles des réseaux neuronaux (TCN, GATv2, PAE, D3QN, Captum). |
| **Fiches d'Attribution** | `ReportAnnexCardsRenderer` | Classement de l'attribution des caractéristiques par carrefour (longueur de file, occupation, vitesse). |
| **Audit des Vetos Guardian** | `ReportGuardianTableRenderer` | Tableau d'audit interrogeant PostgreSQL pour tous les vetos de sécurité symboliques et neuronaux. |
| **Synthèse Consolidée** | `ReportConsolidatedSummaryRenderer` | Vue d'ensemble statistique comparant les métriques de référence (*baseline*) et d'IA. |

---

## 4. Modèles de Rapports Multilingues

Les modèles de rapports et les structures de sections sont conservés dans [`config/templates/`](../../config/templates) :
- `config/templates/xai/xai_report_sections.json` : Définitions structurées des sections.
- `config/templates/xai/xai_categories.json` : Balises de catégories localisées.
- `config/templates/omml_equation_templates.json` : Modèles de base pour les équations OMML.
- `config/templates/xai/xai_table_templates.json` : En-têtes de tableaux et définitions de mise en forme.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
