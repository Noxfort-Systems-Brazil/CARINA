---
tags: [warrants, mutcd, fhwa, traffic-engineering, safety, analysis, sas]
aliases: [Traffic Engineering Warrants, Signal Warrants, MUTCD Analysis, Warrant Evaluator]
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
             ├──> Mandat 1 : Volume Véhiculaire sur Huit Heures
             ├──> Mandat 2 : Volume Véhiculaire sur Quatre Heures
             ├──> Mandat 3 : Volume & Retard d'Heure de Pointe
             ├──> Mandat 7 : Expérience des Accidents & Taux Critique
             └──> Mandat 8 : Coordination du Réseau Routier
```

---

## 2. Mandats MUTCD Implémentés dans `src/analysis/`

### 2.1 Mandat 1 : Volume Véhiculaire sur Huit Heures (`warrant_strategies.py`)
Évalue si le volume de trafic sur les rues sécantes atteint les seuils minimaux de débit véhiculaire pendant 8 heures quelconques d'une journée moyenne :
- **Condition A (Volume Véhiculaire Minimal) :** Les volumes d'approche de la voie principale et secondaire dépassent les débits horaires critiques $V_{major} \ge 500\text{ véh/h}$ et $V_{minor} \ge 150\text{ véh/h}$.
- **Condition B (Interruption du Trafic Continu) :** Le débit sur la voie principale est si dense que le trafic sur la voie secondaire sécante subit un retard excessif ($V_{major} \ge 750\text{ véh/h}$ et $V_{minor} \ge 75\text{ véh/h}$).

### 2.2 Mandat 2 : Volume Véhiculaire sur Quatre Heures
S'applique lorsque le débit sur les voies principales et secondaires satisfait aux courbes MUTCD de 4 heures tracées dans [`src/analysis/warrant_math.py`](../../src/analysis/warrant_math.py).

### 2.3 Mandat 3 : Volume & Retard d'Heure de Pointe
Évalue si les conditions de circulation au cours de l'unique heure la plus chargée de la journée entraînent des retards ou des risques extrêmes :
- Le retard total à l'arrêt subi par le trafic sur une approche de voie secondaire est égal ou supérieur à 4 véhicules-heures pour une approche à une voie.
- Le volume sur l'approche est égal ou supérieur à 100 véhicules par heure.

### 2.4 Mandat 7 : Expérience des Accidents
Évalue si l'installation d'un feu de signalisation réduira le taux d'accidents :
- Un essai préalable adéquat de mesures alternatives avec un respect satisfaisant n'a pas permis de réduire la fréquence des collisions.
- Cinq accidents signalés ou plus de types susceptibles d'être évités par un feu de signalisation (ex. collisions par angle droit) se sont produits au cours d'une période de 12 mois.

### 2.5 Mandat 8 : Réseau Routier
Justifie l'installation d'un signal pour encourager la concentration et l'organisation des flux de circulation sur un réseau artériel coordonné.

---

## 3. Utilitaires Mathématiques (`warrant_math.py`)

Situé dans [`src/analysis/warrant_math.py`](../../src/analysis/warrant_math.py) :
- **Calcul de la Vitesse au 85e Centile :** Évalue si les limitations de vitesse affichées doivent réduire les seuils de volume de mandat de 70% (applicable lorsque la vitesse de la voie principale dépasse $70\text{ km/h}$ ou dans les zones rurales isolées).
- **Ratio de Débit Critique :** Calcule les débits de saturation voie par voie et le degré de saturation ($X = v/c$).
- **Accumulation par Fenêtre Glissante :** Agrège les échantillons chronologiques en classes de volumes horaires robustes.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
