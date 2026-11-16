---
tags: [rendering, heatmaps, maps, sumo, visualization, graphics]
aliases: [Rendering Engine, Heatmaps, Map Generator, Canvas Visualization]
---

# 🗺️ Map Rendering Engine & Asynchronous Heatmaps

This document specifies CARINA's map rendering and traffic visualization subsystem located in [`src/rendering/`](../../src/rendering). It details static vector map generation from SUMO road network definitions (`.net.xml`), spatial coordinate projection, and asynchronous real-time heatmap interpolation.

⬅️ Back to [Main Documentation Hub](carina_moc.md) | 🖥️ See [UI & Dashboard](ui_and_dashboard.md) | 📈 See [MFD & Analytics](mfd_and_analytics.md)

---

## 1. Subsystem Architecture

CARINA provides native geospatial visualization without relying on external web map tiles or proprietary mapping services. The rendering subsystem operates entirely offline:

```text
 SUMO Road Network (`.net.xml`) / Telemetry
                      │
                      ▼
        ┌───────────────────────────┐
        │  map_coordinate_generator │ (Transforms UTM/Cartesian -> Canvas Pixels)
        └─────────────┬─────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
┌────────────────────────┐  ┌────────────────────────┐
│   static_map_renderer  │  │ async_heatmap_renderer │
│ (Lanes, Nodes, Lights) │  │ (KDE Density & Delays) │
└───────────┬────────────┘  └───────────┬────────────┘
            │                           │
            └─────────────┬─────────────┘
                          ▼
             Native Flet Canvas Surface
             (`LiveCanvasMapWidget`)
```

---

## 2. Core Modules in `src/rendering/`

### 2.1 Coordinate Transformation (`map_coordinate_generator.py`)
Located in [`src/rendering/map_coordinate_generator.py`](../../src/rendering/map_coordinate_generator.py):
- Converts SUMO 2D coordinate projections $(x, y)$ into viewport canvas coordinates $(u, v)$.
- Supports smooth pan, pinch-to-zoom, and auto-centering based on the bounding box of all active intersections.
- Manages aspect ratio preservation across varying monitor resolutions.

### 2.2 Static Vector Map Renderer (`static_map_renderer.py`) & SUMO Net LRU Cache (`sumo_net_cache.py`)
Located in [`src/rendering/static_map_renderer.py`](../../src/rendering/static_map_renderer.py) and [`src/utils/sumo_net_cache.py`](../../src/utils/sumo_net_cache.py):
- Parses SUMO `.net.xml` lane geometry, junction boundaries, and internal lane connections through [`read_sumo_net_cached()`](../../src/utils/sumo_net_cache.py) (thread-safe LRU cache up to 8 entries keyed by path, `mtime_ns`, size, `with_programs`, and `with_internal`).
- Renders multi-lane arterial roads with lane dividers, directional arrows, and traffic light head symbols.
- Caches rendered vector paths in memory to eliminate CPU recomputation during static scenes.

### 2.3 Asynchronous Heatmap Renderer (`async_heatmap_renderer.py`) & Offscreen Matplotlib (`mpl_utils.py`)
Located in [`src/rendering/async_heatmap_renderer.py`](../../src/rendering/async_heatmap_renderer.py) and [`src/rendering/mpl_utils.py`](../../src/rendering/mpl_utils.py):
- Employs **Kernel Density Estimation (KDE)** to interpolate continuous spatial heatmaps from discrete lane metrics:
  - **Traffic Density Heatmap:** Displays vehicle accumulation per square kilometer.
  - **Waiting Time & Delay Heatmap:** Highlights arterial bottleneck pinch-points.
  - **Spillback Risk Heatmap:** Visualizes Guardian Agent predicted congestion waves.
- Offloads Gaussian blur and matrix convolutions to background worker threads, and renders plots through isolated offscreen `Figure` + `FigureCanvasAgg` instances (`create_offscreen_figure` / `close_offscreen_figure`) rather than global `pyplot` state, preventing memory leaks and GUI thread contention.

---

## 3. Configuration & Heatmap Color Gradients

Heatmap weights and thresholds are configured in [`config/settings.ini`](../../config/settings.ini):

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
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
