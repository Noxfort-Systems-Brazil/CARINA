---
tags: [developer, guide, setup, agents, config, 12-factor]
aliases: [Developer Guides, Configuration Reference, Agent Architecture]
---

# 🛠️ Developer & Integration Guides

This document provides step-by-step developer guides for setting up the environment, configuring settings, creating custom reinforcement learning agents, and understanding the CARINA codebase.

⬅️ Back to [Main Documentation Hub](carina_moc.md) | 🧪 See [Testing & Validation](testing.md) | 🚀 See [Deployment & Packaging](deployment_and_packaging.md) | 🗄️ See [Database & Schemas](database_and_schemas.md) | 🚑 See [EVP Preemption](evp_and_preemption.md)

---

## 1. Environment & Configuration Setup

CARINA follows the **12-Factor App** configuration methodology. Secrets and environmental attributes are separated from operational hyperparameters:

### 1.1 Secrets & Infrastructure: `.env`
Copy the example file to `.env`:
```bash
cp .env.example .env
```
Configure your credentials:
```bash
CARINA_ENV=development                   # 'development' or 'production'
CARINA_DB_TYPE=sqlite                    # 'sqlite' or 'postgresql'
CARINA_DB_USER=admin
CARINA_DB_PASSWORD=admin
CARINA_DB_HOST=localhost
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_SNMP_COMMUNITY=public

# Hardware & Web Gateway (Go Subprocess)
CARINA_GATEWAY_ENABLED=true
CARINA_GATEWAY_PORT=2201
CARINA_TAILSCALE_AUTH_KEY=               # Optional: tskey-auth-xxx for automated Funnel setup

# External Monitor Telemetry (Broker MQTT or URL HTTP/Cloud/Ngrok)
CARINA_MQTT_HOST=127.0.0.1
CARINA_MQTT_PORT=1883
CARINA_MQTT_USER=
CARINA_MQTT_PASSWORD=
```

### 1.2 Operational Parameters: `config/settings.ini`
Hyperparameters, training intervals, and watchdog tolerances reside in [`config/settings.ini`](../../config/settings.ini):

```ini
[AI_TRAINING]
episode_max_steps = 100
update_timestep = 1024
gamma = 0.99
sequence_length = 4
k_epochs = 4
eps_clip = 0.2
gae_lambda = 0.95

[PBT]
evolution_frequency_episodes = 10
exploitation_percentile = 25
learning_rate_range = 0.00001, 0.0005

[MATURITY]
auto_pacing_enabled = True
auto_performance_margin_enabled = True
child_phase_episodes = 1
teen_phase_min_episodes = 1
performance_margin = -100.0

[REWARD_WEIGHTS]
auto_reward_weights_enabled = True
weight_waiting_time = -2.0
weight_flow = 2.0

[YELLOW_SCHEDULE]
yellow_schedule_enabled = False
yellow_schedule_start = 23:00
yellow_schedule_end = 05:00
yellow_schedule_all_semaphores = False

[WATCHDOG]
initial_grace_period_seconds = 10
heartbeat_timeout_seconds = 5.0

[GUARDIAN_AGENT]
learning_rate = 0.00025
gamma = 0.90
epsilon_start = 1.0
epsilon_end = 0.05
batch_size = 128

[HEATMAP_SCALING]
weight_occupancy = 1.0
weight_waiting_time = 1.5
weight_flow = 1.0
saturation_threshold = 0.85
lane_aggregation_strategy = max
heatmap_strategy = combined
heatmap_saturation = 1.0

[REMOTE_GATEWAY]
gateway_enabled = true
cco_subdomain = cco
evp_subdomain = evp
evp_auth_token =
cco_port = 2201
evp_port = 8085

[EVP]
preemption_enabled = True
entry_distance_meters = 160.0
exit_distance_meters = 15.0
dwell_watchdog_seconds = 45.0
enforce_clearance = True
```

### 1.3 Interacting with Programmatic Calculators
For autonomous network calibration, CARINA exposes standalone calculators in `src/promotion/` and `src/engine/`:

```python
# 1. Dynamic Maturity Pacing (episode durations from topology):
from promotion.maturity_pacing_calculator import MaturityPacingCalculator
MaturityPacingCalculator.apply_if_enabled(maturity_manager, net, tls_list, settings)

# 2. Dynamic Performance Graduation Margin (fluid dynamics & speed limits):
from promotion.performance_margin_calculator import PerformanceMarginCalculator
margin = PerformanceMarginCalculator.calculate_from_topology(net, settings)
PerformanceMarginCalculator.apply_if_enabled(maturity_manager, margin, settings)

# 3. Dynamic Reward Weights Balancing (HCM link traversal time):
from engine.reward_weights_calculator import RewardWeightsCalculator
weights = RewardWeightsCalculator.calculate_from_topology(net, settings)
RewardWeightsCalculator.apply_if_enabled(reward_calculator, weights, settings)
```

### 1.4 Interacting with Settings (`src/settings/`)
CARINA provides a clean SOLID configuration subsystem in [`src/settings/`](../../src/settings).

Developers can access settings through the modular `SettingsService` or via the legacy `SettingsManager` facade:

```python
# Direct modular approach:
from settings import SettingsService, IniFileStorage, DotenvSecretProvider
service = SettingsService(
    storage=IniFileStorage("config/settings.ini"),
    env_provider=DotenvSecretProvider()
)
value = service.get("ai_gamma", default=0.99)

# Or via backwards-compatible facade (recommended across existing code):
from utils.settings_manager import SettingsManager
settings_dict = SettingsManager().load_settings()
learning_rate = float(settings_dict.get("learning_rate", 0.00025))
```

All keys are validated against [`SettingsSchema`](../../src/settings/schema.py), guaranteeing automatic mapping to the correct INI section and `.env` fallback.

---

## 2. Agent Hierarchy & Extending Reinforcement Learning

CARINA's neural architecture divides decision-making into three specialized roles located in [`src/agents/`](../../src/agents):

1. **`LocalAgent` ([`local_agent.py`](../../src/agents/local_agent.py)):** Tactical PPO-TCN agent controlling local intersection phase durations.
2. **`GuardianAgent` ([`guardian_agent.py`](../../src/agents/guardian_agent.py)):** Neuro-symbolic D3QN safety sentinel that audits and vetoes unsafe actions.
3. **`StrategistAgent` ([`strategist_agent.py`](../../src/agents/strategist_agent.py)):** ST-GATv2 Lite arterial graph coordinator providing spatiotemporal traffic embeddings and emergent green waves.

### 2.1 Implementing a Custom Agent
To create a new tactical agent (e.g., `CustomPPOAgent`):

1. Create `src/agents/custom_ppo_agent.py`:
```python
import torch
import torch.nn as nn

class CustomPPOAgent:
    def __init__(self, state_dim: int, action_dim: int, config: dict):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def act(self, observation_tensor: torch.Tensor, explore: bool = True) -> int:
        """Selects discrete traffic signal phase action."""
        with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu"):
            # Compute action logits
            action_index = 0
            return action_index

    def update(self, memory_buffer) -> dict:
        """Executes backpropagation optimization."""
        return {"loss": 0.0}
```

2. Register your agent in [`src/core/decision_coordinator.py`](../../src/core/decision_coordinator.py):
```python
from agents.custom_ppo_agent import CustomPPOAgent

# Inside DecisionCoordinator initialization:
if agent_type == "CUSTOM_PPO":
    self.agent = CustomPPOAgent(state_dim, action_dim, config)
```

---

## 3. Packaging & Distribution

CARINA provides a multi-stage Docker builder script ([`scripts/build_deb.sh`](../../scripts/build_deb.sh)) that compiles the React CCO frontend, compiles the Go gateway binary, prepares an isolated Python virtualenv, and packages everything into a self-contained Debian package (`dist/carina_1.0.0_amd64.deb`).

To build the package locally:
```bash
./scripts/build_deb.sh
```

For full installation and deployment instructions, see [Deployment & Packaging](deployment_and_packaging.md).

---

## 4. Simulating Emergency Vehicles & Preemption Corridors

Developers can test and validate emergency vehicle preemption without physical transponders or live ambulances using the integrated CLI simulator ([`demo/evp_vehicle_simulator.py`](../../demo/evp_vehicle_simulator.py)):

### 4.1 Running the Simulation Modes
```bash
# 1. Single Emergency Runway (SAMU ambulance racing towards intersection with siren active):
python demo/evp_vehicle_simulator.py --mode emergency --vehicle SAMU-01 --duration 25.0

# 2. Continuous Fleet Multi-Corporation Patrol (SAMU, Fire, Police orbiting with 2 Hz telemetry):
python demo/evp_vehicle_simulator.py --mode patrol --duration 60.0

# 3. Siren-Off Approach (Verifies preemption veto when vehicle approaches without active siren):
python demo/evp_vehicle_simulator.py --mode siren_off --vehicle BOMB-03
```

By default, the simulator transmits to `http://localhost:8085` (standalone receiver) or `http://localhost:2201` (Go Web Gateway). Specify target host and port via:
```bash
python demo/evp_vehicle_simulator.py --host 127.0.0.1 --port 2201 --mode emergency
```

### 4.2 Direct HTTP Injection via cURL
Developers can also trigger synthetic GPS telemetry pings directly:
```bash
curl -X POST http://localhost:2201/api/v1/evp/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "SAMU-01",
    "corporation": "SAMU",
    "latitude": -23.55052,
    "longitude": -46.63330,
    "speed_kmh": 65.0,
    "heading_deg": 90.0,
    "siren_active": true,
    "timestamp": 1789458600.0
  }'
```
Expected response is `HTTP 204 No Content` ($< 1\text{ ms}$). Observe the preemption logs in CARINA console:
```text
[EVPKinematicsEngine] Vehicle SAMU-01 entered approach gate (112.4m to J01)
[EVPPreemptionEngine] Granting emergency preemption hold on Stage 1 for SAMU-01
[GoGatewayClient] Sent NDJSON command: {"cmd":"evp_preempt","intersection_id":"J01",...}
```

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
