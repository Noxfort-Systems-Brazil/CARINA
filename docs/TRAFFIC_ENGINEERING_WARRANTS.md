---
tags: [warrants, mutcd, fhwa, traffic-engineering, safety, analysis, sas]
aliases: [Traffic Engineering Warrants, Signal Warrants, MUTCD Analysis, Warrant Evaluator]
---

# 🚦 Traffic Engineering Signal Warrants & Infrastructure Analysis

This document specifies CARINA's engineering warrant analysis subsystem located in [`src/analysis/`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/analysis). It details the mathematical formulation and automated evaluation of formal traffic signal warrants based on the **FHWA MUTCD** (Manual on Uniform Traffic Control Devices) and Brazilian municipal standards.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 📈 See [MFD & Analytics](MFD_AND_ANALYTICS.md) | 🔍 See [Explainable AI & SAS](XAI_AND_SAS.md)

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
             ├──> Warrant 1: Eight-Hour Vehicular Volume
             ├──> Warrant 2: Four-Hour Vehicular Volume
             ├──> Warrant 3: Peak Hour Delay & Volume
             ├──> Warrant 7: Crash Experience & Critical Rate
             └──> Warrant 8: Roadway Network Coordination
```

---

## 2. Implemented MUTCD Warrants in `src/analysis/`

### 2.1 Warrant 1: Eight-Hour Vehicular Volume (`warrant_strategies.py`)
Evaluates whether traffic volume on intersecting streets meets minimum vehicular volume thresholds for any 8 hours of an average day:
- **Condition A (Minimum Vehicular Volume):** Major and minor street approach volumes exceed critical hourly volumes $V_{major} \ge 500\text{ veh/h}$ and $V_{minor} \ge 150\text{ veh/h}$.
- **Condition B (Interruption of Continuous Traffic):** Traffic volume on a major street is so heavy that traffic on a minor intersecting street suffers excessive delay ($V_{major} \ge 750\text{ veh/h}$ and $V_{minor} \ge 75\text{ veh/h}$).

### 2.2 Warrant 2: Four-Hour Vehicular Volume
Applies when volume on major and minor streets satisfies the MUTCD 4-hour curves plotted in [`src/analysis/warrant_math.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/analysis/warrant_math.py).

### 2.3 Warrant 3: Peak Hour Volume & Delay
Evaluates whether traffic conditions during the single highest-volume hour of the day cause extreme delay or hazard:
- Total stopped time delay experienced by traffic on one minor-street approach equals or exceeds 4 vehicle-hours for a one-lane approach.
- Volume on the approach equals or exceeds 100 vehicles per hour.

### 2.4 Warrant 7: Crash Experience
Evaluates whether a traffic signal will reduce accident rates:
- An adequate trial of alternative measures with satisfactory compliance has failed to reduce the crash frequency.
- Five or more reported crashes of types susceptible to relief by a traffic signal (e.g., right-angle collisions) have occurred within a 12-month period.

### 2.5 Warrant 8: Roadway Network
Justifies signal installation to encourage concentration and organization of traffic flow on a coordinated arterial network.

---

## 3. Mathematical Utilities (`warrant_math.py`)

Located in [`src/analysis/warrant_math.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/analysis/warrant_math.py):
- **85th-Percentile Speed Calculation:** Evaluates if posted speed limits should scale warrant threshold volumes down by 70% (applicable when major street speed exceeds $70\text{ km/h}$ or in isolated rural communities).
- **Critical Flow Ratio:** Computes lane-by-lane saturation flows and degree of saturation ($X = v/c$).
- **Moving-Window Accumulation:** Aggregates time-series samples into robust hourly volume bins.
