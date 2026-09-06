---
tags: [rendering, heatmaps, maps, sumo, visualization, graphics]
aliases: [Rendering Engine, Heatmaps, Map Generator, Canvas Visualization]
---

# 🗺️ Map Rendering Engine & Asynchronous Heatmaps

This document specifies CARINA's map rendering and traffic visualization subsystem located in [`src/rendering/`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/rendering). It details static vector map generation from SUMO road network definitions (`.net.xml`), spatial coordinate projection, and asynchronous real-time heatmap interpolation.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🖥️ See [UI & Dashboard](UI_AND_DASHBOARD.md) | 📈 See [MFD & Analytics](MFD_AND_ANALYTICS.md)

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
Located in [`src/rendering/map_coordinate_generator.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/rendering/map_coordinate_generator.py):
- Converts SUMO 2D coordinate projections $(x, y)$ into viewport canvas coordinates $(u, v)$.
- Supports smooth pan, pinch-to-zoom, and auto-centering based on the bounding box of all active intersections.
- Manages aspect ratio preservation across varying monitor resolutions.

### 2.2 Static Vector Map Renderer (`static_map_renderer.py`)
Located in [`src/rendering/static_map_renderer.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/rendering/static_map_renderer.py):
- Parses SUMO `.net.xml` lane geometry, junction boundaries, and internal lane connections.
- Renders multi-lane arterial roads with lane dividers, directional arrows, and traffic light head symbols.
- Caches rendered vector paths in memory to eliminate CPU recomputation during static scenes.

### 2.3 Asynchronous Heatmap Renderer (`async_heatmap_renderer.py`)
Located in [`src/rendering/async_heatmap_renderer.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/rendering/async_heatmap_renderer.py):
- Employs **Kernel Density Estimation (KDE)** to interpolate continuous spatial heatmaps from discrete lane metrics:
  - **Traffic Density Heatmap:** Displays vehicle accumulation per square kilometer.
  - **Waiting Time & Delay Heatmap:** Highlights arterial bottleneck pinch-points.
  - **Spillback Risk Heatmap:** Visualizes Guardian Agent predicted congestion waves.
- Offloads Gaussian blur and matrix convolutions to background worker threads, preventing GUI frame drops.

---

## 3. Configuration & Heatmap Color Gradients

Heatmap weights and thresholds are configured in [`config/settings.ini`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/config/settings.ini):

```ini
[HEATMAP_SCALING]
weight_occupancy = 1.0
weight_waiting_time = 1.5
weight_queue_length = 2.0
gaussian_kernel_radius = 24
color_ramp = viridis  # Supported: viridis, plasma, turbo, traffic_light
```
