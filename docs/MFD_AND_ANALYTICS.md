---
tags: [mfd, analytics, dynamics, density, gating, capacity-drop]
aliases: [MFD Engine, Network Analytics, Traffic Physics, Macroscopic Fundamental Diagram]
---

# 📈 Macroscopic Fundamental Diagram & Network Analytics

This document details the Macroscopic Fundamental Diagram subsystem located in [`src/mfd/`](../src/mfd), the **`MFD_Worker`** process, macroscopic traffic flow physics, perimeter gating algorithms, and the incident filter cache.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 📊 See [Traffic Warrants](TRAFFIC_ENGINEERING_WARRANTS.md) | 🧠 See [Neural Formulations](RESEARCH_NOTES.md)

---

## 1. Macroscopic Fundamental Diagram (MFD) Theory

The **Macroscopic Fundamental Diagram (MFD)** relates the total accumulation of vehicles (density $K$) in an urban network to the total space-mean flow ($Q$). Unlike microscopic models that track individual car-following interactions, the MFD provides a holistic, network-wide representation of urban traffic states.

```text
       Q (veh/h)
          ▲                Zone 1: Uncongested (Tactical PPO Active)
     Qmax │           /\   Zone 2: Capacity Drop (Perimeter Gating Triggered)
          │          /  \  Zone 3: Gridlock / Collapse (Emergency Override)
          │         /    \
          └────────┴──────┴────────► K (veh/km)
                  Kcrit   Kjam
```

- **Zone 1: Uncongested Region ($K < K_{crit}$):** Individual intersections operate with local PPO-TCN policies maximizing local green allocation.
- **Zone 2: Capacity Drop Region ($K > K_{crit}$):** Traffic friction between queues causes global throughput to degrade sharply (*Capacity Drop*).
- **Zone 3: Gridlock ($K \to K_{jam}$):** Urban arterial gridlock where vehicles cannot clear intersections due to downstream spillback.

---

## 2. Mathematical Formulations

Network-wide density $K_{net}$ and space-mean flow $Q_{net}$ are aggregated as weighted averages across all $N$ monitored road segments:

$$K_{net} = \frac{\sum_{i=1}^N k_i \cdot L_i}{\sum_{i=1}^N L_i}, \quad Q_{net} = \frac{\sum_{i=1}^N q_i \cdot L_i}{\sum_{i=1}^N L_i}$$

Where:
- $k_i$: Density of link $i$ (vehicles per kilometer).
- $q_i$: Flow rate of link $i$ (vehicles per hour).
- $L_i$: Physical length of link $i$ in meters.

---

## 3. Core Modules in `src/mfd/`

The MFD analytical suite consists of 35 specialized modules in [`src/mfd/`](../src/mfd):

### 3.1 MFD Worker Process (`mfd_worker.py`)
Runs as an isolated operating system process spawned by `ProcessManager`. It listens on the `mfd_trigger` IPC queue, performs macroscopic regressions, and returns results on `mfd_results`.

### 3.2 Comparison Engine & Baseline Manager (`mfd_comparison_engine.py` & `mfd_baseline_manager.py`)
- Continuously compares current adaptive AI throughput against fixed-time baseline curves.
- Computes vehicle hours traveled (VHT) and vehicle kilometers traveled (VKT) savings.

### 3.3 Historical Reconstructor (`mfd_history_reconstructor.py`)
Rebuilds flow-density scatter plots from PostgreSQL `synapse_fluid_dynamics` across multi-day observation windows.

### 3.4 Urban Impact Calculator (`mfd_impact_calculator.py`)
Quantifies municipal emissions reductions ($\text{CO}_2$, $\text{NO}_x$), fuel savings, and economic productivity gains resulting from congestion reduction.

---

## 4. Perimeter Gating Actuation

When network density exceeds critical capacity ($K_{net} \ge K_{crit}$):
1. The `MFD_Worker` emits a perimeter gating alert to the `CentralController`.
2. Perimeter intersections bordering the congested urban core throttle incoming green times ($T_{green} \leftarrow T_{green} \times \eta$, where $\eta \in [0.6, 0.8]$).
3. Outbound arterial corridors receive maximum green priority to flush vehicles out of the central business district.

---

## 5. Incident Filter Debug Cache (`.carina_incident_filter_cache.json`)

To prevent localized accidents or construction lane closures from corrupting the macroscopic MFD curve, [`src/drivers/incident_filter.py`](../src/drivers/incident_filter.py) isolates anomalous links and stores active incident states in `.carina_incident_filter_cache.json` for rapid recovery across system restarts.
