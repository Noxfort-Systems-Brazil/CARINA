---
tags: [research, ai, math, neural]
aliases: [Neural Research, Mathematical Formulations, PPO-TCN, GOMES]
---

# 🧠 Neural Research & Mathematical Formulations

This document details the mathematical framework, neural network architectures, and curriculum formulations underlying CARINA's **Graph-based Operational Multi-agent Expert System (GOMES)** and the **DA SILVA** maturation curriculum.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🏛️ See [Multiprocessing Architecture](../ARCHITECTURE.md) | 🛡️ See [Safety & Watchdog](SAFETY_AND_WATCHDOG.md) | 🔍 See [Explainable AI & SAS](XAI_AND_SAS.md)

---

## 1. PPO-TCN: Temporal Convolutional Networks over LSTMs

Standard Recurrent Neural Networks (LSTMs/GRUs) suffer from vanishing gradients and vanishing temporal context during long episode Backpropagation Through Time (BPTT). CARINA replaces LSTMs with a **Temporal Convolutional Network (TCN)** backbone in the PPO Tactical Agent.

```text
Input Tensor History: X ∈ ℝ^(B × C × T)
  B: Batch size
  C: Features per timestep (occupancy, speed, queue, phase)
  T: Temporal context window (e.g., T = 8 seconds at 10Hz = 80 frames)
```

### 1.1 Dilated Causal Convolutions

To ensure zero temporal leakage (the prediction at time $t$ depends only on timestamps $\le t$), TCN uses 1D dilated causal convolutions:

$$y(t) = (x \star_d f)(t) = \sum_{i=0}^{k-1} f(i) \cdot x(t - d \cdot i)$$

Where:
- $k$: Kernel size ($k = 3$)
- $d$: Dilation factor ($d = 2^l$ at layer index $l \in \{0, 1, 2, 3\}$)
- Receptive Field size: $RF = 1 + \sum_{l=0}^{L-1} (k - 1) \cdot d_l$

The TCN outputs a dense temporal representation tensor $H_{tcn}$, which feeds into the PPO Actor and Critic heads.

### 1.2 PPO Clipped Surrogate Objective

The PPO policy network is optimized using the clipped surrogate objective with Generalized Advantage Estimation (GAE):

$$L^{CLIP}(\theta) = \hat{\mathbb{E}}_t \left[ \min \left( r_t(\theta)\hat{A}_t, \text{clip}(r_t(\theta), 1-\epsilon, 1+\epsilon)\hat{A}_t \right) \right]$$

Where:
- $r_t(\theta) = \frac{\pi_\theta(a_t | s_t)}{\pi_{\theta_{old}}(a_t | s_t)}$ is the probability ratio.
- $\hat{A}_t = \sum_{l=0}^{\infty} (\gamma \lambda)^l \delta_{t+l}^V$ is the GAE advantage estimator.
- $\epsilon = 0.2$ is the policy clipping boundary.

---

## 2. Predictive Autoencoder (PAE) & Latent Space $Z$

The **Predictive Autoencoder (PAE)** predicts future traffic queue spillbacks from past spatio-temporal trends.

```text
        ┌──────────────┐          ┌───────────────────────┐          ┌──────────────┐
X_hist  │  PAE Encoder │ ───────> │  Latent Bottleneck Z  │ ───────> │  PAE Decoder │ ───> X_pred
(t-8s..t)└──────────────┘          │  Z ∈ ℝ^16             │          └──────────────┘      (t+1s..t+30s)
                                   └───────────────────────┘
```

### 2.1 PAE Loss Function

The PAE is trained offline and online using a joint Mean Squared Error (MSE) and Kullback-Leibler (KL) divergence regularization:

$$\mathcal{L}_{PAE} = \underbrace{\| X_{pred} - X_{future} \|_2^2}_{\text{Reconstruction & Prediction Loss}} + \beta \cdot D_{KL}\Big( q_\phi(Z|X) \,\parallel\, \mathcal{N}(0, I) \Big)$$

The 16-dimensional latent vector $Z \in \mathbb{R}^{16}$ captures the physical momentum of traffic queues and is concatenated into the PPO input vector.

---

## 3. Dueling DQN-TCN Guardian Agent

The **Guardian Agent** continuously estimates **Spillback Risk** for every intersection lane using a Dueling Deep Q-Network over TCN feature representations:

$$Q(s, a; \theta, \alpha, \beta) = V(s; \theta, \beta) + \left( A(s, a; \theta, \alpha) - \frac{1}{|\mathcal{A}|} \sum_{a' \in \mathcal{A}} A(s, a'; \theta, \alpha) \right)$$

Where:
- $V(s)$: Scalar baseline value of state $s$.
- $A(s, a)$: Advantage of taking phase action $a$.

If $\max_a Q(s, a_{spillback}) > \tau_{risk}$ (where $\tau_{risk} = 0.8$), the Guardian overrides the Tactical Agent's proposed phase and forces an emergency clearing phase.

---

## 4. Strategic Layer: Graph Attention Networks (GATv2 Lite)

To coordinate multi-intersection "Green Waves" across arterial avenues, CARINA models the road network as a directed graph $\mathcal{G} = (\mathcal{V}, \mathcal{E})$.

### 4.1 GATv2 Attention Weights

For connected intersections $i, j \in \mathcal{V}$, GATv2 computes dynamic attention coefficients $\alpha_{ij}$:

$$\alpha_{ij} = \frac{\exp\left( \mathbf{a}^T \text{LeakyReLU}\left( \mathbf{W} [h_i \,\|\, h_j] \right) \right)}{\sum_{k \in \mathcal{N}_i} \exp\left( \mathbf{a}^T \text{LeakyReLU}\left( \mathbf{W} [h_i \,\|\, h_k] \right) \right)}$$

Where:
- $h_i, h_j$: Feature representations of node $i$ and neighboring node $j$.
- $\mathbf{W}$: Shared weight matrix.
- $\mathbf{a}$: Learnable attention vector.

---

## 5. DA SILVA Maturation Curriculum Formulation

The **Dynamic Agent Safety Integrated Learning for Validated Autonomy (DA SILVA)** pipeline evaluates policy maturity using **Policy Shannon Entropy**:

$$\mathcal{H}(\pi_\theta(\cdot | s_t)) = -\sum_{a \in \mathcal{A}} \pi_\theta(a | s_t) \log \pi_\theta(a | s_t)$$

### 5.1 Progression Criteria and Dynamic Entropy Decay Curve

To ensure that random policies are never promoted prematurely, policy maturity uses an action-bounded entropy ceiling $E_{max} = \ln(|\mathcal{A}|)$ (where $E_{max} = \ln(3) \approx 1.0986$ for 3 actions) or normalized entropy $\mathcal{H}_{norm} = \mathcal{H} / \ln(|\mathcal{A}|) \in [0, 1]$. The admission threshold decays dynamically with user-configured duration ($t$ episodes) via `DynamicEntropyCalculator`:

$$E(t) = E_{ideal} + (E_{max} - E_{ideal}) \cdot e^{-k \cdot t}$$

Where $E_{ideal} = 0.10$, $k = 0.05$ for the Child $\to$ Teen transition, and $k = 0.15$ for the Teen $\to$ Adult transition. The nominal asymptotic progression targets are:

1. **CHILD Stage (Shadow Mode):** $\mathcal{H} > E_{child}(t)$ (nominal asymptotic target $\mathcal{H} > 0.40$). Actions run strictly in shadow mode (passive telemetry only); legacy baseline controller operates hardware signal plans. Because $E(t) < \ln(3)$ for all $t \ge 1$, a random policy ($\mathcal{H} = \ln 3$) is strictly prohibited from graduating. Inviolable minimum duration: 1 full week ($E_{\text{week}}$ episodes computed by [`EpisodeStepCalculator`](../src/utils/episode_step_calculator.py)) to cover all 168 real calendar hourly slots.
2. **TEEN Stage (Restricted Autonomy):** $E_{adult}(t) < \mathcal{H} \le E_{child}(t)$ (nominal range $0.15 < \mathcal{H} \le 0.40$). Agent operates physical hardware exclusively during off-peak hours (defined by Synapse dynamic schedule or classical urban defaults); during peak traffic periods, agent reverts to shadow mode for public safety. Inviolable minimum duration: 1 full week ($E_{\text{week}}$ episodes).
3. **ADULT Stage (Full Autonomy):** $\mathcal{H} \le E_{adult}(t)$ (nominal asymptotic target $\mathcal{H} \le 0.15$, reached at $t \ge 20$ episodes with $k=0.15$) and Mean Reward $\mu_{reward} > \mu_{baseline} + \delta^*$. Full 24/7 autonomous actuation granted across all traffic conditions.

### 5.1.1 Topological Episode Step Scaling and Weekly Pacing
To eliminate magic numbers and align each episode's temporal horizon with the physical scale of the urban road network, CARINA employs the [`EpisodeStepCalculator`](../src/utils/episode_step_calculator.py):
- **Topological Complexity ($C_{\text{topo}}$):** Ratio of real physical links $E_{\text{real}}$ (unifying opposing two-way corridors and stripping internal intersection connectors prefixed with `:`) to traffic light count $N$, weighted by average lane capacity $\bar{F}$:
  $$C_{\text{topo}} = \text{clamp}\left( \frac{E_{\text{real}}}{N} \times \left(1.0 + 0.1 \times (\bar{F} - 1.0)\right), \quad 0.8, \quad 1.6 \right)$$
- **Sub-linear Physical Relaxation:** Scales sub-linearly with critical corridor depth ($\sqrt{N}$) and network geographic diameter ($D_{\text{km}}$), preventing duration explosion in metropolises:
  $$T_{\text{physical}} = 180 + \left( 60 \cdot \sqrt{N} + 30 \cdot D_{\text{km}} \right) \times C_{\text{topo}}$$
- **Steps per Episode ($S$):** Converted using pessimistic HFT telemetry interval $\Delta t = 250\text{ ms}$ ($4\text{ steps/second}$), rounded up to base-10 multiples of 100, and clamped between 2.5 minutes ($600\text{ steps}$) and 1 hour ($14,400\text{ steps}$):
  $$S = \text{clamp}\left( \left\lceil \frac{T_{\text{physical}} / 0.25}{100} \right\rceil \times 100, \quad 600, \quad 14400 \right)$$
- **Inviolable 1-Week Safety Floor ($E_{\text{week}}$):** Calculates minimum episodes required to span exactly 7 full days ($604,800\text{ seconds}$):
  $$E_{\text{week}} = \left\lceil \frac{604800}{S \times 0.25} \right\rceil$$

### 5.1.2 Weekly Calendar Coverage Tracking & Pause/Resume Tolerance
To verify that policy evaluation captures the complete spectrum of urban traffic dynamics (weekdays, rush hours, night hours, and weekends) before promotion, the [`WeeklyCoverageTracker`](../src/core/weekly_coverage_tracker.py) operates alongside [`ActionAuthorizer`](../src/core/action_authorizer.py):
- **168 Calendar Slots Matrix:** Tracks all 168 hours of the calendar week ($7\text{ days} \times 24\text{ hours}$). Telemetry frames with real timestamps (`datetime.fromtimestamp(raw_timestamp)`) tick their corresponding `(weekday, hour)` slot.
- **Atomic Persistence:** The coverage matrix state is persisted atomically to disk (`weekly_coverage_CHILD.json` and `weekly_coverage_TEEN.json`), tolerating process pauses, server restarts, and maintenance cycles without resetting maturation progress.
- **Peak Gating (Synapse & Classical Fallback):** TEEN actuation is restricted to off-peak periods. If Synapse telemetry does not provide `peak_schedule.json`, CARINA enforces classical urban peak windows:
  - *Monday to Friday:* Morning peak (**06:30 to 09:00**) and Evening peak (**17:00 to 19:30**) in shadow mode.
  - *Weekends:* Off-peak (active autonomous control allowed).
- **Holistic Macro Evaluation:** Promotion evaluates the aggregate weekly performance ($\mu_{\text{week}} \ge \mu_{\text{baseline}} + \delta^*$), ensuring that isolated weather disruptions or localized holiday anomalies do not disqualify a safe, competent policy.

### 5.1.3 Inviolable Safety Invariants
To safeguard critical traffic infrastructure against operator misconfiguration, maturation rules enforce inviolable mathematical invariants:
- **Inviolable Time Floor:** Operators may configure longer training observation, but can never reduce duration below the 1-week safety floor:
  $$t_{\min} = \max(E_{\text{week}}, \text{user\_config})$$
- **Certainty Ceiling (Entropy Floor):** Operators may enforce stricter certainty (lower entropy), but can never loosen the threshold to accept chaotic policies:
  $$\text{threshold} = \min(E_{\text{calculated}}(t), E_{\text{manual\_config}})$$

### 5.2 Intra-Phase Population-Based Training (PBT)
To ensure biological and developmental integrity across agent cohorts, evolutionary exploitation and exploration in [`PopulationManager`](../src/core/population_manager.py) operate under strict intra-phase isolation:
- **Cohort Grouping:** Agents compete, clone weights, and mutate hyperparameters strictly within their lifecycle stage ($\text{TEEN} \leftrightarrow \text{TEEN}$, $\text{ADULT} \leftrightarrow \text{ADULT}$).
- **Childhood Shielding:** Agents in the `CHILD` stage are exempt from evolutionary mutations. Their neural weights remain unperturbed while observing physical network dynamics.
- **Topological Heterogeneity Safety:** Weight transfer across dissimilar junction topologies is safeguarded against tensor shape mismatches via runtime dimension validation.

### 5.3 Dynamic Graduation Performance Margin ($\delta^*$)
Rather than arbitrary static thresholds, the graduation margin required for an agent to advance from `TEEN` to `ADULT` is calculated continuously from empirical road traffic fluid dynamics:

$$\delta^* = K \times \left(1 - \frac{\bar{v}_{\text{child}}}{v_{\text{limit}}}\right) \times (1 - \text{occupancy}_{\text{child}}) \times 100\%$$

Where:
- $\left(1 - \frac{\bar{v}_{\text{child}}}{v_{\text{limit}}}\right)$ quantifies the operational inefficiency of legacy signal plans observed during childhood.
- $(1 - \text{occupancy}_{\text{child}})$ represents available physical road space headroom.
- $K = 0.25$ aligns target expectations with empirical benchmarks from real-world adaptive systems (SCATS / SCOOT: $10\%\text{--}15\%$).
- $\delta^*$ is securely clamped to $[3.0\%, 25.0\%]$ to prevent unreachable promotion goals in saturated networks or premature promotion in unconstrained corridors.

### 5.4 Physical Reward Function Balancing (HCM Traffic Physics)
CARINA balances the multi-objective reward function to prevent dimensional disparity between delay penalties and throughput bonuses:

$$R(t) = w_{\text{wait}} \times T_{\text{wait}}(t) + w_{\text{flow}} \times F_{\text{discharged}}(t)$$

By Highway Capacity Manual (HCM) formulations, discharging one vehicle saves the characteristic link travel time:

$$\tau = \frac{\bar{L}_{\text{links}}}{\bar{v}_{\text{limit}}}$$

The physical balancing algorithm in [`RewardWeightsCalculator`](../src/engine/reward_weights_calculator.py) establishes:
- $w_{\text{wait}} = -1.0$ (normalized delay penalty per second of queue).
- $w_{\text{flow}} = \text{clamp}(2.0, 25.0, \text{round}(\tau \times \alpha, 2))$, ensuring vehicle discharge incentives match the scale of accumulated queue delay.

---

<div align="center">
  <img src="assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
