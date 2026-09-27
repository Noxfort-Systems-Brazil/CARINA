---
tags: [safety, guardian, watchdog, veto, failsafe, neuro-symbolic]
aliases: [Safety Architecture, Guardian Veto, Watchdog System, Safety Auditor]
---

# 🛡️ Safety Architecture, Guardian Firewall & Watchdog

This document details CARINA's dual-stage Neuro-Symbolic Safety Firewall ([`GuardianAgent`](../../src/agents/guardian_agent.py) & [`SafetyAuditor`](../../src/core/safety_auditor.py)), hardware fail-safe mechanisms, and the real-time deterministic [`Watchdog`](../../src/watchdog/watchdog_process.py) process.

⬅️ Back to [Main Documentation Hub](../CARINA_MOC.md) | 🚦 See [Hardware Drivers](hardware_drivers.md) | 🧠 See [Neural Formulations](../RESEARCH_NOTES.md) | 🧪 See [Testing & Validation](testing.md)

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

The [`SafetyAuditor`](../../src/core/safety_auditor.py) enforces strict physical constraints that can never be relaxed, modified, or bypassed by neural network optimization:

| Rule ID | Name | Constraint Description | Action on Violation |
| :--- | :--- | :--- | :--- |
| **SR-01** | **Minimum Green Time** | Active phase must remain green for at least $T_{min} = 7.0\text{ s}$ to clear queued vehicles. | Force `ACTION_KEEP_PHASE`. |
| **SR-02** | **Yellow Clearance** | Any phase transition must execute a mandatory $3.0\text{ s}$ yellow warning interval. | Intercept action; inject Yellow phase. |
| **SR-03** | **All-Red Interval** | Conflicting directional movements require a $2.0\text{ s}$ all-red clearance interval. | Inject All-Red clearance state. |
| **SR-04** | **Pedestrian Protection** | Activated pedestrian push-buttons guarantee an uninterrupted walk/flashing interval. | Lock conflicting vehicle movements. |
| **SR-05** | **Conflict Matrix** | Prevents concurrent green indications on conflicting or intersecting lanes. | Hard veto; revert to safe resting state. |

---

## 3. Neural Spillback Veto (`GuardianAgent`)

The **Guardian Agent** ([`src/agents/guardian_agent.py`](../../src/agents/guardian_agent.py)) runs a Dueling Deep Q-Network over TCN temporal representations to estimate **Spillback Risk** ($Q_{risk} \in [0.0, 1.0]$):

- **Threshold ($\tau_{risk}$):** $0.80$ (configurable in `config/settings.ini`).
- **Emergency Override:** If $Q(s, a_{proposed}) > 0.80$, the tactical agent's proposal is vetoed. The Guardian injects an emergency clearance phase to discharge the congested arterial link before upstream gridlock occurs.

---

## 4. Real-Time Process Watchdog (`src/watchdog/`)

The `Watchdog` microservice ([`src/watchdog/watchdog_process.py`](../../src/watchdog/watchdog_process.py) and [`src/watchdog/watchdog_logic.py`](../../src/watchdog/watchdog_logic.py)) monitors the liveness of all 8 CARINA microservices:

- **Heartbeat Interval:** 100 ms via the `wd` IPC queue.
- **Heartbeat Timeout:** 5.0 seconds (initial grace period: 10 seconds).
- **Fail-Safe Mechanism:** If the `AI_Process` or `CentralController` crashes, deadlocks, or misses consecutive heartbeats:
  1. The Watchdog notifies the desktop UI tray.
  2. It immediately signals the [`FailsafeManager`](../../src/controller/failsafe_manager.py) to drop phase holds on physical controllers.
  3. Physical traffic controllers autonomously revert to local fixed-time plans or yellow flash.
  4. Triggers the **F.E.N.I.X. Process Supervisor** (`on_fenix_trigger`) to initiate autonomous recovery and state reconciliation.

---

## 5. F.E.N.I.X. Self-Healing & Crash Recovery Architecture (`src/fenix/`)

To achieve true autonomous 24/7 resilience without manual operator intervention, CARINA implements **F.E.N.I.X.** (Fault-tolerant Engine for Networked Intelligent eXecution) in [`src/fenix/`](../../src/fenix).

```text
       Watchdog Timeout / Process Crash
                     │
                     ▼
          ┌─────────────────────┐
          │   FenixSupervisor   │ (Orchestrator Facade)
          └──────────┬──────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────────┐     ┌──────────────────────┐
│  RecoveryPolicy  │     │   SubprocessRunner   │
│(Windowed Backoff)│     │(SIGTERM -> SIGKILL)  │
└──────────────────┘     └──────────┬───────────┘
                                    │ Spawns New Child
                                    ▼
                         ┌──────────────────────┐
                         │   StateReconciler    │
                         │(FROZEN_SYNC Mode)    │
                         └──────────┬───────────┘
                                    │ Wait Next Transition (Zero Collision Risk)
                                    ▼
                         ┌──────────────────────┐
                         │    NORMAL (Active)   │
                         └──────────────────────┘
```

### 5.1 F.E.N.I.X. Lifecycle States (`FenixState`)
Defined in [`src/fenix/protocols.py`](../../src/fenix/protocols.py):
- **`IDLE`**: Initial state before process supervision starts.
- **`NORMAL`**: Supervised AI engine is operating nominally with full actuation authority.
- **`SUSPECT`**: Process heartbeat missed or unhealthy telemetry detected by Watchdog.
- **`RESTARTING`**: Zombie process terminated; awaiting backoff window before respawn.
- **`FROZEN_SYNC`**: Resurrected process is receiving live telemetry, but neural inference and actuation commands are strictly locked (`is_inference_allowed = False`).
- **`SHADOW_WARMUP`**: Background forward passes warm up PyTorch caches and GATv2 node embeddings.
- **`HANDOVER_PENDING`**: Waiting for physical controllers to transition to a safe stage boundary.
- **`FAILSAFE_ACTIVE`**: Fallback mode where physical controllers run autonomous fixed-time plans while recovery executes.
- **`HALTED`**: Maximum crash quota exceeded within the sliding window; locks system in safe fallback and alerts operators.

### 5.2 Windowed Crash Recovery Policy (`WindowedCrashRecoveryPolicy`)
Located in [`src/fenix/recovery_policy.py`](../../src/fenix/recovery_policy.py):
- Tracks process crashes within a sliding time window (default: $300\text{ s}$).
- Computes exponential backoff between restart attempts ($2.0\text{ s} \to 4.0\text{ s} \to 8.0\text{ s}$).
- Prevents infinite restart loops: if crash rate exceeds $M$ failures (default: 5), transitions to `HALTED`.

### 5.3 Clean Boundary Handover (`StateReconciler`)
Located in [`src/fenix/state_reconciler.py`](../../src/fenix/state_reconciler.py):
- **Mid-Stage Collision Hazard:** When the AI process resurrects, injecting commands mid-stage into a physical intersection could violate clearance intervals or cause abrupt signal switches.
- **Zero-Risk Handshake:** The reconciler interrogates current physical controller stages (`reconcile_with_field`).
- **Phase Transition Unlock:** Neural control is only unlocked (`on_stage_transition_detected`) when the physical controller naturally transitions to its next local stage, guaranteeing smooth, collision-free resumption.

---

For physical controller communication details, see [Hardware Drivers](hardware_drivers.md).
