---
tags: [developer, guide, setup, agents, config, 12-factor]
aliases: [Developer Guides, Configuration Reference, Agent Architecture]
---

# 🛠️ Developer & Integration Guides

This document provides step-by-step developer guides for setting up the environment, configuring settings, creating custom reinforcement learning agents, and understanding the CARINA codebase.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🧪 See [Testing & Validation](TESTING.md) | 🚀 See [Deployment & Packaging](DEPLOYMENT_AND_PACKAGING.md) | 🗄️ See [Database & Schemas](DATABASE_AND_SCHEMAS.md)

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
CARINA_DB_USER=admin
CARINA_DB_PASSWORD=admin
CARINA_DB_HOST=localhost
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_SNMP_COMMUNITY=public
```

### 1.2 Operational Parameters: `config/settings.ini`
Hyperparameters, training intervals, and watchdog tolerances reside in [`config/settings.ini`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/config/settings.ini):

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
```

---

## 2. Agent Hierarchy & Extending Reinforcement Learning

CARINA's neural architecture divides decision-making into four specialized roles located in [`src/agents/`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/agents):

1. **`LocalAgent` ([`local_agent.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/agents/local_agent.py)):** Tactical PPO-TCN agent controlling local intersection phase durations.
2. **`GuardianAgent` ([`guardian_agent.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/agents/guardian_agent.py)):** Neuro-symbolic D3QN safety sentinel that audits and vetoes unsafe actions.
3. **`ConsultantAgent` ([`consultant_agent.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/agents/consultant_agent.py)):** High-capacity Predictive Autoencoder (PAE) projecting future traffic trends.
4. **`StrategistAgent` ([`strategist_agent.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/agents/strategist_agent.py)):** ST-GATv2 Lite arterial graph coordinator.

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

2. Register your agent in [`src/core/decision_coordinator.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/core/decision_coordinator.py):
```python
from agents.custom_ppo_agent import CustomPPOAgent

# Inside DecisionCoordinator initialization:
if agent_type == "CUSTOM_PPO":
    self.agent = CustomPPOAgent(state_dim, action_dim, config)
```

---

## 3. Packaging & Distribution (`build_installer.sh`)

CARINA uses Docker as an isolated, sterile build environment to compile standalone `.deb` installers for Ubuntu/Debian Linux:

```bash
chmod +x build_installer.sh
./build_installer.sh
```

The script packages PyInstaller binaries, systemd service units, configuration templates, and desktop icons into `./dist/carina_1.0.0_amd64.deb`.

For detailed containerization and deployment instructions, see [Deployment & Packaging](DEPLOYMENT_AND_PACKAGING.md).
