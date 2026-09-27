---
tags: [ui, flet, dashboard, frontend, sds, planning, widgets]
aliases: [UI Architecture, Dashboard Service, Flet Frontend, Planning View]
---

# 🖥️ UI Architecture, Planning View & Smart Dashboard Service

This document specifies CARINA's native desktop user interface located in [`ui/`](../../ui), the **Smart Dashboard Service (SDS)** in [`src/sds/`](../../src/sds), the **System Tray Manager**, and the single-instance locking system.

⬅️ Back to [Main Documentation Hub](../CARINA_MOC.md) | 🗺️ See [Rendering & Heatmaps](../RENDERING_AND_HEATMAPS.md) | 🔍 See [Explainable AI & SAS](xai_and_sas.md)

---

## 1. Decoupled Desktop Architecture (`ui/` & `src/sds/`)

To prevent GUI rendering or client browser socket lag from dropping real-time traffic control frames, CARINA completely decouples its frontend into the **`DashboardService` (SDS)** process ([`run_sds_worker`](../../src/sds/dashboard_worker.py)).

```text
CentralController (gRPC) ──> [sds Queue] ──> DashboardService (SDS) ──> [ui Queue] ──> Flet UI (Main Thread)
                                                   │
                                                   └──> WebSocket Telemetry Server (port 8080)
```

---

## 2. Real Flet UI Architecture & View Hierarchy

The frontend is built using **[Flet](https://flet.dev/)** (Python + Flutter engine) located in [`ui/`](../../ui).

```text
ui/
├── main_ui.py                      # Primary Flet application bootstrap & window setup
│
├── views/                          # Application Screen Views
│   ├── dashboard_view.py           # Real-time traffic monitoring & interactive map canvas
│   ├── planning_view.py            # Network topology planning, phase timing & street grouping
│   ├── diagnostics_view.py         # IPC latency metrics, memory usage & process monitors
│   ├── system_status_view.py       # Active microservices state & physical controller statuses
│   ├── settings_view.py            # System configuration & controller IP endpoint editor
│   └── error_view.py               # Global error capture & diagnostic exception view
│
├── widgets/                        # Specialized Modular UI Widgets
│   ├── live_canvas_map_widget.py   # High-performance custom canvas drawing roads and signals
│   ├── planning_control_panel_widget.py # Planning toolbars, stage selectors & node inspector
│   ├── mfd_viewer_widget.py        # Live Macroscopic Fundamental Diagram curve plotter
│   ├── xai_viewer_widget.py        # Captum neural feature attribution breakdown charts
│   ├── street_info_widget.py       # Per-lane speed, occupancy & queue length readouts
│   ├── traffic_light_widget.py     # Live signal phase head animations (Red, Yellow, Green)
│   ├── audit_log_widget.py         # Forensic Guardian safety veto inspection table
│   └── global_controls_widget.py   # Start, Pause, Step & Emergency Override buttons
│
├── renderers/                      # Canvas Drawing & Visual Synchronization
│   ├── map_drawer.py               # Vector geometry rasterizer for lanes and junctions
│   ├── planning_map_renderer.py    # Visual layout engine for topology nodes
│   └── map_visual_syncer.py        # Smooth 60 FPS animation synchronizer
│
└── locales/                        # Internationalization (i18n) Dictionaries
    ├── pt_br.json                  # Portuguese (Brazil) - Default
    ├── en_us.json                  # English (United States)
    ├── es_es.json                  # Spanish
    ├── fr_fr.json                  # French
    ├── ru_ru.json                  # Russian
    └── zh_cn.json                  # Simplified Chinese
```

---

## 3. Planning View & Network Topology Editor

The **Planning View** ([`ui/views/planning_view.py`](../../ui/views/planning_view.py)) enables municipal traffic engineers to interactively inspect and configure physical road networks:
- **Topology Grouping:** Group intersection clusters into coordinated arterial corridors (Green Waves).
- **Phase & Stage Inspector:** Inspect minimum green constraints, yellow clearance, and all-red intergreen buffers.
- **Export Handler:** Export modified signal timing plans directly to controller connection repositories or CSV templates.

For vector map rendering details, see [Map Rendering & Heatmaps](../RENDERING_AND_HEATMAPS.md).

---

## 4. System Tray & Single Instance Lock (`SingleInstanceLock`)

CARINA runs seamlessly as a background system daemon with a native desktop tray icon:

### 4.1 System Tray Management ([`UITrayManager`](../../src/launcher/ui_tray_manager.py))
- **Tray Actions:** Minimize to Tray, Open Dashboard, View Live Logs, Restart Services, Graceful Shutdown.
- **Notification Popups:** Emits native OS notifications when the Watchdog detects microservice crashes or when the Guardian Agent fires an emergency safety veto.

### 4.2 Single Instance Lock ([`SingleInstanceLock`](../../src/launcher/single_instance.py))
- **Port:** `42123`
- If a user double-clicks `carina.py` or the executable while CARINA is already running:
  1. The duplicate process attempts to bind TCP port `42123`.
  2. Upon failure, it transmits a `RESTORE` command signal over the local TCP socket to the primary instance.
  3. The primary instance brings the Flet window to the foreground, and the duplicate process terminates cleanly.
