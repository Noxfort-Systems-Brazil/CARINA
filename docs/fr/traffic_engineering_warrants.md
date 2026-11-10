---
tags: [warrants, mutcd, fhwa, traffic-engineering, safety, analysis, sas]
aliases: [Mandats d'Ingénierie du Trafic, Justifications de Feux, Analyse MUTCD, Évaluateur de Mandats]
---

# 🚦 Mandats de Signalisation Routière & Analyse d'Infrastructure

Ce document spécifie le sous-système d'analyse des mandats d'ingénierie de la circulation de CARINA situé dans [`src/analysis/`](../../src/analysis). Il détaille la formulation mathématique et l'évaluation automatisée des mandats de feux réglementaires formels basés sur le **FHWA MUTCD** (*Manual on Uniform Traffic Control Devices*) et les normes municipales.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 📈 Voir [MFD & Analyse Réseau](mfd_and_analytics.md) | 🔍 Voir [IA Explicable & SAS](xai_and_sas.md)

---

## 1. Évaluation Automatisée des Mandats de Feux

Avant d'installer ou de réajuster des feux de circulation, les ingénieurs municipaux sont légalement tenus de démontrer qu'un carrefour satisfait aux mandats réglementaires d'ingénierie formels. Le **Smart Analysis System (SAS)** évalue les données historiques accumulées depuis PostgreSQL pour déterminer si un feu de circulation est justifié ou s'il nécessite une modification de ses cycles et minutages.

```text
 Données Historiques de Trafic (PostgreSQL `synapse_fluid_dynamics`)
                             │
                             ▼
                ┌─────────────────────────┐
                │ InfrastructureAnalyzer  │
                └────────────┬────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
   ┌──────────────────────┐      ┌──────────────────────┐
   │   WarrantEvaluator   │      │     WarrantMath      │
   │ (Stratégies Mandats) │      │(Calculs Débits & Vit)│
   └──────────┬───────────┘      └──────────────────────┘
              │
              ├──> Mandat 1 : VolumeWarrant (Volumes Tableau MUTCD 4C-1)
              ├──> Mandat 2 : DelayWarrant (Retard Inacceptable D)
              ├──> Mandat 3 : QueueWarrant (File d'Attente Statistique P95)
              └──> Mandat 4 : SaturationWarrant (Degré de Saturation X = v/c)
```

---

## 2. Stratégies de Mandats Implémentées (`src/analysis/warrant_strategies.py`)

CARINA structure son analyse technique selon le **Patron Stratégie** enregistré dans [`WarrantEvaluator`](../../src/analysis/warrant_evaluator.py) :

### 2.1 Mandat 1 : Mandat de Volume (`VolumeWarrant`)
Évalue les volumes de trafic d'approche via l'équation fondamentale de l'écoulement du trafic :
$$q = k \times (v \times 3.6)$$
- **Seuils du Tableau 4C-1 du MUTCD :** Évalue les voies d'approche et les limites de vitesse :
  - **1 Voie Majeure / 1 Voie Mineure :** Condition A : $V_{majeure} \ge 500\text{ véh/h}$, $V_{mineure} \ge 150\text{ véh/h}$. Condition B : $V_{majeure} \ge 750\text{ véh/h}$, $V_{mineure} \ge 75\text{ véh/h}$.
  - **2+ Voies Majeure / 2+ Voies Mineure :** Condition A : $V_{majeure} \ge 600\text{ véh/h}$, $V_{mineure} \ge 200\text{ véh/h}$. Condition B : $V_{majeure} \ge 900\text{ véh/h}$, $V_{mineure} \ge 100\text{ véh/h}$.
- **Facteur de Réduction de 70% pour Haute Vitesse :** Si la vitesse réglementaire de l'axe majeur dépasse $70\text{ km/h}$ ($19.44\text{ m/s}$), l'ensemble des seuils de volume est pondéré par $0.70$ (ex. $500 \to 350\text{ véh/h}$, $150 \to 105\text{ véh/h}$).

### 2.2 Mandat 2 : Mandat de Retard (`DelayWarrant`)
Quantifie le retard opérationnel subi sur les approches secondaires par rapport au temps de trajet en circulation libre :
$$D = \frac{L}{v_{\text{reel}}} - \frac{L}{v_{\text{limite}}}$$
- Évalue si le retard moyen dépasse le seuil inacceptable :
$$D_{moyen} > D_{\text{seuil}}$$
- Seuil par défaut : `unacceptable_delay = 90.0 s`.

### 2.3 Mandat 3 : Mandat de File d'Attente P95 (`QueueWarrant`)
Audite l'accumulation des files d'attente à l'aide de distributions statistiques au 95e percentile afin de prévenir les remontées de files (spillback) :
- Calcule la longueur empirique au 95e percentile $P95(Q)$ sur l'échantillon des capteurs.
- Le mandat est satisfait si :
$$P95(Q) > Q_{\text{seuil}}$$
- Seuil par défaut : `max_queue_p95 = 15` véhicules.

### 2.4 Mandat 4 : Mandat de Degré de Saturation (`SaturationWarrant`)
Évalue le ratio volume/capacité ($v/c$) sur l'ensemble des voies d'approche :
$$X = \frac{q}{N \times f_{\text{ideal}}}$$
Où :
- $q$ : Volume moyen spatial ($\text{véh/h}$).
- $N$ : Nombre de voies d'approche.
- $f_{\text{ideal}}$ : Débit de saturation idéal par voie ($1800\text{ véh/h/voie}$).
- Le mandat est validé si le degré maximal de saturation critique dépasse la capacité admissible :
$$X_{\max} > X_{\text{critique}}$$
- Seuil par défaut : `saturation_critical = 0.85` ($85\%$ de saturation).

---

## 3. Utilitaires Mathématiques (`warrant_math.py`)

Situés dans [`src/analysis/warrant_math.py`](../../src/analysis/warrant_math.py) :
- **`compute_volume_q(density, speed)` :** Calcule le flux moyen spatial $q = k \times (v \times 3.6)$.
- **`compute_delay(length, v_real, v_limit)` :** Calcule le retard véhiculaire réel par rapport à la vitesse maximale autorisée.
- **`compute_p95(values)` :** Calcule la longueur empirique de file d'attente au 95e percentile.
- **`compute_saturation_ratio(volume, num_lanes, ideal_flow)` :** Calcule le degré de saturation ($X = v/c$).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3 ou ultérieure (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
