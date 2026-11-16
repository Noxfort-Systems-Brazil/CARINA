---

tags: [desarrollador, guia, configuracion, agentes, ajustes, 12-factor]

aliases: [Guías para Desarrolladores, Referencia de Configuración, Arquitectura de Agentes]

---



# 🛠️ Guías para Desarrolladores e Integración



Este documento proporciona guías paso a paso para desarrolladores para la configuración del entorno, la gestión de ajustes, la creación de agentes personalizados de aprendizaje por refuerzo y la comprensión de la base de código de CARINA.



⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🧪 Ver [Pruebas y Validación](testing.md) | 🚀 Ver [Despliegue y Empaquetado](deployment_and_packaging.md) | 🗄️ Ver [Base de Datos y Esquemas](database_and_schemas.md) | 🚑 Ver [Preempción EVP](evp_and_preemption.md)



---



## 1. Configuración del Entorno y Parámetros



CARINA adopta la metodología de configuración de **Aplicaciones de 12 Factores**. Los secretos y variables de entorno se desacoplan estrictamente de los hiperparámetros operativos:



### 1.1 Secretos e Infraestructura: `.env`

Copie el archivo de ejemplo a `.env`:

```bash

cp .env.example .env

```

Configure sus credenciales:

```bash

CARINA_ENV=development                   # 'development' o 'production'

CARINA_DB_TYPE=sqlite                    # 'sqlite' o 'postgresql'

CARINA_DB_USER=admin

CARINA_DB_PASSWORD=admin

CARINA_DB_HOST=localhost

CARINA_DB_PORT=5432

CARINA_DB_NAME=carina_data

CARINA_DB_CONNECTED=False

CARINA_SNMP_COMMUNITY=public



# Hardware y Web Gateway (Propietario Único CentralController: CARINA_GATEWAY_ROLE=owner; UI/AI: remote)

# ¡Mantenga CARINA_GATEWAY_ENABLED=False en producción hasta configurar los tokens de autenticación siguientes!

CARINA_GATEWAY_ENABLED=False

CARINA_GATEWAY_PORT=2201

CARINA_TRAP_PORT=162

CARINA_EVP_AUTH_TOKEN=

CARINA_CCO_AUTH_TOKEN=

CARINA_CCO_ALLOWED_ORIGIN=

CARINA_GATEWAY_TLS_CERT=

CARINA_GATEWAY_TLS_KEY=

CARINA_GATEWAY_TLS_CA=

CARINA_GATEWAY_TLS_SERVER_NAME=

CARINA_TAILSCALE_AUTH_KEY=               # Opcional: tskey-auth-xxx para configuración Funnel automática



# Seguridad del Enlace Synapse HFT gRPC (:50051)

CARINA_GRPC_AUTH_TOKEN=

CARINA_GRPC_TLS_ENABLED=False

CARINA_GRPC_TLS_CERT=

CARINA_GRPC_TLS_KEY=

CARINA_GRPC_TLS_CA=

CARINA_GRPC_REQUIRE_CLIENT_CERT=False



# Sobrescrituras Opcionales de Directorios de Almacenamiento / Configuración

CARINA_OUTPUT_DIR=

CARINA_CONFIG_DIR=



# Telemetría de Monitoreo Externo (Broker MQTT o URL HTTP/Cloud/Ngrok)

CARINA_MONITOR_ENABLED=False

CARINA_MQTT_HOST=localhost

CARINA_MQTT_PORT=1883

CARINA_MQTT_USER=

CARINA_MQTT_PASSWORD=

```



### 1.2 Parámetros Operativos: `config/settings.ini`

Los hiperparámetros, intervalos de entrenamiento y tolerancias de watchdog residen en [`config/settings.ini`](../../config/settings.ini):



```ini

[AI_TRAINING]

episode_max_steps = 100

telemetry_delta_ms = 250

update_timestep = 1024

gamma = 0.99

sequence_length = 12

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

child_phase_episodes = 1344

teen_phase_min_episodes = 1344

performance_margin = 8.12



[REWARD_WEIGHTS]

auto_reward_weights_enabled = True

weight_waiting_time = -1.0

weight_flow = 6.04



[LOGGING]

log_step_progress = False

root_log_level = INFO

log_progress_frequency = 1

log_progress = True



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

weight_flow = -0.5

saturation_threshold = 100.0

lane_aggregation_strategy = max

heatmap_strategy = max

heatmap_saturation = 100.0



[REMOTE_GATEWAY]

gateway_enabled = False

cco_subdomain =

evp_subdomain =

evp_auth_token =

cco_auth_token =

cco_allowed_origin =

gateway_tls_cert =

gateway_tls_key =

cco_port = 8550

evp_port = 8085



[SYNAPSE]

port = 50051

max_workers = 10

grpc_auth_token =

grpc_tls_enabled = False

grpc_tls_cert =

grpc_tls_key =

grpc_tls_ca =

grpc_require_client_cert = False



[EVP]

auto_register_fleet = False

```



### 1.3 Interacción con Calculadoras Programáticas

Para la calibración autónoma de la red, CARINA expone calculadoras independientes en `src/promotion/` y `src/engine/`:



```python

# 1. Ritmo Dinámico de Madurez (duraciones de episodio según topología):

from promotion.maturity_pacing_calculator import MaturityPacingCalculator

MaturityPacingCalculator.apply_if_enabled(maturity_manager, net, tls_list, settings)



# 2. Margen Dinámico de Rendimiento para Graduación (dinámica de fluidos y límites de velocidad):

from promotion.performance_margin_calculator import PerformanceMarginCalculator

margin = PerformanceMarginCalculator.calculate_from_topology(net, settings)

PerformanceMarginCalculator.apply_if_enabled(maturity_manager, margin, settings)



# 3. Balance Dinámico de Pesos de Recompensa (tiempo de recorrido de tramo HCM):

from engine.reward_weights_calculator import RewardWeightsCalculator

weights = RewardWeightsCalculator.calculate_from_topology(net, settings)

RewardWeightsCalculator.apply_if_enabled(reward_calculator, weights, settings)

```



### 1.4 Interacción con Configuraciones (`src/settings/`)

CARINA proporciona un subsistema de configuración limpio basado en SOLID en [`src/settings/`](../../src/settings).



Los desarrolladores pueden acceder a las configuraciones a través del `SettingsService` modular o mediante la fachada heredada `SettingsManager`:



```python

# Enfoque modular directo:

from settings import SettingsService, IniFileStorage, DotenvSecretProvider

service = SettingsService(

    storage=IniFileStorage("config/settings.ini"),

    env_provider=DotenvSecretProvider()

)

value = service.get("ai_gamma", default=0.99)



# O a través de la fachada retrocompatible (recomendada en el código existente):

from utils.settings_manager import SettingsManager

settings_dict = SettingsManager().load_settings()

learning_rate = float(settings_dict.get("learning_rate", 0.00025))

```



Todas las claves se validan frente a [`SettingsSchema`](../../src/settings/schema.py), garantizando el mapeo automático a la sección correcta de INI y el respaldo desde `.env`. Los contratos de dominio segregados residen en [`src/interfaces/`](../../src/interfaces) (`controller.py`, `drivers.py`, `engine.py`, `repositories.py`), y la propiedad del hardware entre subprocesos se rige por `CARINA_GATEWAY_ROLE` (`owner` en `CentralController` frente a `remote` en UI/AI/SDS).



---



## 2. Jerarquía de Agentes y Extensión de Aprendizaje por Refuerzo



La arquitectura neuronal de CARINA divide la toma de decisiones en tres roles especializados ubicados en [`src/agents/`](../../src/agents):



1. **`LocalAgent` ([`local_agent.py`](../../src/agents/local_agent.py)):** Agente táctico PPO-TCN que controla las duraciones de fase de las intersecciones locales.

2. **`GuardianAgent` ([`guardian_agent.py`](../../src/agents/guardian_agent.py)):** Centinela de seguridad neuro-simbólico D3QN que audita y veta acciones inseguras.

3. **`StrategistAgent` ([`strategist_agent.py`](../../src/agents/strategist_agent.py)):** Coordinador arterial de grafos ST-GATv2 Lite que suministra embeddings espacio-temporales y ondas verdes emergentes.



### 2.1 Implementación de un Agente Personalizado

Para crear un nuevo agente táctico (ej., `CustomPPOAgent`):



1. Cree `src/agents/custom_ppo_agent.py`:

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



2. Registre su agente en [`src/core/decision_coordinator.py`](../../src/core/decision_coordinator.py):

```python

from agents.custom_ppo_agent import CustomPPOAgent



# Inside DecisionCoordinator initialization:

if agent_type == "CUSTOM_PPO":

    self.agent = CustomPPOAgent(state_dim, action_dim, config)

```



---



## 3. Empaquetado y Distribución



CARINA proporciona un script hermético de compilación multietapa con Docker ([`scripts/build_deb.sh`](../../scripts/build_deb.sh)) que compila el frontend web CCO (React), el gateway nativo en Go, prepara el virtualenv aislado de Python y empaqueta la solución en un paquete Debian (`dist/carina_1.0.0_amd64.deb`).



Para generar el paquete localmente:

```bash

./scripts/build_deb.sh

```



Para instrucciones de despliegue y tiempo de ejecución, consulte [Despliegue y Empaquetado](deployment_and_packaging.md).



---



## 4. Simulación de Vehículos de Emergencia y Corredores de Preempción



Los desarrolladores pueden probar y validar la preempción de vehículos de emergencia sin transpondedores físicos ni ambulancias reales mediante el simulador CLI integrado ([`demo/evp_vehicle_simulator.py`](../../demo/evp_vehicle_simulator.py)):



### 4.1 Ejecución de los Modos de Simulación

```bash

# 1. Carrera de Emergencia Individual (ambulancia SAMU avanzando hacia cruce con sirena encendida):

python demo/evp_vehicle_simulator.py --mode emergency --vehicle SAMU-01 --duration 25.0



# 2. Patrulla Continua Multi-Corporación (SAMU, Bomberos, Policía orbitando con telemetría a 2 Hz):

python demo/evp_vehicle_simulator.py --mode patrol --duration 60.0



# 3. Aproximación con Sirena Apagada (Comprueba el veto de preempción cuando el vehículo se acerca sin sirena activa):

python demo/evp_vehicle_simulator.py --mode siren_off --vehicle BOMB-03

```



De forma predeterminada, el simulador transmite a `http://localhost:8085` (receptor autónomo) o a `http://localhost:2201` (Gateway Web en Go). Especifique host y puerto mediante:

```bash

python demo/evp_vehicle_simulator.py --host 127.0.0.1 --port 2201 --mode emergency

```



### 4.2 Inyección HTTP Directa vía cURL

Los desarrolladores también pueden emitir pings sintéticos de telemetría GPS directamente:

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

La respuesta esperada es `HTTP 204 No Content` ($< 1\text{ ms}$). Observe los registros de preempción en la consola de CARINA:

```text

[EVPKinematicsEngine] Vehicle SAMU-01 entered approach gate (112.4m to J01)

[EVPPreemptionEngine] Granting emergency preemption hold on Stage 1 for SAMU-01

[GoGatewayClient] Sent NDJSON command: {"cmd":"evp_preempt","intersection_id":"J01",...}

```



---



<div align="center">

  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>

  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>

  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>

  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>

</div>
