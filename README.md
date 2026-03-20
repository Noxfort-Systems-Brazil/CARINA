<div align="center">
  <h1>🚦 CARINA</h1>
  <h3>Controlled Artificial Road-traffic Intelligence Network Architecture</h3>
  <p><i>A next-generation, Open-Source Artificial Intelligence Ecosystem for Adaptive Urban Traffic Control</i></p>
</div>

---

## 🌎 Executive Summary

**CARINA** is not just an algorithm; it is a comprehensively distributed, state-of-the-art AI ecosystem designed to serve as the "digital brain" for smart city traffic networks. Conceived as a digital public good, CARINA bridges the gap between bleeding-edge **Deep Reinforcement Learning (DRL)** research and robust **Urban Traffic Engineering**.

By replacing archaic, hardcoded fixed-time controllers with dynamic, learning-capable neural networks, CARINA continuously adapts to real-world congestion patterns. Its primary objectives are to:
- **Maximize Vehicular Throughput:** Drastically reduce wait times at intersections.
- **Prevent Cascading Gridlocks:** Anticipate and neutralize traffic shockwaves before they paralyze city grids.
- **Guarantee Safety:** Employ neuro-symbolic fail-safes to ensure no algorithm can ever trigger dangerous or contradictory traffic light phases.

---

## 🧠 The Neural Core: GOMES Architecture

At the epicenter of CARINA's decision-making is the **GOMES (Graph-based Operational Multi-agent Expert System)** Architecture. Unlike monolithic AI approaches, GOMES distributes traffic management across specialized, interacting neural entities:

### 1. Local Tactical Agent (PPO + TCN)
The brain governing each individual intersection. 
- **Algorithm:** **Proximal Policy Optimization (PPO)**.
- **Temporal Reasoning:** CARINA abandons traditional LSTMs in favor of **Temporal Convolutional Networks (TCN)**. TCNs offer vastly superior extraction of long-term temporal dependencies in traffic streams, processing historical queue lengths and velocity gradients with highly parallelizable 1D convolutions.
- **Evolution:** Agents periodically undergo **Population-Based Training (PBT)**, cross-pollinating hyperparameter mutations (Learning Rates, Entropy Coefficients) to discover globally optimal configurations dynamically.

### 2. Strategic Coordinator (GAT Base)
A localized traffic light cannot solve a city-wide jam. 
- **Algorithm:** **Graph Attention Networks (GAT)**.
- **Function:** The Strategist constructs a mathematical Graph where nodes are intersections and edges are connecting streets. It calculates Attention Vectors, allowing a Local Agent to "look ahead" and understand the downstream congestion state of its neighbors, facilitating green-wave formations across long avenues.

### 3. Guardian Agent (Dueling DQN)
Safety is paramount. AI hallucinations in traffic control are fatal.
- **Algorithm:** **Dueling Deep Q-Networks (DQN)** combined with hardcoded fixed-time tables.
- **Function:** The Guardian acts as a neuro-symbolic *Safety Auditor*. Operating asynchronously, it intercepts every action predicted by the Local Tactical Agent. If the Guardian's Q-values detect an imminent risk (e.g., green-light conflicts or catastrophic gridlock), it triggers a deterministic Veto, overriding the AI with a safe, pre-calculated fixed-time sequence derived from its internal tables.

---

## 🎓 Training & Maturation: The DA SILVA Pipeline

Deploying an untrained neural network into a live city grid is irresponsible. CARINA utilizes the **DA SILVA (Dynamic Agent Safety Integrated Learning for Validated Autonomy)** curriculum. Agents must prove their competence through biological-like maturity stages:

1. **CHILD (Shadow Mode):** The agent is connected to the live grid but only observes. It predicts actions and calculates losses against the existing fixed-time system without actually controlling the lights.
2. **TEEN (Restricted Autonomy):** The agent is granted control of the intersection exclusively during low-risk, off-peak hours (e.g., 2:00 AM) with aggressive Guardian safety margins.
3. **ADULT (Full Autonomy):** Upon continuously exceeding a predefined Reward Threshold and demonstrating stabilized Policy Entropy, the agent "graduates" and assumes full 24/7 autonomous control.

---

## 🔬 Explainable AI (XAI) & LLM Transducers

Deep Neural Networks are often heavily criticized as uninterpretable "black boxes" by urban engineers. CARINA solves this by integrating a native **Explainable AI (XAI) Pipeline**:

- **Captum Mathematical Attributions:** Working directly on the PyTorch Tensors, Captum mathematically dissects the TCN weights during runtime mapping exactly which input (e.g., *Northbound Lane Occupancy at t-5s*) triggered the neural network to switch the light to Green.
- **Semantic Transducer (LLM Backend):** A raw matrix of integrated gradients means nothing to a city mayor. The Transducer passes these numerical arrays through a Large Language Model prompt, generating a human-readable, technically accurate "Laudo Técnico" (Technical Report) explaining the AI's logic in plain English/Portuguese.

---

## ⚙️ Software Architecture & Enterprise Tech Stack

CARINA is engineered for extreme resilience, deterministic behavior, and massive scalability using strictly enforced **SOLID** object-oriented design principles.

*   **Asynchronous Microservices:** Deep RL Trajectory loops (`EpisodeRunner`), SQL database commits (`DatabaseWorker`), and Explainable AI generation (`XAIOrchestrator`) are rigorously isolated into standalone OS multiprocessing pools linked by thread-safe IPC Queues.
*   **Infrastructure Analysis Service (SAS):** CARINA isn't just a driver; it's a consultant. By accumulating weeks of live telemetry, the native SAS Engine evaluates intersections against global Traffic Engineering Warrants, autonomously recommending the deployment or removal of physical traffic lights.
*   **Polymorphic Data Persistence:** The SQL layer dynamically mounts connection pools. It defaults to embedded **SQLite3** for rapid prototyping, but instantly scales to **psycopg2 PostgreSQL** ecosystems for distributed, multi-instance Machine Learning workloads via `settings.ini`.
*   **PyTorch TensorBoard native integration:** Reinforcement learning curves (Cumulative Rewards, Policy Entropy, surrogate losses) are streamed natively to PyTorch's `SummaryWriter` for highly granular, real-time introspection via the web dashboard.
*   **Noxfort Monitor Telemetry (MQTT v2):** Cloud-native integration that fires sub-second UDP heartbeats and critical Incident Reports (e.g., Watchdog failsafes, Guardian Vetos) to external IoT monitoring matrices.
*   **Flet (Flutter) Reactive UI:** A stunning, asynchronous graphical desktop interface featuring high-framerate map topologies, heatmap visualizations (Max/Avg lane aggregation), and live terminal diagnostics without writing a single line of web code.

---

## 🚀 Getting Started

CARINA functions as a passive network node. It connects to **Eclipse SUMO** for simulation or directly to physical controllers via the agnostic **Synapse HFT Protocol**.

### Installation (Linux/Debian)

```bash
# Clone the repository
git clone https://github.com/noxfort/CARINA.git
cd CARINA

# Create and activate Python Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# Install Core dependencies + TensorBoard & PostgreSQL bindings
pip install -r requirements.txt
pip install psycopg2-binary tensorboard

# Launch the Application
python3 carina.py
```

### Accessing TensorBoard
Once the AI training episode steps begin to roll, you can view the neural introspection matrices:
```bash
tensorboard --logdir=results/tensorboard
```
Open your browser at `http://localhost:6006`.

---

<div align="center">
  <b>Developed with ❤️ for the future of urban mobility.</b><br>
  <i>Copyright (C) 2026 Gabriel Moraes - Noxfort Systems | GNU Affero General Public License v3</i>
</div>
