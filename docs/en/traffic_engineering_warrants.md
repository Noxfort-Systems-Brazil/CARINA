---
tags: [warrants, mutcd, fhwa, traffic-engineering, safety, analysis, sas]
aliases: [Traffic Engineering Warrants, Signal Warrants, MUTCD Analysis, Warrant Evaluator]
---

# 🚦 Traffic Engineering Signal Warrants & Infrastructure Analysis

This document specifies CARINA's engineering warrant analysis subsystem located in [`src/analysis/`](../../src/analysis). It details the mathematical formulation and automated evaluation of formal traffic signal warrants based on the **FHWA MUTCD** (Manual on Uniform Traffic Control Devices) and Brazilian municipal standards.

⬅️ Back to [Main Documentation Hub](carina_moc.md) | 📈 See [MFD & Analytics](mfd_and_analytics.md) | 🔍 See [Explainable AI & SAS](xai_and_sas.md)

---

## 1. Automated Signal Warrant Evaluation

Before deploying or adjusting traffic signals, municipal engineers are legally required to demonstrate that an intersection satisfies formal engineering warrants. The **Smart Analysis System (SAS)** evaluates accumulated historical data from PostgreSQL to determine whether a traffic signal is justified or requires timing modifications.

```text
 Historical Traffic Data (PostgreSQL `synapse_fluid_dynamics`)
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
  │  (Warrant Strategies)│      │(Volume & Speed Math) │
  └──────────┬───────────┘      └──────────────────────┘
             │
             ├──> Warrant 1: VolumeWarrant (MUTCD Table 4C-1 Volumes)
             ├──> Warrant 2: DelayWarrant (Unacceptable Delay D)
             ├──> Warrant 3: QueueWarrant (P95 Statistical Queue)
             └──> Warrant 4: SaturationWarrant (Degree of Saturation X = v/c)
```

---

## 2. Implemented Traffic Engineering Warrant Strategies (`src/analysis/warrant_strategies.py`)

CARINA structures its engineering analysis using the **Strategy Pattern** registered in [`WarrantEvaluator`](../../src/analysis/warrant_evaluator.py):

### 2.1 Warrant 1: Volume Warrant (`VolumeWarrant`)
Evaluates approach traffic volumes using the fundamental traffic flow equation:
$$q = k \times (v \times 3.6)$$
- **MUTCD Table 4C-1 Thresholds:** Evaluates approach lanes and speed limits:
  - **1 Lane Major / 1 Lane Minor:** Condition A: $V_{major} \ge 500\text{ veh/h}$, $V_{minor} \ge 150\text{ veh/h}$. Condition B: $V_{major} \ge 750\text{ veh/h}$, $V_{minor} \ge 75\text{ veh/h}$.
  - **2+ Lanes Major / 2+ Lanes Minor:** Condition A: $V_{major} \ge 600\text{ veh/h}$, $V_{minor} \ge 200\text{ veh/h}$. Condition B: $V_{major} \ge 900\text{ veh/h}$, $V_{minor} \ge 100\text{ veh/h}$.
- **High-Speed 70% Reduction Factor:** If the posted major street speed exceeds $70\text{ km/h}$ ($19.44\text{ m/s}$), all volume thresholds are scaled by $0.70$ (e.g., $500 \to 350\text{ veh/h}$, $150 \to 105\text{ veh/h}$).

### 2.2 Warrant 2: Delay Warrant (`DelayWarrant`)
Quantifies operational delay experienced on secondary intersecting approaches relative to free-flow travel time:
$$D = \frac{L}{v_{\text{real}}} - \frac{L}{v_{\text{limit}}}$$
- Evaluates whether average delay exceeds the unacceptable delay threshold:
$$D_{avg} > D_{\text{threshold}}$$
- Default threshold: `unacceptable_delay = 90.0 s`.

### 2.3 Warrant 3: Queue P95 Warrant (`QueueWarrant`)
Audits queue buildup using 95th-percentile statistical distributions to prevent arterial spillback:
- Calculates the empirical 95th-percentile queue length $P95(Q)$ across accumulated sensor samples.
- Warrant is satisfied if:
$$P95(Q) > Q_{\text{threshold}}$$
- Default threshold: `max_queue_p95 = 15` vehicles.

### 2.4 Warrant 4: Degree of Saturation Warrant (`SaturationWarrant`)
Evaluates the volume-to-capacity ($v/c$) ratio across all approach lanes:
$$X = \frac{q}{N \times f_{\text{ideal}}}$$
Where:
- $q$: Space-mean vehicle volume ($\text{veh/h}$).
- $N$: Number of approach lanes.
- $f_{\text{ideal}}$: Ideal saturation flow per lane ($1800\text{ veh/h/lane}$).
- Warrant is satisfied if the maximum lane saturation ratio exceeds critical capacity:
$$X_{\max} > X_{\text{critical}}$$
- Default threshold: `saturation_critical = 0.85` ($85\%$ capacity).

---

## 3. Mathematical Utilities (`warrant_math.py`)

Located in [`src/analysis/warrant_math.py`](../../src/analysis/warrant_math.py):
- **`compute_volume_q(density, speed)`:** Computes space-mean flow volume $q = k \times (v \times 3.6)$.
- **`compute_delay(length, v_real, v_limit)`:** Computes real vehicular travel delay relative to posted speed limits.
- **`compute_p95(values)`:** Computes the empirical 95th-percentile queue length.
- **`compute_saturation_ratio(volume, num_lanes, ideal_flow)`:** Calculates the degree of saturation ($X = v/c$).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
