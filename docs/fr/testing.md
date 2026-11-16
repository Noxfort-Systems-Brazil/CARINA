---
tags: [testing, pytest, coverage, mocks, safety, validation]
aliases: [Directives de Tests, Tests Unitaires, Mocks de Sécurité, Assurance Qualité]
---

# 🧪 Directives de Tests & Validation

CARINA régit des infrastructures de feux de circulation municipales critiques pour la sécurité. Une fiabilité absolue, des tests unitaires déterministes, des mocks de pilotes et une validation continue des vetos de sécurité sont obligatoires avant tout déploiement de modifications.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🛡️ Voir [Sécurité & Watchdog](safety_and_watchdog.md) | 🚦 Voir [Pilotes Matériels](hardware_drivers.md) | 🛠️ Voir [Guides du Développeur](developer_guides.md) | 🚑 Voir [Préemption EVP](evp_and_preemption.md)

---

## 1. Exécution de la Suite de Tests (`pytest`)

CARINA dispose d'une suite de tests exhaustive comprenant **967 tests Python automatisés** (vérifiés via `pytest --collect-only` : **935 tests unitaires** répartis sur 192 fichiers, **18 tests d'intégration** sur 8 fichiers et **14 tests** sur 4 fichiers de test à la racine) plus **46 tests unitaires Go** répartis sur 15 fichiers `*_test.go`, garantissant la sécurité, l'absence de régression et un basculement déterministe à la microseconde sur chaque sous-système. Tous les tests sont situés dans [`tests/`](../../tests) et [`src_go/`](../../src_go).

### 1.1 Exécuter les Tests avec Protection Mémoire (`scripts/pytest_limited.sh`)
Pour éviter que les fixtures multiprocessus PyTorch/SLM n'épuisent la RAM de l'hôte lors des exécutions complètes, privilégiez l'exécuteur limité au niveau noyau [`scripts/pytest_limited.sh`](../../scripts/pytest_limited.sh) associé à [`tests/memory_guard.py`](../../tests/memory_guard.py) :
```bash
# Applique les limites systemd cgroup v2 (MemoryHigh=1536M, MemoryMax=2048M, MemorySwapMax=512M)
# ou bascule sur ulimit -d + la garde RSS d'arbre de processus CARINA_PYTEST_MAX_RAM_MB :
./scripts/pytest_limited.sh tests/ -v
```
- **Récupération Déterministe des Ressources :** `tests/memory_guard.py` échantillonne le RSS de l'arbre de processus, exécute `gc.collect()` / `malloc_trim()` en douceur et nettoie les singletons (`GoGatewayClient`, `HardwareConnectionManager`, `DatabaseManager`, figures Matplotlib) via `reclaim_test_resources()`.
- **Garde de Test SLM Hors Ligne :** Le chargement réel de LLM GGUF est désactivé par défaut sous `pytest` sauf si `CARINA_ALLOW_REAL_SLM=1` est explicitement exporté.

### 1.2 Exécuter Directement Tous les Tests & Rapports de Couverture
```bash
pytest tests/ -v
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```
Le rapport de couverture HTML est généré dans `htmlcov/index.html`.

### 1.3 Exécuter les Tests Unitaires de la Passerelle Matérielle Go (`go test`)
Pour exécuter les tests unitaires natifs en Go (46 fonctions de test couvrant NTCIP, UTMC, SNMPv3/codec, trappes binaires, découverte, fail-safe, EVP et authentification/TLS de la Passerelle Web) :
```bash
cd src_go && go test -v -race ./...
```

---

## 2. Structure Réelle du Répertoire de Tests

```text
tests/
├── conftest.py                     # Fixtures pytest partagées, bases de test temporaires & envs simulés
├── memory_guard.py                 # Moniteur RSS d'arbre de processus, trims GC doux & libération de singletons
├── mock_junctions.py               # Graphe synthétique de topologie & définitions de nœuds
├── benchmark.py                    # Bancs d'essai de performance (débit & latence)
├── test_*.py                       # 4 suites racine (14 tests : cohérence, invariants, pacing, couverture hebdomadaire)
│
├── unit/                           # Tests Unitaires Isolés (192 fichiers / 935 tests collectés)
│   ├── test_closed_loop_hardware_control.py # Décodage des masques NTCIP/UTMC & synchro d'étapes en boucle fermée
│   ├── test_field_readiness_configs.py # config_path par carrefour, transfert de jetons & minutages de phase
│   ├── test_grpc_security.py       # Tests TLS/mTLS gRPC Synapse & BearerTokenServerInterceptor
│   ├── test_sds_cco_broadcast_security.py # CCOBroadcastClient TLS + épinglage SHA-256 du certificat feuille
│   ├── test_guardian_calibration_and_training.py # Entraînement CHILD QR-D3QN, calibration F2, Noisy-OR & gel
│   ├── test_db_connection_and_locking.py # PostgresConnectionPool, pragmas SQLite WAL & db_transaction
│   ├── test_nvidia_memory_and_hotpath_optimizations.py # BatchedPAE, torch.vmap, GAE NumPy, ReplayMemory hôte
│   ├── test_phase2_db_ipc_optimizations.py # SQL make_interval, ThreadSafePipeConnection & rétention EVP
│   ├── test_phase3_slm_xai_render_optimizations.py # slm_process_lock, VRAM pynvml, mpl_utils, cache XAI
│   ├── test_phase4_gateway_evp_ui_optimizations.py # Pause fenêtre MapAnimator, pagination AuditLog, perf CCO
│   ├── test_pytest_memory_guard.py # Échantillonnage RSS, trims doux & récupération de ressources
│   ├── test_solid_full_audit_refactoring.py # Interfaces ségréguées & décompositions SOLID des coordinateurs
│   ├── test_solid_gateway_and_step_refactoring.py # Tests DIP du coordinateur de passerelle & pipeline par pas
│   ├── test_evp_*.py               # 12 modules EVP (service, cinématique, préemption, flotte, marqueurs UI)
│   ├── test_local_agent.py         # Sélection d'action de l'Agent Tactique PPO & boucle de mise à jour
│   ├── test_guardian_agent.py      # Sentinelle de sécurité D3QN & validation des seuils de risque
│   ├── test_strategist_agent.py    # Coordinateur artériel par Attention sur Graphes ST-GATv2 Lite
│   ├── test_pae_model.py           # Tests iTransformer PAE action-conditionné & estimation d'incertitude
│   ├── test_remote_gateway_and_cco.py # Tests Passerelle Web Tailscale & flux CCO
│   ├── test_settings_modular.py    # SettingsService modulaire, Schéma, Fournisseurs & INI
│   ├── test_monitor_client.py      # Client MonitorClient polymorphe, transports HTTP & MQTT
│   ├── test_go_gateway_bridge.py   # Sous-processus Passerelle Go & pont IPC par tubes
│   ├── test_fenix_*.py             # Superviseur FENIX, runner, politique de récupération & réconciliateur d'état
│   ├── security/                   # Suites de sécurité crypto, PBKDF2, politique de mot de passe & SOLID
│   └── ...                         # Couverture complète sur core, mfd, sas, xai, rendering & ui
│
└── integration/                    # Tests d'Intégration Système de Bout en Bout (8 Modules / 18 Tests)
    ├── test_system_integration.py    # Cycle complet télémétrie-vers-actionnement gRPC
    ├── test_gateway_ipc_pipeline.py  # Pipeline IPC par tube anonyme NDJSON de la Passerelle Go
    ├── test_gateway_ownership_and_fenix_roundtrip.py # Propriété CARINA_GATEWAY_ROLE owner/remote & aller-retour FENIX
    ├── test_go_gateway_snmp_hil_loopback.py # Binaire Go réel compilé <-> boucle HIL agent mock SNMP
    ├── test_hft_performance_sla.py   # Latence de boucle HFT sous la milliseconde & validation SLA
    ├── test_postgres_migrations.py   # Migrations de schéma PostgreSQL Alembic & rollback
    ├── test_traffic_light_drivers.py # Vérifications d'intégration haut niveau des pilotes NTCIP/UTMC
    └── test_watchdog_resilience.py   # Basculement sur expiration Watchdog & résurrection
```

---

## 3. Rédaction de Tests de Veto de Sécurité (`SafetyAuditor`)

Toute nouvelle action ou transition de phase doit obligatoirement être validée par [`src/core/safety_auditor.py`](../../src/core/safety_auditor.py) :

```python
import pytest
from core.safety_auditor import SafetyAuditor

def test_symbolic_min_green_veto():
    """Vérifie que l'auditeur oppose un veto à un changement prématuré avant la fin du vert minimal."""
    auditor = SafetyAuditor(min_green_time_seconds=7.0)

    # Simulation de l'état actuel : la phase 1 n'a été active que pendant 3.0 secondes
    current_state = {"active_phase": 1, "phase_duration_seconds": 3.0}
    proposed_action = 2  # Tentative de passage prématuré en phase 2

    # Audit de l'action
    authorized_action, is_vetoed, reason = auditor.audit(current_state, proposed_action)

    assert is_vetoed is True
    assert authorized_action == 1  # Forcé de maintenir la phase active
    assert "Minimum Green" in reason


def test_evp_preemption_overrides_rl_action():
    """Vérifie la règle SR-00 : la préemption active impose le vert sur le couloir tout en respectant le jaune."""
    auditor = SafetyAuditor(min_green_time_seconds=7.0)

    current_state = {
        "active_phase": 2,
        "phase_duration_seconds": 15.0,
        "evp_active": True,
        "evp_target_stage": 1,
        "yellow_clearance_completed": True
    }
    proposed_action = 3  # L'agent RL voulait la Phase 3

    authorized_action, is_vetoed, reason = auditor.audit(current_state, proposed_action)

    assert is_vetoed is True
    assert authorized_action == 1  # Forcé vers l'étape 1 cible EVP
    assert "SR-00" in reason or "Preemption" in reason
```

---

## 4. Simulation de Pilotes Matériels (Mocks)

Lors de tests de contrôleurs sans matériel physique connecté, utilisez les fixtures de mock fournies dans [`tests/conftest.py`](../../tests/conftest.py) pour simuler les réponses SNMP UDP :

```python
def test_ntcip_driver_status_query(mock_snmp_client):
    driver = NTCIPDriver(ip_address="127.0.0.1", port=161)
    status = driver.query_phase_status()
    assert "greens" in status
    assert "reds" in status
```

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3 ou ultérieure (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
