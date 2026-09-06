---
tags: [safety, guardian, watchdog, veto, failsafe, neuro-symbolic]
aliases: [Safety Architecture, Guardian Veto, Watchdog System, Safety Auditor]
---

# 🛡️ Safety Architecture, Guardian Firewall & Watchdog

This document details CARINA's dual-stage Neuro-Symbolic Safety Firewall ([`GuardianAgent`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/agents/guardian_agent.py) & [`SafetyAuditor`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/core/safety_auditor.py)), hardware fail-safe mechanisms, and the real-time deterministic [`Watchdog`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/watchdog/watchdog_process.py) process.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🚦 See [Hardware Drivers](HARDWARE_DRIVERS.md) | 🧠 See [Neural Formulations](RESEARCH_NOTES.md) | 🧪 See [Testing & Validation](TESTING.md)

---

## 1. Dual-Stage Safety Firewall Overview

CARINA completely decouples physical public safety from deep reinforcement learning performance. Neural policies can suggest actions, but all actions must be formally cleared through a two-tier safety firewall before dispatching to physical hardware:

```text
Proposed Phase Action ──> [1. Symbolic Safety Rules] ──> [2. Neural Spillback Veto] ──> Hardware Actuation
                               │                               │
                               ├── Veto (Min Green / Yellow)   └── Veto (Spillback Risk > 0.8)
                               └── Force Keep Phase            └── Force Clearing Phase
```

---

## 2. Symbolic Veto Rules Inventory (`SafetyAuditor`)

The [`SafetyAuditor`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/core/safety_auditor.py) enforces strict physical constraints that can never be relaxed, modified, or bypassed by neural network optimization:

| Rule ID | Name | Constraint Description | Action on Violation |
| :--- | :--- | :--- | :--- |
| **SR-01** | **Minimum Green Time** | Active phase must remain green for at least $T_{min} = 7.0\text{ s}$ to clear queued vehicles. | Force `ACTION_KEEP_PHASE`. |
| **SR-02** | **Yellow Clearance** | Any phase transition must execute a mandatory $3.0\text{ s}$ yellow warning interval. | Intercept action; inject Yellow phase. |
| **SR-03** | **All-Red Interval** | Conflicting directional movements require a $2.0\text{ s}$ all-red clearance interval. | Inject All-Red clearance state. |
| **SR-04** | **Pedestrian Protection** | Activated pedestrian push-buttons guarantee an uninterrupted walk/flashing interval. | Lock conflicting vehicle movements. |
| **SR-05** | **Conflict Matrix** | Prevents concurrent green indications on conflicting or intersecting lanes. | Hard veto; revert to safe resting state. |

---

## 3. Neural Spillback Veto (`GuardianAgent`)

The **Guardian Agent** ([`src/agents/guardian_agent.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/agents/guardian_agent.py)) runs a Dueling Deep Q-Network over TCN temporal representations to estimate **Spillback Risk** ($Q_{risk} \in [0.0, 1.0]$):

- **Threshold ($\tau_{risk}$):** $0.80$ (configurable in `config/settings.ini`).
- **Emergency Override:** If $Q(s, a_{proposed}) > 0.80$, the tactical agent's proposal is vetoed. The Guardian injects an emergency clearance phase to discharge the congested arterial link before upstream gridlock occurs.

---

## 4. Real-Time Process Watchdog (`src/watchdog/`)

The `Watchdog` microservice ([`src/watchdog/watchdog_process.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/watchdog/watchdog_process.py) and [`src/watchdog/watchdog_logic.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/watchdog/watchdog_logic.py)) monitors the liveness of all 8 CARINA microservices:

- **Heartbeat Interval:** 100 ms via the `wd` IPC queue.
- **Heartbeat Timeout:** 5.0 seconds (initial grace period: 10 seconds).
- **Fail-Safe Mechanism:** If the `AI_Process` or `CentralController` crashes, deadlocks, or misses consecutive heartbeats:
  1. The Watchdog notifies the desktop UI tray.
  2. It immediately signals the [`FailsafeManager`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/controller/failsafe_manager.py) to drop phase holds on physical controllers.
  3. Physical traffic controllers autonomously revert to local fixed-time plans or yellow flash.

For physical controller communication details, see [Hardware Drivers](HARDWARE_DRIVERS.md).
