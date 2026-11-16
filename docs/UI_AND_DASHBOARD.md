---
tags: [ui, flet, dashboard, frontend, sds, planning, widgets]
aliases: [UI Architecture, Dashboard Service, Flet Frontend, Planning View]
---

# 🖥️ UI Architecture, Planning View & Smart Dashboard Service

This document specifies CARINA's native desktop user interface located in [`ui/`](../ui), the **Smart Dashboard Service (SDS)** in [`src/sds/`](../src/sds), the **System Tray Manager**, and the single-instance locking system.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🗺️ See [Rendering & Heatmaps](RENDERING_AND_HEATMAPS.md) | 🔍 See [Explainable AI & SAS](XAI_AND_SAS.md) | 🚑 See [EVP Preemption](EVP_AND_PREEMPTION.md)

---

## 1. Decoupled Desktop Architecture (`ui/` & `src/sds/`)

To prevent GUI rendering or client browser socket lag from dropping real-time traffic control frames, CARINA completely decouples its frontend into the **`DashboardService` (SDS)** process ([`run_sds_worker`](../src/sds/dashboard_worker.py), running with `CARINA_GATEWAY_ROLE=remote`):

```text
CentralController (owner) ──> [sds Queue] ──> DashboardService (SDS) ──> [ui_telemetry Queue] ──> Flet UI (Main Thread)
                                                    ├──> WebSocket Server (port 8080, 2.0s client timeout & backpressure)
                                                    └──> CCOBroadcastClient (Pinned HTTPS -> Go Web Gateway :2201)
```

- **Performance & Memory Guards (`ui/` & `src/sds/`):**
  - [`MapAnimator`](../ui/animators/map_animator.py) & [`WindowManager`](../ui/managers/window_manager.py): Pause map redraw loops while the desktop window is minimized/hidden (`_carina_window_hidden`) and gate renders via `_data_dirty` flags.
  - [`AuditLogWidget`](../ui/widgets/audit_log_widget.py): Paginates Guardian audit records ($\le 100$ rows per page) to keep Flet table updates instantaneous.
  - [`RemoteGatewaySettingsPersister`](../ui/controllers/remote_gateway_settings_persister.py): Synchronizes `gateway_enabled` across `settings.ini`, `SettingsManager`, `.env`, and runtime backend.
  - [`EVPFleetConnectionCard`](../ui/cards/evp_fleet_connection_card.py): Unregisters `EVPNotifier` listeners deterministically in `will_unmount()`.
  - [`DashboardDataCoordinator`](../ui/controllers/dashboard_data_coordinator.py): Updates local `HardwareConnectionManager` passive mirrors (`remote_hardware_status`) from IPC telemetry frames.

---

## 2. Real Flet UI Architecture & View Hierarchy

The frontend is built using **[Flet](https://flet.dev/)** (Python + Flutter engine) located in [`ui/`](../ui).

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
├── cards/                          # Modular Settings & Inspector Cards (OCP Pattern)
│   ├── evp_fleet_connection_card.py    # Emergency fleet vehicle registration & RFID/transponder config
│   ├── evp_safety_parameters_card.py  # Preemption distance gates, max dwell watchdog & clearance
│   ├── remote_gateway_card.py          # Go Web Gateway toggles, port 2201 & Tailscale mesh status
│   ├── account_settings_card.py        # Operator user profile, roles (RBAC) & credentials
│   ├── database_settings_card.py       # Database engine selection (SQLite/PostgreSQL) & migrations
│   ├── hardware_connection_card.py     # NTCIP 1202 & UTMC field controller connection pool
│   ├── piloting_school_card.py         # Autonomous PBT pacing & RL graduation thresholds
│   ├── reward_weights_card.py          # Delay, pressure, queue & speed reward balancing
│   ├── traffic_rules_card.py           # Minimum green, yellow clearance & all-red constraints
│   ├── yellow_schedule_card.py         # Automated overnight flashing yellow schedules
│   ├── monitor_settings_card.py        # External MQTT broker / HTTP webhook telemetry
│   ├── advanced_system_card.py         # Watchdog timeouts, IPC buffer sizes & heartbeats
│   ├── advanced_dqn_card.py            # DQN replay buffer size, target network sync & epsilon
│   └── advanced_ppo_card.py            # PPO clip ratio, entropy coefficient & value loss coef
│
├── widgets/                        # Specialized Modular UI Widgets
│   ├── live_canvas_map_widget.py   # High-performance custom canvas drawing roads and signals
│   ├── evp_vehicle_marker.py       # Custom canvas renderer for emergency vehicles (shapes & sirens)
│   ├── evp_vehicle_card.py         # Floating telemetry card showing real-time GPS, speed & ETA
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

The **Planning View** ([`ui/views/planning_view.py`](../ui/views/planning_view.py)) enables municipal traffic engineers to interactively inspect and configure physical road networks:
- **Topology Grouping:** Group intersection clusters into coordinated arterial corridors (Green Waves).
- **Phase & Stage Inspector:** Inspect minimum green constraints, yellow clearance, and all-red intergreen buffers.
- **Export Handler:** Export modified signal timing plans directly to controller connection repositories or CSV templates.

For vector map rendering details, see [Map Rendering & Heatmaps](RENDERING_AND_HEATMAPS.md).

---

## 4. System Tray & Single Instance Lock (`SingleInstanceLock`)

CARINA runs seamlessly as a background system daemon with a native desktop tray icon:

### 4.1 System Tray Management ([`UITrayManager`](../src/launcher/ui_tray_manager.py))
- **Tray Actions:** Minimize to Tray, Open Dashboard, View Live Logs, Restart Services, Graceful Shutdown.
- **Notification Popups:** Emits native OS notifications when the Watchdog detects microservice crashes or when the Guardian Agent fires an emergency safety veto.

### 4.2 Single Instance Lock ([`SingleInstanceLock`](../src/launcher/single_instance.py))
- **Port:** `42123`
- If a user double-clicks `carina.py` or the executable while CARINA is already running:
  1. The duplicate process attempts to bind TCP port `42123`.
  2. Upon failure, it transmits a `RESTORE` command signal over the local TCP socket to the primary instance.
  3. The primary instance brings the Flet window to the foreground, and the duplicate process terminates cleanly.

---

## 5. Modular Settings Cards Architecture (`ui/cards/`)

CARINA’s configuration view ([`ui/views/settings_view.py`](../ui/views/settings_view.py)) follows an Open-Closed Component Architecture (OCP) assembled via [`SettingsConfigurator`](../ui/builders/settings_configurator.py):

| Card Component | Description | Auto / Manual Modes |
| :--- | :--- | :--- |
| **`EVPFleetConnectionCard`** | Emergency vehicle fleet registration & RFID transponders | • Corporation Tagging (Police, SAMU, Fire)<br>• Plate Authorization & Access Blacklisting |
| **`EVPSafetyParametersCard`** | Preemption kinematics, gates & safety clearances | • Entry Detection Gate ($60\text{--}160\text{ m}$)<br>• Exit Threshold ($\le 15\text{ m}$)<br>• Dwell Watchdog ($45\text{ s}$)<br>• Mandatory Yellow/All-Red Clearance |
| **`RemoteGatewayCard`** | Go Web Gateway & Tailscale mesh management | • Port 2201 Web Gateway Daemon Toggle<br>• Tailscale Funnel Status & Public URL Inspector |
| **`AccountSettingsCard`** | Operator authentication & RBAC user profiles | • Role Assignment (Operator, Superuser)<br>• Session Security & Password Validation |
| **`DatabaseSettingsCard`** | SQLite & PostgreSQL storage backend configuration | • DB Engine Switcher & Pool Configuration<br>• Connection Verification & Schema Migrations |
| **`PilotingSchoolCard`** | Lifecycle duration pacing and promotion rules | • Auto Duration Pacing (Network Size)<br>• Auto Fluid Dynamics Graduation Margin ($\delta^*$) |
| **`RewardWeightsCard`** | RL optimization weights (Waiting Time vs Vehicle Flow) | • Auto Physical Balancing (HCM Travel Time $\tau$)<br>• Manual Weight Overrides |
| **`YellowScheduleCard`** | Autonomous overnight flashing yellow schedules | • Time Window Scheduler (HH:MM)<br>• Intersection/Network Selective Targeting |
| **`AdvancedSystemCard`** | System-level PBT and Watchdog parameters | • PBT Exploitation Percentile<br>• Watchdog Grace Period & Analysis Intervals |
| **`AdvancedDQNCard`** | Deep Q-Network hyperparameter configuration | • Replay Buffer Capacity, Target Net Sync Frequency, $\epsilon$-decay |
| **`AdvancedPPOCard`** | Proximal Policy Optimization hyperparameter configuration | • Clip Ratio ($\epsilon=0.2$), Entropy Coef, Value Loss Coef |
| **`TrafficRulesCard`** | Statutory safety and minimum signal timings | • Min Green, Yellow Clearance, All-Red Buffers |
| **`HardwareConnectionCard`** | Physical field controllers (NTCIP / UTMC) | • IP Endpoints, SNMP Credentials & Fail-Safe Test |
| **`MonitorSettingsCard`** | External telemetry and incident streaming | • MQTT Broker / HTTP Webhook Endpoints |

---

## 6. EVP Visual Canvas Markers & Live Telemetry Inspector (`ui/widgets/`)

For desktop monitoring, CARINA renders active emergency vehicles in real time directly on the Flet live canvas:

- **`EVPVehicleMarker` ([`ui/widgets/evp_vehicle_marker.py`](../ui/widgets/evp_vehicle_marker.py)):**
  - **Corporation Glyphs:** Renders distinct vector silhouettes based on vehicle corporation:
    - *Ambulance / SAMU:* Equilateral Triangle ($\Delta$, White `#FFFFFF` / Alert Red `#E53935`).
    - *Firefighters / Bombeiros:* Square ($\square$, Orange `#FF9800`/`#FF8C00` / Alert Fire Red `#FF3D00`).
    - *Police / Military:* Circle ($\bigcirc$, Dark Blue `#1E3A8A` / Alert Royal Blue `#2563EB`).
  - **Siren Animator:** When `siren_active=True`, the marker pulses concentric strobe rings at $2.5\text{ Hz}$ across the canvas, alerting operators to an active emergency run.
  - **Dynamic Heading:** Automatically rotates vehicle orientation to match real-time GPS bearing degrees.

- **`EVPVehicleCard` ([`ui/widgets/evp_vehicle_card.py`](../ui/widgets/evp_vehicle_card.py)):**
  - Floating HUD card overlay displaying callsign, velocity ($\text{km/h}$), siren state, distance to downstream signal stop bar ($\text{m}$), and preemption status (`APPROACHING`, `HOLD_ACTIVE`, `CLEARED`).

---

## 7. Central Control Operator (CCO) Web & Mobile Architecture (`src_tsx/src_cco`)

In addition to the native Flet desktop GUI, CARINA includes a modern web-based **Central Control Operator (CCO)** platform built in **React 18**, **TypeScript**, **TailwindCSS**, and **Vite** located in [`src_tsx/src_cco/`](../src_tsx/src_cco). It is designed according to **Clean Architecture** principles, guaranteeing total decoupling between domain traffic rules, streaming infrastructure, and presentation components:

```text
src_tsx/src_cco/
├── domain/                         # Pure Domain Entities, Models & Business Services
│   ├── models/                     # Core Business Entities
│   │   ├── Topology.ts             # MapTopology, Node, Edge, Bounds interfaces
│   │   ├── CongestionLevel.ts      # Domain VO resolving retention colors and thresholds
│   │   ├── EmergencyVehicle.ts     # Telemetry & Preemption state model (SAMU, Bombeiros, Polícia)
│   │   └── TrafficLight.ts         # Signal phase heads, display state & timing models
│   ├── services/                   # Pure Geometric & Cartographic Domain Services
│   │   ├── MapProjectionService.ts # Isotropic 2D orthographic bounds & SVG aspect ratio calculations
│   │   ├── GeoProjectionService.ts # Canonical WGS84 GPS to SUMO Cartesian conversion
│   │   └── StreetTopologyGrouperService.ts # Road edge aggregation & heatmap path generation
│   └── contracts/                  # Boundary Interfaces (DIP)
│       ├── ITopologyRepository.ts  # Network topology fetching contract
│       └── ICcoStreamService.ts    # Real-time event streaming interface & connection status
│
├── application/                    # Application Use Cases & Orchestrators
│   └── usecases/
│       ├── LoadTopologyUseCase.ts          # Fetches & caches network geometry
│       ├── ManageEmergencyFleetUseCase.ts   # Categorizes vehicles by corporation & computes active alerts
│       └── ProcessTelemetryUseCase.ts      # Unpacks SSE stream payloads into domain state
│
├── infrastructure/                 # External Adapters, APIs & Gateways
│   ├── api/
│   │   └── HttpTopologyRepository.ts       # Axios/Fetch implementation of ITopologyRepository
│   ├── stream/
│   │   └── SseCcoStreamService.ts          # Server-Sent Events client (/cco/stream) with auto-reconnect
│   └── adapters/
│       └── EChartsOptionAdapter.ts         # Adapter transforming domain models to ECharts specs
│
└── presentation/                   # Reactive UI, Hooks, Components & Themes
    ├── context/
    │   └── ThemeContext.tsx                # Operator shift theme switcher (☀️ Light / 🌙 Dark) with localStorage
    ├── utils/
    │   └── haptics.ts                      # Tactile vibration feedback for mobile touch devices
    ├── hooks/
    │   ├── useCcoViewModel.ts              # Root view-model coordinating use cases, SSE stream & state
    │   ├── useCcoMapLayers.ts              # Memoized layers computation (streets, nodes, lights)
    │   └── useMapViewport.ts               # Pan, zoom, pinch-to-zoom gestures & smooth flyTo animations
    ├── components/
    │   ├── CcoHeader.tsx                   # Single-row responsive bar with fleet badges, search, theme & fullscreen
    │   ├── CcoMap.tsx                      # High-performance SVG vector map with isotropic pan/zoom
    │   ├── EvpAlertToast.tsx               # Collapsible emergency alert toast (micro-pill on mobile)
    │   └── map/
    │       ├── InspectionBottomSheet.tsx   # Ergonomic mobile bottom sheet & desktop element inspector
    │       ├── QuickSearchModal.tsx        # Instant search & auto-focus (flyTo) command palette
    │       ├── MapScaleBar.tsx             # Real-world dynamic metric scale (m/km) calibrated to SUMO
    │       ├── MapRoadsLayer.tsx           # Multi-stroke casing & congestion heatmap road rasterizer
    │       ├── MapIntersectionsLayer.tsx   # Interactive junction nodes with touch hit targets
    │       ├── MapTrafficLightsLayer.tsx   # Signal phase heads with active glow and diagnostics
    │       ├── MapEmergencyVehiclesLayer.tsx # Live vehicle markers, heading rotation & siren auras
    │       ├── MapGlowFilters.tsx          # SVG neon glow filter definitions for signals & alerts
    │       ├── MapLegend.tsx               # Collapsible operational heatmap & glyph legend
    │       └── MapZoomControls.tsx         # Isotropic zoom in, zoom out and camera recentering
    ├── styles/
    │   ├── flet_color_palette.json         # Exact color synchronization with desktop Flet palette
    │   └── index.css                       # Tailwind directives and viewport overscroll locks
    ├── App.tsx                             # Root component with ThemeProvider and modal orchestration
    └── main.tsx                            # React DOM entry point
```

---

## 8. Modern CCO UI/UX Capabilities & Ergonomics

The CCO frontend is engineered to provide an optimal operational experience whether accessed on a 4K command room videowall or on a mobile smartphone in the field:

1. **Ergonomic Mobile Bottom Sheet (`InspectionBottomSheet.tsx`):**
   - On mobile devices (`< 768px`), inspection cards dock to the bottom of the screen with a grab handle and native swipe-down dismiss gestures.
   - On desktop workstations (`>= 768px`), details float gracefully in a compact corner HUD.
   - Provides comprehensive real-time diagnostics for:
     - **Emergency Vehicles:** Callsign, velocity ($\text{km/h}$), GPS heading ($^\circ$), siren state, and target intersection.
     - **Traffic Lights:** Signal ID, active phase, live state indicator (Green, Yellow, Red), coordinates, and Fenix Watchdog supervision status.
     - **Intersections & Streets:** Physical junction nodes, street name, congestion percentage ($0\text{--}100\%$), and traffic flow rating.

2. **Dual Operational Shift Themes (☀️ Day / 🌙 Night):**
   - **Cartographic Day Mode (`#F7F7F7`):** High-contrast light background optimized for field operations and sunlight readability.
   - **Videowall Night Mode (`#020617`):** Deep dark palette designed to reduce operator eye strain during night shifts in darkened command centers.
   - Instantly switchable via a header toggle and automatically persisted in browser `localStorage`.

3. **Command Palette Quick Search & Cinematic Auto-Focus (`QuickSearchModal.tsx` & `flyTo`):**
   - Accessible via the header search button or global keyboard shortcuts (`Ctrl+K` or `/`).
   - Instantly indexes vehicles, semaphores, intersections, and street names.
   - Selecting any result triggers an animated camera flight (`flyTo`) with ease-out cubic interpolation, centering the target and opening its inspection sheet.

4. **Dynamic Metric Scale Bar (`MapScaleBar.tsx`):**
   - Real-world metric scale bar (e.g. `|—— 100 m ——|`) that automatically recalibrates in real time based on the active zoom level and SUMO's 1:1 metric coordinates.

5. **Interactive Fleet Filtering & Micro-Chips:**
   - Header badges for **SAMU**, **Bombeiros**, and **Polícia** function as interactive filters. Tapping a corporation highlights its units on the map while subtly dimming other vehicles.

6. **Immersive Fullscreen & Mobile Tactile Haptics:**
   - One-tap fullscreen button maximizes screen real estate by removing browser bars.
   - Micro-haptic vibrations (`navigator.vibrate`) provide physical confirmation when interacting with signals, vehicles, and zoom controls on supported touch devices.

---

## 9. Go Web Gateway Delivery, CCO Optimizations & Remote Connectivity

The web-based CCO is served by the high-throughput **Go Web Gateway** ([`src_go/web_gateway/`](../src_go/web_gateway)) running on port `2201` (`CARINA_GATEWAY_PORT`):

- **Fail-Closed & Token-Protected Delivery:** Returns `503 Service Unavailable` when disabled (`gateway_enabled=False`), serves compressed static React assets at `/cco/`, and protects `/cco/stream`, `/cco/topology`, and `/cco/broadcast` with constant-time `CARINA_CCO_AUTH_TOKEN`, `CARINA_CCO_ALLOWED_ORIGIN` CORS, and optional HTTPS/TLS.
- **Compositor-Thread & Viewport Optimizations (`src_tsx/src_cco/`):** Uses GPU compositor-only CSS keyframe animations (`transform` + `opacity`), `requestAnimationFrame` ref-driven pan/zoom in `useMapViewport.ts`, shallow equality state diffing in `useCcoViewModel.ts`, and pauses vehicle cleanup timers when `document.hidden` is true.
- **Sub-50ms SSE Telemetry Stream & Pinned Ingestion:** Exposes `/cco/stream` fed by SDS [`CCOBroadcastClient`](../src/sds/cco_broadcast_client.py) (latest-wins non-blocking publisher with SHA-256 leaf pinning via `PinnedHTTPSConnection`).
- **Tailscale Mesh & Remote Ingestion:** Integrates with Tailscale Funnel for encrypted remote access by field units and webhook ingestion from emergency dispatch CAD systems.

---

<div align="center">
  <img src="assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
