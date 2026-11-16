---
tags: [rendering, heatmaps, maps, sumo, visualization, graphics]
aliases: [Rendering Engine, Heatmaps, Map Generator, Canvas Visualization]
---

# 🗺️ Moteur de Rendu Cartographique & Cartes Thermiques Asynchrones

Ce document spécifie le sous-système de rendu cartographique et de visualisation du trafic de CARINA situé dans [`src/rendering/`](../../src/rendering). Il détaille la génération de cartes vectorielles statiques à partir des définitions de réseaux routiers SUMO (`.net.xml`), la projection de coordonnées spatiales et l'interpolation asynchrone de cartes thermiques (*heatmaps*) en temps réel.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🖥️ Voir [Interface Desktop & Tableau de Bord](ui_and_dashboard.md) | 📈 Voir [MFD & Analyse Réseau](mfd_and_analytics.md)

---

## 1. Architecture du Sous-Système

CARINA fournit une visualisation géospatiale native sans dépendre de tuiles cartographiques web externes ni de services cartographiques propriétaires. Le sous-système de rendu fonctionne de manière entièrement hors ligne :

```text
 Réseau Routier SUMO (`.net.xml`) / Télémétrie
                      │
                      ▼
        ┌───────────────────────────┐
        │  map_coordinate_generator │ (Convertit UTM/Cartésien -> Pixels Canvas)
        └─────────────┬─────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
┌────────────────────────┐  ┌────────────────────────┐
│   static_map_renderer  │  │ async_heatmap_renderer │
│ (Voies, Nœuds, Feux)   │  │ (Densité KDE & Délais) │
└───────────┬────────────┘  └───────────┬────────────┘
            │                           │
            └─────────────┬─────────────┘
                          ▼
             Surface Canvas Native Flet
             (`LiveCanvasMapWidget`)
```

---

## 2. Modules Principaux dans `src/rendering/`

### 2.1 Transformation de Coordonnées (`map_coordinate_generator.py`)
Situé dans [`src/rendering/map_coordinate_generator.py`](../../src/rendering/map_coordinate_generator.py) :
- Convertit les projections de coordonnées 2D de SUMO $(x, y)$ en coordonnées d'affichage canvas $(u, v)$.
- Prend en charge le panoramique fluide (*pan*), le zoom par pincement (*pinch-to-zoom*) et le centrage automatique basé sur la boîte englobante de tous les carrefours actifs.
- Gère la préservation du ratio d'aspect sur différentes résolutions d'écran.

### 2.2 Moteur de Rendu Vectoriel Statique (`static_map_renderer.py`) & Cache LRU SUMO Net (`sumo_net_cache.py`)
Situé dans [`src/rendering/static_map_renderer.py`](../../src/rendering/static_map_renderer.py) et [`src/utils/sumo_net_cache.py`](../../src/utils/sumo_net_cache.py) :
- Analyse la géométrie des voies, les limites des carrefours et les connexions internes de voies du fichier `.net.xml` de SUMO via [`read_sumo_net_cached()`](../../src/utils/sumo_net_cache.py) (cache LRU thread-safe jusqu'à 8 entrées indexé par chemin, `mtime_ns`, taille, `with_programs` et `with_internal`).
- Restitue les artères multi-voies avec séparateurs de voies, flèches directionnelles et symboles de têtes de feux tricolores.
- Met en cache les chemins vectoriels rendus en mémoire pour éliminer les recalculs processeur lors des scènes statiques.

### 2.3 Moteur de Rendu de Cartes Thermiques Asynchrones (`async_heatmap_renderer.py`) & Matplotlib Hors Écran (`mpl_utils.py`)
Situé dans [`src/rendering/async_heatmap_renderer.py`](../../src/rendering/async_heatmap_renderer.py) et [`src/rendering/mpl_utils.py`](../../src/rendering/mpl_utils.py) :
- Utilise l'**Estimation de Densité par Noyau (KDE)** pour interpoler des cartes thermiques spatiales continues à partir de métriques discrètes de voies :
  - **Carte thermique de densité de trafic :** Affiche l'accumulation de véhicules par kilomètre carré.
  - **Carte thermique des temps d'attente et retards :** Met en évidence les points d'étranglement des artères.
  - **Carte thermique du risque de remontée de file (*spillback*) :** Visualise les ondes de congestion prédites par l'Agent Guardian.
- Décharge le flou gaussien et les convolutions matricielles sur des threads de travail en arrière-plan, et effectue le rendu des graphiques à travers des instances hors écran isolées `Figure` + `FigureCanvasAgg` (`create_offscreen_figure` / `close_offscreen_figure`) plutôt que l'état global `pyplot`, évitant ainsi les fuites mémoire et la contention du thread IHM.

---

## 3. Configuration & Dégradés de Couleurs des Cartes Thermiques

Les pondérations et seuils des cartes thermiques sont configurés dans [`config/settings.ini`](../../config/settings.ini) :

```ini
[HEATMAP_SCALING]
weight_occupancy = 1.0
weight_waiting_time = 1.5
weight_flow = 1.0
saturation_threshold = 0.85
lane_aggregation_strategy = max
heatmap_strategy = combined
heatmap_saturation = 1.0
```

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3 ou ultérieure (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
