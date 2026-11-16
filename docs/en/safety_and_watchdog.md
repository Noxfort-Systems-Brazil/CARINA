---
tags: [safety, guardian, watchdog, veto, failsafe, neuro-symbolic]
aliases: [Safety Architecture, Guardian Veto, Watchdog System, Safety Auditor]
---

# 🛡️ Safety Architecture, Guardian Firewall & Watchdog

This document details CARINA's dual-stage Neuro-Symbolic Safety Firewall ([`GuardianAgent`](../../src/agents/guardian_agent.py) & [`SafetyAuditor`](../../src/core/safety_auditor.py)), hardware fail-safe mechanisms, and the real-time deterministic [`Watchdog`](../../src/watchdog/watchdog_process.py) process.

⬅️ Back to [Main Documentation Hub](carina_moc.md) | 🚨 See [EVP Preemption](evp_and_preemption.md) | 🚦 See [Hardware Drivers](hardware_drivers.md) | 🧠 See [Neural Formulations](research_notes.md) | 🧪 See [Testing & Validation](testing.md)

---

## 1. Dual-Stage Safety Firewall Overview

CARINA completely decouples physical public safety from deep reinforcement learning performance. Neural policies can suggest actions, but all actions pass through physical logit masking and multi-stage safety vetting before dispatching to physical hardware:

```text
State + PAE Latent ──> [PhysicalActionMasker] ──> [ActionVetoResolver] ──> Actuation
                        (Logit Clearance/MinG)      ├── 0. EVP Priority Intercept (SR-00)
                                                    ├── 1. Symbolic Rules (SR-01..SR-06)
                                                    └── 2. QR-D3QN + Noisy-OR Risk Veto
```

- [`PhysicalActionMasker`](../../src/engine/physical_action_masker.py): Constrains `ActorCriticNet` FP32 logits prior to sampling, forbidding premature switches during yellow/all-red clearance or below minimum green and forcing transitions above maximum green.
- [`ActionVetoResolver`](../../src/engine/action_veto_resolver.py): Orchestrates EVP preemption overrides (`SR-00`) and `GuardianAgent` spillback vetoes (`ACTION_KEEP_STAGE`) in the step pipeline.

---

## 2. Symbolic Veto Rules Inventory (`SafetyAuditor`)

The [`SafetyAuditor`](../../src/core/safety_auditor.py) and [`GuardianSymbolicAuditor`](../../src/safety/guardian_symbolic_auditor.py) enforce strict physical constraints that can never be relaxed, modified, or bypassed by neural network optimization:

| Rule ID | Name | Constraint Description | Action on Violation |
| :--- | :--- | :--- | :--- |
| **SR-00** | **Emergency Preemption (EVP)** | Active emergency vehicle (SAMU/Fire/Police) approaching with siren engaged. | Intercept action; enforce safe yellow/all-red clearance, then inject `ACTION_HOLD` on target green corridor. |
| **SR-01** | **Minimum Green Time** | Active phase must remain green for at least $T_{min} = 7.0\text{ s}$ to clear queued vehicles. | Force `ACTION_KEEP_PHASE`. |
| **SR-02** | **Yellow Clearance** | Any phase transition must execute a mandatory $3.0\text{ s}$ yellow warning interval. | Intercept action; inject Yellow phase. |
| **SR-03** | **All-Red Interval** | Conflicting directional movements require a $2.0\text{ s}$ all-red clearance interval. | Inject All-Red clearance state. |
| **SR-04** | **Minimum Red Time** | Non-served movements must satisfy a minimum red interval before being recalled. | Inhibit premature phase re-activation. |
| **SR-05** | **Maximum Green Ceiling (Anti-Starvation)** | Phase cannot exceed maximum green duration if competing approaches have waiting queues. | Force phase termination and transition to competing demand. |
| **SR-06** | **Conflict Matrix & Ghost Green** | Prevents concurrent green indications on conflicting or intersecting lanes. | Hard veto; revert to safe resting state. |

---

## 3. Calibrated Neural Spillback Veto (`GuardianAgent` & `src/safety/`)

The **Guardian Agent** ([`src/agents/guardian_agent.py`](../../src/agents/guardian_agent.py)) integrates a **Distributional Quantile-Regression Dueling Double DQN (`D3QN_TCN`, `num_quantiles = 32`)** with capacity-aware kinematic physics and non-compensatory risk fusion:

- **Tail-Risk Quantile Estimation ($\text{CVaR}_{\alpha}$):** `GuardianNeuralPredictor` evaluates worst-case lower quantiles ($\alpha = 0.20$) rather than mean Q-values alone.
- **Physical Kinematic & PAE Estimation ([`GuardianPhysicsEstimator`](../../src/safety/guardian_physics_estimator.py)):** Slices strictly incoming-edge sensor triplets (`edge_feature_dim`), normalizes queues against physical road vehicle capacities (`edge_capacities`), projects saturation growth over the intergreen clearance horizon $H = \text{yellow} + \text{all\_red}$, and queries counterfactual PAE forecasts (`decode_with_uncertainty` for `ADVANCE` vs `KEEP`).
- **Scale-Invariant Calibration & Noisy-OR Fusion ([`GuardianRiskCalibrator`](../../src/safety/guardian_risk_calibrator.py)):** Calibrates quantile spreads via regularized logistic regression and $F_2$-score threshold tuning on `CHILD` graduation, combining physical, PAE, and QR-D3QN risks with non-compensatory Noisy-OR ($1 - \prod_i (1 - c_i r_i)$) and a hard physical/PAE spillback floor.
- **Safe `CHILD`-Only Shadow Training & Freeze ([`GuardianShadowTrainer`](../../src/safety/guardian_shadow_trainer.py) & [`GuardianCheckpointService`](../../src/safety/guardian_checkpoint_service.py)):** Trains QR-D3QN off-policy exclusively during `Maturity.CHILD` while physical signals follow fixed-time plans; upon promotion to `TEEN`/`ADULT`, runs `finalize_child_calibration()` and `freeze_for_deployment()` (releasing `target_net`, `optimizer`, and PER buffers) and atomically persists `guardian_{tl_id}.pth`.

---

## 4. Real-Time Process Watchdog (`src/watchdog/`)

The `Watchdog` microservice ([`src/watchdog/watchdog_process.py`](../../src/watchdog/watchdog_process.py) and [`src/watchdog/watchdog_logic.py`](../../src/watchdog/watchdog_logic.py)) monitors the liveness of all 8 CARINA microservices:

- **Heartbeat Interval:** 100 ms via the `wd` IPC queue.
- **Heartbeat Timeout:** 5.0 seconds (initial grace period: 10 seconds).
- **Fail-Safe Mechanism:** If the `AI_Process` or `CentralController` crashes, deadlocks, or misses consecutive heartbeats:
  1. The Watchdog notifies the desktop UI tray.
  2. It signals [`FailsafeManager`](../../src/controller/failsafe_manager.py) -> `HardwareGatewayCoordinator.on_failsafe_triggered()`, invoking `EmergencyReleaseControlAll()` on the Go gateway (releasing holds while keeping SNMP drivers/trap listener ready for `resume_control` on recovery).
  3. Physical traffic controllers autonomously revert to local fixed-time plans or yellow flash.
  4. Triggers the **F.E.N.I.X. Process Supervisor** (`on_fenix_trigger` via `fenix` queue and [`fenix_supervision_loop.py`](../../src/launcher/fenix_supervision_loop.py)) to initiate autonomous recovery and closed-loop state reconciliation.
  5. **Preemption Dwell Watchdog:** In parallel, [`EVPPreemptionEngine`](../../src/evp/evp_preemption_engine.py) enforces a strict $45.0\text{ s}$ maximum preemption dwell timeout, releasing arterial holds if vehicle checkout is delayed or missed.

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

### 5.3 Clean Boundary Handover (`StateReconciler` & `FenixStageDispatcher`)
Located in [`src/fenix/state_reconciler.py`](../../src/fenix/state_reconciler.py) and [`src/controller/fenix_stage_dispatcher.py`](../../src/controller/fenix_stage_dispatcher.py):
- **Mid-Stage Collision Hazard:** When the AI process resurrects, injecting commands mid-stage into a physical intersection could violate clearance intervals or cause abrupt signal switches.
- **Closed-Loop Field Handshake:** `FenixStageDispatcher` queries fresh controller snapshots from the Go gateway, decodes active field stages via [`HardwareTelemetryDecoder`](../../src/drivers/hardware_telemetry_decoder.py), and reconciles `StateReconciler` (`reconcile_with_field` via `fenix_post_resurrection`).
- **Phase Transition Unlock:** Neural control is unlocked (`on_stage_transition_detected`) when the physical controller transitions to a safe stage boundary, emitting `fenix_handover_complete` -> `HANDOVER_COMPLETE` so `FenixSupervisor` confirms resurrection and resumes heartbeats (`resume_control`).

---

For physical controller communication details, see [Hardware Drivers](hardware_drivers.md).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
