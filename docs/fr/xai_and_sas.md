---
tags: [xai, sas, captum, abnt, forensic-audit, guardian-veto, attribution]
aliases: [Explainable AI, SAS Analytics, XAI Pipeline, Forensic Auditing]
---

# 🔍 IA Explicable (XAI), Audit Médico-Légal & Analyses SAS

Ce document spécifie le pipeline d'explicabilité médico-légale de CARINA situé dans [`src/xai/`](../../src/xai) et [`src/sas/`](../../src/sas). Il détaille les **Gradients Intégrés Google Captum**, les 5 équations neuronales formelles, les tableaux d'audit des vetos de sécurité de l'Agent Guardian et la génération de rapports conformes à l'ABNT NBR 14724.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 📄 Voir [Blocs de Rapports & Word](report_blocks_and_templates.md) | 🤖 Voir [Petits Modèles de Langage](slm_and_local_llm.md)

---

## 1. Architecture d'Explicabilité Médico-Légale (`src/xai/`)

Dans la gestion du trafic municipal, les décisions de type « boîte noire » de l'IA sont juridiquement inacceptables pour les ministères publics, les cours des comptes et les ingénieurs agréés de la circulation. CARINA garantit une **explicabilité mathématique 100% déterministe** grâce à :

```text
 ┌─────────────────────────┐          ┌───────────────────────────┐          ┌────────────────────────┐
 │  Réseau Neuronal Profond│ ───────> │ Gradients Intégrés Captum │ ───────> │  Rapport ABNT NBR 14724│ ───> xai.docx Médico-Légal
 │  (TCN + ST-GATv2 + D3QN)│          │ (0% à 100%)               │          │  5 Équations Formelles │      (Rapport d'Audit Municipal)
 └─────────────────────────┘          └───────────────────────────┘          │  + Table Veto Guardian │
                                                                             └────────────────────────┘
```

Le pipeline XAI utilise une architecture de constructeur multi-agents modulaire :
- [`src/xai/multi_agent_report_builder.py`](../../src/xai/multi_agent_report_builder.py) : Coordonne la génération des rapports municipaux sur tous les carrefours.
- [`src/xai/captum_attribution_engine.py`](../../src/xai/captum_attribution_engine.py) : Calcule les attributions de gradients le long de la trajectoire d'interpolation de la référence vers l'entrée actuelle.
- [`src/xai/network_attribution_aggregator.py`](../../src/xai/network_attribution_aggregator.py) : Agrège l'importance des caractéristiques à travers les artères urbaines.
- [`src/xai/report_block_registry.py`](../../src/xai/report_block_registry.py) : Répartit les sections de rapport vers les moteurs de rendu spécialisés.

---

## 2. Les 5 Équations Neuronales Formelles (Section 2 du Rapport)

Afin de satisfaire aux normes d'auditabilité administrative, le rapport de CARINA comprend 5 équations LaTeX formelles régissant chaque couche neuronale :

### 2.1 Convolution Causale Dilatée (LocalAgent TCN)
$$\mathbf{y}(t) = (x *_d f)(t) = \sum_{i=0}^{k-1} f(i) \cdot x(t - d \cdot i)$$

### 2.2 Attention sur Graphes Spatio-Temporelle (ST-GATv2 Lite)
$$\alpha_{ij}(t) = \frac{\exp\left(\mathbf{a}^T \text{LeakyReLU}\left(\mathbf{W} [\mathbf{h}_i \parallel \mathbf{h}_j]\right)\right)}{\sum_{k \in \mathcal{N}_i} \exp\left(\mathbf{a}^T \text{LeakyReLU}\left(\mathbf{W} [\mathbf{h}_i \parallel \mathbf{h}_k]\right)\right)}$$

### 2.3 Formulation de l'Auto-Encodeur Prédictif (PAE)
$$\mathcal{L}_{\text{PAE}}(\phi, \theta) = \frac{1}{N} \sum_{k=1}^N \| x_k(t + \Delta t) - g_\theta(f_\phi(x_k(t))) \|^2$$

### 2.4 Q-Valeur Dueling de Sécurité Guardian (Veto D3QN)
$$Q(s, a) = V(s) + \left( A(s, a) - \frac{1}{|\mathcal{A}|} \sum_{a'} A(s, a') \right)$$

### 2.5 Gradients Intégrés Captum (Axiome de Complétude)
$$\text{IntegratedGradients}_i(x) = (x_i - x'_i) \times \int_0^1 \frac{\partial F(x' + \alpha(x - x'))}{\partial x_i} d\alpha$$

$$\sum_{i=1}^n \text{IntegratedGradients}_i(x) = F(x) - F(x')$$

---

## 3. Tableau d'Audit des Vetos de l'Agent Guardian

Le rapport interroge la table PostgreSQL `step_decisions` pour générer le **Tableau Officiel d'Audit des Vetos de Sécurité de l'Agent Guardian** :

| ID du Carrefour | Décisions Évaluées | Actions Approuvées | Vetos de Sécurité | Taux de Conformité (%) | Cause Racine Principale du Veto |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Junction ID 1193472566** | 1 420 | 1 396 | 24 | **98.3%** | Protection du Temps Vert Minimal (7s) |
| **Junction ID 2281940123** | 1 420 | 1 418 | 2 | **99.8%** | Respect du Dégagement Jaune (3s) |

Pour plus de détails sur le formatage du document et le rendu mathématique OMML, voir [Blocs de Rapports & Word](report_blocks_and_templates.md).
Pour la synthèse des justifications textuelles hors ligne en langage naturel, voir [Petits Modèles de Langage (SLM)](slm_and_local_llm.md).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
