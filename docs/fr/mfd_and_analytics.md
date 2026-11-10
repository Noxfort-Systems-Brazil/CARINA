---
tags: [mfd, analytics, dynamics, density, gating, capacity-drop]
aliases: [MFD Engine, Network Analytics, Traffic Physics, Macroscopic Fundamental Diagram]
---

# 📈 Diagramme Fondamental Macroscopique & Analyse de Réseau

Ce document détaille le sous-système du Diagramme Fondamental Macroscopique situé dans [`src/mfd/`](../../src/mfd), le processus **`MFD_Worker`**, la physique macroscopique des flux de trafic, les algorithmes de régulation de périmètre (*perimeter gating*), ainsi que le cache de filtres d'incidents.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 📊 Voir les [Mandats de Trafic](traffic_engineering_warrants.md) | 🧠 Voir les [Formulations Neuronales](research_notes.md)

---

## 1. Théorie du Diagramme Fondamental Macroscopique (MFD)

Le **Diagramme Fondamental Macroscopique (MFD)** relie l'accumulation totale de véhicules (densité $K$) dans un réseau urbain au débit spatial moyen total ($Q$). Contrairement aux modèles microscopiques qui suivent les interactions individuelles de poursuite de véhicules, le MFD offre une représentation globale et holistique des états du trafic urbain.

```text
       Q (veh/h)
          ▲                Zone 1 : Fluide (PPO Tactique Actif)
     Qmax │           /\   Zone 2 : Chute de Capacité (Régulation de Périmètre Déclenchée)
          │          /  \  Zone 3 : Blocage Généralisé / Effondrement (Dérogation d'Urgence)
          │         /    \
          └────────┴──────┴────────► K (veh/km)
                  Kcrit   Kjam
```

- **Zone 1 : Région non congestionnée ($K < K_{crit}$) :** Les carrefours individuels fonctionnent avec des politiques locales PPO-TCN maximisant l'allocation locale de temps vert.
- **Zone 2 : Région de chute de capacité ($K > K_{crit}$) :** Les frictions de trafic entre les files d'attente dégradent brutalement le débit global (*Capacity Drop*).
- **Zone 3 : Blocage total / Saturation ($K \to K_{jam}$) :** Blocage des artères urbaines où les véhicules ne peuvent plus franchir les carrefours en raison de remontées de files d'attente vers l'amont (*spillback*).

---

## 2. Formulations Mathématiques

La densité à l'échelle du réseau $K_{net}$ et le débit spatial moyen $Q_{net}$ sont agrégés sous forme de moyennes pondérées sur l'ensemble des $N$ segments de route surveillés :

$$K_{net} = \frac{\sum_{i=1}^N k_i \cdot L_i}{\sum_{i=1}^N L_i}, \quad Q_{net} = \frac{\sum_{i=1}^N q_i \cdot L_i}{\sum_{i=1}^N L_i}$$

Où :
- $k_i$ : Densité du tronçon $i$ (véhicules par kilomètre).
- $q_i$ : Débit du tronçon $i$ (véhicules par heure).
- $L_i$ : Longueur physique du tronçon $i$ en mètres.

---

## 3. Modules Principaux dans `src/mfd/`

La suite analytique MFD est composée de 35 modules spécialisés dans [`src/mfd/`](../../src/mfd) :

### 3.1 Processus MFD Worker (`mfd_worker.py`)
S'exécute comme un processus de système d'exploitation isolé généré par le `ProcessManager`. Il écoute la file IPC `mfd_trigger`, exécute des régressions macroscopiques et renvoie les résultats sur `mfd_results`.

### 3.2 Moteur de Comparaison & Gestionnaire de Référence (`mfd_comparison_engine.py` & `mfd_baseline_manager.py`)
- Compare en continu le débit adaptatif actuel de l'IA par rapport aux courbes de référence à temps fixe (*fixed-time*).
- Calcule les gains en heures de véhicules parcourues (VHT) et en kilomètres de véhicules parcourus (VKT).

### 3.3 Reconstructeur Historique (`mfd_history_reconstructor.py`)
Reconstruit les nuages de points débit-densité à partir de la table PostgreSQL `synapse_fluid_dynamics` sur des fenêtres d'observation de plusieurs jours.

### 3.4 Calculateur d'Impact Urbain (`mfd_impact_calculator.py`)
Quantifie les réductions d'émissions municipales ($\text{CO}_2$, $\text{NO}_x$), les économies de carburant et les gains de productivité économique résultant de la réduction de la congestion.

---

## 4. Actionnement de la Régulation de Périmètre (*Perimeter Gating*)

Lorsque la densité du réseau dépasse la capacité critique ($K_{net} \ge K_{crit}$) :
1. Le `MFD_Worker` émet une alerte de régulation de périmètre vers le `CentralController`.
2. Les carrefours périphériques bordant le cœur urbain congestionné réduisent leurs temps de vert entrants ($T_{green} \leftarrow T_{green} \times \eta$, où $\eta \in [0.6, 0.8]$).
3. Les couloirs artériels sortants reçoivent la priorité verte maximale pour évacuer les véhicules hors du centre d'affaires ou de la zone saturée.

---

## 5. Cache de Débogage du Filtre d'Incidents (`.carina_incident_filter_cache.json`)

Pour éviter que des accidents localisés ou des fermetures de voies pour travaux ne corrompent la courbe macroscopique MFD, [`src/drivers/incident_filter.py`](../../src/drivers/incident_filter.py) isole les tronçons anormaux et enregistre les états d'incidents actifs dans `.carina_incident_filter_cache.json` pour une récupération rapide lors des redémarrages du système.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
