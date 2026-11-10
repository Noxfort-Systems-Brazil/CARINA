---
tags: [desenvolvedor, guia, configuracao, agentes, config, 12-factor]
aliases: [Guias do Desenvolvedor, Referência de Configurações, Arquitetura de Agentes]
---

# 🛠️ Guias do Desenvolvedor & Integração

Este documento fornece guias passo a passo para configuração do ambiente de desenvolvimento, parametrização do sistema, criação de agentes de aprendizado por reforço personalizados e boas práticas na base de código do CARINA.

⬅️ [Central de Documentação](carina_moc.md) | 🧪 [Testes e Validação](testing.md) | 🚀 [Implantação & Empacotamento](deployment_and_packaging.md) | 🗄️ [Banco de Dados & Esquemas](database_and_schemas.md) | 🚑 [Preempção de Emergência (EVP)](evp_and_preemption.md)

---

## 1. Configuração do Ambiente e Parâmetros

O CARINA segue a metodologia de configuração **12-Factor App**. Segredos e atributos de infraestrutura são mantidos isolados dos hiperparâmetros operacionais do sistema:

### 1.1 Segredos & Infraestrutura: `.env`
Copie o arquivo de exemplo para `.env`:
```bash
cp .env.example .env
```
Configure suas credenciais locais:
```bash
CARINA_ENV=development                   # 'development' ou 'production'
CARINA_DB_TYPE=sqlite                    # 'sqlite' ou 'postgresql'
CARINA_DB_USER=admin
CARINA_DB_PASSWORD=admin
CARINA_DB_HOST=localhost
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_SNMP_COMMUNITY=public

# Gateway Go de Hardware e Web (Subprocesso)
CARINA_GATEWAY_ENABLED=true
CARINA_GATEWAY_PORT=2201
CARINA_TAILSCALE_AUTH_KEY=               # Opcional: tskey-auth-xxx para ativação automática do Funnel

# Telemetria de Monitoramento Externo (Broker MQTT ou URL HTTP/Cloud/Ngrok)
CARINA_MQTT_HOST=127.0.0.1
CARINA_MQTT_PORT=1883
CARINA_MQTT_USER=
CARINA_MQTT_PASSWORD=
```

### 1.2 Parâmetros Operacionais: `config/settings.ini`
Hiperparâmetros neurais, intervalos de treinamento e tolerâncias do watchdog residem em [`config/settings.ini`](../../config/settings.ini):

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

### 1.3 Interagindo com os Calculadores Programáticos
Para calibração autônoma da rede viária, o CARINA expõe calculadores modulares em `src/promotion/` e `src/engine/`:

```python
# 1. Ritmo Dinâmico de Maturidade (duração das fases baseada na malha):
from promotion.maturity_pacing_calculator import MaturityPacingCalculator
MaturityPacingCalculator.apply_if_enabled(maturity_manager, net, tls_list, settings)

# 2. Margem Dinâmica de Graduação de Desempenho (fluidodinâmica e limites de velocidade):
from promotion.performance_margin_calculator import PerformanceMarginCalculator
margin = PerformanceMarginCalculator.calculate_from_topology(net, settings)
PerformanceMarginCalculator.apply_if_enabled(maturity_manager, margin, settings)

# 3. Balanceamento Dinâmico de Pesos de Recompensa (tempo livre de travessia HCM):
from engine.reward_weights_calculator import RewardWeightsCalculator
weights = RewardWeightsCalculator.calculate_from_topology(net, settings)
RewardWeightsCalculator.apply_if_enabled(reward_calculator, weights, settings)
```

### 1.4 Interagindo com as Configurações (`src/settings/`)
O CARINA implementa um subsistema modular alinhado aos princípios SOLID em [`src/settings/`](../../src/settings).

Os desenvolvedores podem acessar as configurações através do `SettingsService` desacoplado ou pela fachada retrocompatível `SettingsManager`:

```python
# Abordagem modular direta:
from settings import SettingsService, IniFileStorage, DotenvSecretProvider
service = SettingsService(
    storage=IniFileStorage("config/settings.ini"),
    env_provider=DotenvSecretProvider()
)
value = service.get("ai_gamma", default=0.99)

# Ou via fachada compatível (recomendado no código existente):
from utils.settings_manager import SettingsManager
settings_dict = SettingsManager().load_settings()
learning_rate = float(settings_dict.get("learning_rate", 0.00025))
```

Todas as chaves são validadas contra [`SettingsSchema`](../../src/settings/schema.py), garantindo mapeamento transparente para a seção correta do arquivo INI e resolução automática com fallback no `.env`.

---

## 2. Hierarquia de Agentes & Extensão de Aprendizado por Reforço

A arquitetura neural do CARINA divide a tomada de decisão em três papéis especializados localizados em [`src/agents/`](../../src/agents):

1. **`LocalAgent` ([`local_agent.py`](../../src/agents/local_agent.py)):** Agente tático PPO-TCN controlando a duração e seleção das fases semafóricas locais.
2. **`GuardianAgent` ([`guardian_agent.py`](../../src/agents/guardian_agent.py)):** Sentinela neuro-simbólica D3QN que audita e veta ações inseguras que possam gerar engarrafamentos de travamento (spillback).
3. **`StrategistAgent` ([`strategist_agent.py`](../../src/agents/strategist_agent.py)):** Coordenador arterial ST-GATv2 Lite que computa embeddings espaço-temporais e viabiliza ondas verdes arteriais emergentes.

### 2.1 Implementando um Agente Personalizado
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
            # Computa logits da ação
            action_index = 0
            return action_index

    def update(self, memory_buffer) -> dict:
        """Executa a otimização por retropropagação (backpropagation)."""
        return {"loss": 0.0}
```

2. Registre o seu agente em [`src/core/decision_coordinator.py`](../../src/core/decision_coordinator.py):
```python
from agents.custom_ppo_agent import CustomPPOAgent

# Dentro da inicialização do DecisionCoordinator:
if agent_type == "CUSTOM_PPO":
    self.agent = CustomPPOAgent(state_dim, action_dim, config)
```

---

## 3. Empacotamento e Distribuição

O CARINA disponibiliza um script hermético de compilação multi-estágio via Docker ([`scripts/build_deb.sh`](../../scripts/build_deb.sh)) que compila o frontend web CCO (React), o gateway Go nativo, prepara o virtualenv Python isolado e empacota a aplicação em um pacote Debian (`dist/carina_1.0.0_amd64.deb`).

Para gerar o pacote localmente:
```bash
./scripts/build_deb.sh
```

Para instruções completas de implantação e execução, consulte [Implantação & Empacotamento](deployment_and_packaging.md).

---

## 4. Simulando Veículos de Emergência & Corredores de Preempção

Os desenvolvedores podem testar e validar o subsistema de preempção de veículos de emergência sem necessitar de transponders físicos ou ambulâncias reais em trânsito através do simulador CLI integrado ([`demo/evp_vehicle_simulator.py`](../../demo/evp_vehicle_simulator.py)):

### 4.1 Modos de Execução da Simulação
```bash
# 1. Corrida de Emergência Única (ambulância do SAMU correndo até o cruzamento com sirene ativa):
python demo/evp_vehicle_simulator.py --mode emergency --vehicle SAMU-01 --duration 25.0

# 2. Patrulhamento Contínuo Multi-Corporações (SAMU, Bombeiros, Polícia em órbita com telemetria a 2 Hz):
python demo/evp_vehicle_simulator.py --mode patrol --duration 60.0

# 3. Aproximação com Sirene Desligada (Verifica o veto de preempção quando a viatura não aciona sirene):
python demo/evp_vehicle_simulator.py --mode siren_off --vehicle BOMB-03
```

Por padrão, o simulador transmite para `http://localhost:8085` (receptor autônomo) ou `http://localhost:2201` (Go Web Gateway). Especifique o host e a porta de destino através de:
```bash
python demo/evp_vehicle_simulator.py --host 127.0.0.1 --port 2201 --mode emergency
```

### 4.2 Injeção Direta de Telemetria HTTP via cURL
Também é possível acionar pings sintéticos de GPS diretamente via cURL:
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
A resposta esperada é `HTTP 204 No Content` ($< 1\text{ ms}$). Observe os logs de preempção no console do CARINA:
```text
[EVPKinematicsEngine] Vehicle SAMU-01 entered approach gate (112.4m to J01)
[EVPPreemptionEngine] Granting emergency preemption hold on Stage 1 for SAMU-01
[GoGatewayClient] Sent NDJSON command: {"cmd":"evp_preempt","intersection_id":"J01",...}
```

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Mobilidade Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
