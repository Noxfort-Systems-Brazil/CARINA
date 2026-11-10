---
tags: [developer, guide, setup, agents, config, 12-factor]
aliases: [Guides Développeur, Référence de Configuration, Architecture des Agents]
---

# 🛠️ Guides du Développeur & d'Intégration

Ce document fournit des guides pas à pas pour les développeurs concernant la configuration de l'environnement, le paramétrage des options, la création d'agents d'apprentissage par renforcement personnalisés et la compréhension de la base de code de CARINA.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🧪 Voir [Tests & Validation](testing.md) | 🚀 Voir [Déploiement & Empaquetage](deployment_and_packaging.md) | 🗄️ Voir [Base de Données & Schémas](database_and_schemas.md) | 🚑 Voir [Préemption EVP](evp_and_preemption.md)

---

## 1. Configuration de l'Environnement & Paramètres

CARINA applique la méthodologie de configuration **12-Factor App**. Les secrets et les attributs d'environnement sont séparés des hyperparamètres opérationnels :

### 1.1 Secrets & Infrastructure : `.env`
Copiez le fichier exemple vers `.env` :
```bash
cp .env.example .env
```
Configurez vos identifiants :
```bash
CARINA_ENV=development                   # 'development' ou 'production'
CARINA_DB_TYPE=sqlite                    # 'sqlite' ou 'postgresql'
CARINA_DB_USER=admin
CARINA_DB_PASSWORD=admin
CARINA_DB_HOST=localhost
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_SNMP_COMMUNITY=public

# Passerelle Matérielle & Web (Sous-processus Go)
CARINA_GATEWAY_ENABLED=true
CARINA_GATEWAY_PORT=2201
CARINA_TAILSCALE_AUTH_KEY=               # Optionnel: tskey-auth-xxx pour configuration Funnel automatique

# Télémétrie Monitor Externe (Courtier MQTT ou URL HTTP/Cloud/Ngrok)
CARINA_MQTT_HOST=127.0.0.1
CARINA_MQTT_PORT=1883
CARINA_MQTT_USER=
CARINA_MQTT_PASSWORD=
```

### 1.2 Paramètres Opérationnels : `config/settings.ini`
Les hyperparamètres, intervalles d'entraînement et tolérances du watchdog résident dans [`config/settings.ini`](../../config/settings.ini) :

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
auto_pacing_enabled = False
auto_performance_margin_enabled = False
child_phase_episodes = 1
teen_phase_min_episodes = 1
performance_margin = -100.0

[REWARD_WEIGHTS]
auto_reward_weights_enabled = False
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

[REMOTE_GATEWAY]
enabled = True
port = 2201
tailscale_enabled = False
tailscale_hostname = carina-edge

[EVP]
preemption_enabled = True
entry_distance_meters = 160.0
exit_distance_meters = 15.0
dwell_watchdog_seconds = 45.0
enforce_clearance = True
```

### 1.3 Interaction avec les Calculateurs Programmatiques
Pour un étalonnage autonome du réseau, CARINA met à disposition des calculateurs autonomes dans `src/promotion/` et `src/engine/` :

```python
# 1. Rythme Dynamique de Maturité (durée des épisodes selon la topologie) :
from promotion.maturity_pacing_calculator import MaturityPacingCalculator
MaturityPacingCalculator.apply_if_enabled(maturity_manager, net, tls_list, settings)

# 2. Marge Dynamique de Performance pour la Graduation (dynamique des fluides & limitations de vitesse) :
from promotion.performance_margin_calculator import PerformanceMarginCalculator
margin = PerformanceMarginCalculator.calculate_from_topology(net, settings)
PerformanceMarginCalculator.apply_if_enabled(maturity_manager, margin, settings)

# 3. Équilibrage Dynamique des Poids de Récompense (temps de traversée HCM) :
from engine.reward_weights_calculator import RewardWeightsCalculator
weights = RewardWeightsCalculator.calculate_from_topology(net, settings)
RewardWeightsCalculator.apply_if_enabled(reward_calculator, weights, settings)
```

### 1.4 Interaction avec les Paramètres (`src/settings/`)
CARINA intègre un sous-système de configuration propre et conforme aux principes SOLID dans [`src/settings/`](../../src/settings).

Les développeurs peuvent accéder aux paramètres via le service modulaire `SettingsService` ou via la façade de compatibilité `SettingsManager` :

```python
# Approche modulaire directe :
from settings import SettingsService, IniFileStorage, DotenvSecretProvider
service = SettingsService(
    storage=IniFileStorage("config/settings.ini"),
    env_provider=DotenvSecretProvider()
)
value = service.get("ai_gamma", default=0.99)

# Ou via la façade rétrocompatible (recommandée dans le code existant) :
from utils.settings_manager import SettingsManager
settings_dict = SettingsManager().load_settings()
learning_rate = float(settings_dict.get("learning_rate", 0.00025))
```

Toutes les clés sont validées par rapport à [`SettingsSchema`](../../src/settings/schema.py), garantissant un mappage automatique vers la section INI adéquate et le repli vers `.env`.

---

## 2. Hiérarchie des Agents & Extension de l'Apprentissage par Renforcement

L'architecture neuronale de CARINA divise la prise de décision en trois rôles spécialisés situés dans [`src/agents/`](../../src/agents) :

1. **`LocalAgent` ([`local_agent.py`](../../src/agents/local_agent.py)) :** Agent tactique PPO-TCN contrôlant la durée des phases de carrefours locaux.
2. **`GuardianAgent` ([`guardian_agent.py`](../../src/agents/guardian_agent.py)) :** Sentinelle de sécurité neuro-symbolique D3QN qui audite et oppose son veto aux actions dangereuses.
3. **`StrategistAgent` ([`strategist_agent.py`](../../src/agents/strategist_agent.py)) :** Coordinateur de graphe artériel ST-GATv2 Lite fournissant des plongements spatio-temporels du trafic et générant des ondes vertes émergentes.

### 2.1 Implémentation d'un Agent Personnalisé
Pour créer un nouvel agent tactique (ex. `CustomPPOAgent`) :

1. Créez `src/agents/custom_ppo_agent.py` :
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
        """Sélectionne une action discrète de phase de feux de signalisation."""
        with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu"):
            # Calcul des logits d'action
            action_index = 0
            return action_index

    def update(self, memory_buffer) -> dict:
        """Exécute l'optimisation par rétropropagation."""
        return {"loss": 0.0}
```

2. Enregistrez votre agent dans [`src/core/decision_coordinator.py`](../../src/core/decision_coordinator.py) :
```python
from agents.custom_ppo_agent import CustomPPOAgent

# Au sein de l'initialisation de DecisionCoordinator :
if agent_type == "CUSTOM_PPO":
    self.agent = CustomPPOAgent(state_dim, action_dim, config)
```

---

## 3. Empaquetage & Distribution

Les méthodes historiques d'empaquetage PyInstaller et paquets `.deb` via `build_installer.sh` ont été dépréciées et retirées. Une nouvelle méthode de déploiement et d'installation conteneurisée est prévue pour les prochaines versions.

Pour les instructions de déploiement et d'exécution, voir [Déploiement & Empaquetage](deployment_and_packaging.md).

---

## 4. Simulation de Véhicules d'Urgence & Couloirs de Préemption

Les développeurs peuvent tester et valider la préemption de véhicules d'urgence sans transpondeurs physiques ni ambulances réelles grâce au simulateur CLI intégré ([`demo/evp_vehicle_simulator.py`](../../demo/evp_vehicle_simulator.py)) :

### 4.1 Exécution des Modes de Simulation
```bash
# 1. Piste d'urgence unique (ambulance SAMU fonçant vers un carrefour avec sirène active) :
python demo/evp_vehicle_simulator.py --mode emergency --vehicle SAMU-01 --duration 25.0

# 2. Patrouille multi-corporations en continu (SAMU, Pompiers, Police orbitant avec télémétrie à 2 Hz) :
python demo/evp_vehicle_simulator.py --mode patrol --duration 60.0

# 3. Approche avec sirène éteinte (Vérifie le veto de préemption lors de l'approche sans sirène) :
python demo/evp_vehicle_simulator.py --mode siren_off --vehicle BOMB-03
```

Par défaut, le simulateur transmet à `http://localhost:8085` (récepteur autonome) ou `http://localhost:2201` (Passerelle Web Go). Spécifiez l'hôte et le port cible via :
```bash
python demo/evp_vehicle_simulator.py --host 127.0.0.1 --port 2201 --mode emergency
```

### 4.2 Injection HTTP Directe via cURL
Les développeurs peuvent également déclencher des pings de télémétrie GPS synthétiques directement :
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
La réponse attendue est `HTTP 204 No Content` ($< 1\text{ ms}$). Observez les journaux de préemption dans la console de CARINA :
```text
[EVPKinematicsEngine] Vehicle SAMU-01 entered approach gate (112.4m to J01)
[EVPPreemptionEngine] Granting emergency preemption hold on Stage 1 for SAMU-01
[GoGatewayClient] Sent NDJSON command: {"cmd":"evp_preempt","intersection_id":"J01",...}
```

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
