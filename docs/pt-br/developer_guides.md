---
tags: [desenvolvedor, guia, configuracao, agentes, 12-factor]
aliases: [Guias de Desenvolvimento, Referência de Configuração, Arquitetura de Agentes]
---

# 🛠️ Guias de Desenvolvimento e Extensão do CARINA

Este documento fornece guias passo a passo para desenvolvedores sobre como configurar o ambiente de desenvolvimento, gerenciar parâmetros, implementar novos agentes de Aprendizado por Reforço Profundo e estender a base de código do CARINA.

⬅️ [Central de Documentação](README.md) | 🧪 [Testes e Validação](testing.md) | 🚀 [Implantação e Empacotamento](deployment_and_packaging.md) | 🗄️ [Banco de Dados e Schemas](database_and_schemas.md)

---

## 1. Configuração de Ambiente e Parâmetros

O CARINA segue a metodologia **12-Factor App**. Credenciais, segredos e atributos de infraestrutura são estritamente isolados dos hiperparâmetros operacionais:

### 1.1 Infraestrutura e Credenciais: `.env`
Copie o arquivo de exemplo para `.env`:
```bash
cp .env.example .env
```
Configure suas variáveis locais:
```bash
CARINA_ENV=development                   # 'development' ou 'production'
CARINA_DB_USER=admin
CARINA_DB_PASSWORD=admin
CARINA_DB_HOST=localhost
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_SNMP_COMMUNITY=public

# Telemetria do Monitor Externo (Broker MQTT ou URL HTTP/Cloud/Ngrok)
CARINA_MQTT_HOST=127.0.0.1
CARINA_MQTT_PORT=1883
CARINA_MQTT_USER=
CARINA_MQTT_PASSWORD=
```

### 1.2 Parâmetros Operacionais: `config/settings.ini`
Hiperparâmetros, intervalos de treinamento e tolerâncias do Watchdog residem em `config/settings.ini`:

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

### 1.3 Interagindo com Configurações (`src/settings/`)
O CARINA disponibiliza um subsistema modular e baseado em princípios SOLID em `src/settings/`.

Desenvolvedores podem acessar configurações pelo `SettingsService` modular ou através da fachada retrocompatível `SettingsManager`:

```python
# Abordagem modular direta:
from settings import SettingsService, IniFileStorage, DotenvSecretProvider
service = SettingsService(
    storage=IniFileStorage("config/settings.ini"),
    env_provider=DotenvSecretProvider()
)
value = service.get("ai_gamma", default=0.99)

# Ou via fachada retrocompatível (utilizada pelo código existente):
from utils.settings_manager import SettingsManager
settings_dict = SettingsManager().load_settings()
learning_rate = float(settings_dict.get("learning_rate", 0.00025))
```

Todas as chaves são validadas contra `SettingsSchema` (`src/settings/schema.py`), garantindo mapeamento tipado seguro para as seções INI e contingência com o `.env`.

---

## 2. Hierarquia de Agentes e Extensão de RL

A arquitetura neural do CARINA particiona a tomada de decisão em quatro papéis especializados em `src/agents/`:

1. **`LocalAgent` (`src/agents/local_agent.py`):** Agente tático PPO-TCN controlando durações de estágio da interseção local em tempo real ($< 0,5\text{ ms}$).
2. **`GuardianAgent` (`src/agents/guardian_agent.py`):** Sentinela neuro-simbólica D3QN que audita e veta ações que violem regras de trânsito ou causem transbordamento (*spillback*).
3. **`ConsultantAgent` (`src/agents/consultant_agent.py`):** Autoencoder Preditivo (PAE de 128 canais) que projeta tendências futuras da malha urbana.
4. **`StrategistAgent` (`src/agents/strategist_agent.py`):** Coordenador de grafo arterial ST-GATv2 Lite para sincronização de ondas verdes.

### 2.1 Implementando um Agente Customizado
Para criar um novo agente tático (ex: `CustomPPOAgent`):

1. Crie o arquivo `src/agents/custom_ppo_agent.py`:
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
        """Seleciona a ação discreta de fase semafórica."""
        with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu"):
            # Computa logits de ação
            action_index = 0
            return action_index

    def update(self, memory_buffer) -> dict:
        """Executa a otimização por retropropagação (backpropagation)."""
        return {"loss": 0.0}
```

2. Registre seu agente em `src/core/decision_coordinator.py`:
```python
from agents.custom_ppo_agent import CustomPPOAgent

# Dentro da inicialização do DecisionCoordinator:
if agent_type == "CUSTOM_PPO":
    self.agent = CustomPPOAgent(state_dim, action_dim, config)
```

---

## 3. Empacotamento e Distribuição

Os scripts legados de PyInstaller e empacotamento `.deb` via `build_installer.sh` foram depreciados e removidos da base de código para dar lugar a pipelines de containerização modernos e auditáveis.

Para instruções completas de execução e implantação, consulte [Implantação e Empacotamento](deployment_and_packaging.md).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Software e Integração • CARINA CORE v1.2.0</i>
</div>
