---
tags: [testing, pytest, coverage, mocks, safety, validation]
aliases: [Directives de Tests, Tests Unitaires, Mocks de Sécurité, Assurance Qualité]
---

# 🧪 Directives de Tests & Validation

CARINA régit des infrastructures de feux de circulation municipales critiques pour la sécurité. Une fiabilité absolue, des tests unitaires déterministes, des mocks de pilotes et une validation continue des vetos de sécurité sont obligatoires avant tout déploiement de modifications.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🛡️ Voir [Sécurité & Watchdog](safety_and_watchdog.md) | 🚦 Voir [Pilotes Matériels](hardware_drivers.md) | 🛠️ Voir [Guides du Développeur](developer_guides.md) | 🚑 Voir [Préemption EVP](evp_and_preemption.md)

---

## 1. Exécution de la Suite de Tests (`pytest`)

CARINA dispose d'une suite de tests exhaustive comprenant **647 tests automatisés** (vérifiés via `pytest --collect-only`), garantissant la sécurité, l'absence de régression et un basculement déterministe à la microseconde sur chaque sous-système. Tous les tests sont situés dans [`tests/`](../../tests).

### 1.1 Exécuter Tous les Tests
```bash
pytest tests/ -v
```

### 1.2 Générer des Rapports de Couverture
Pour mesurer la couverture de branches et d'instructions à travers `src/` :
```bash
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```
Le rapport de couverture HTML est généré dans `htmlcov/index.html`.

### 1.3 Exécuter les Tests Unitaires de la Passerelle Matérielle Go (`go test`)
Pour exécuter les tests unitaires natifs en Go couvrant NTCIP, UTMC, les trappes et la découverte :
```bash
cd src_go && go test -v ./...
```

---

## 2. Structure Réelle du Répertoire de Tests

```text
tests/
├── conftest.py                     # Fixtures pytest partagées, bases de test temporaires & envs simulés
├── mock_junctions.py               # Graphe synthétique de topologie & définitions de nœuds
├── benchmark.py                    # Bancs d'essai de performance (débit & latence)
│
├── unit/                           # Tests Unitaires Isolés (647 Tests Collectés au Total)
│   ├── test_evp_service.py         # Cycle de vie EVPService, pipeline d'ingestion & déclencheurs de préemption
│   ├── test_evp_kinematics.py      # Distance Haversine, vitesse, cap & portes d'approche
│   ├── test_evp_preemption_engine.py # Arbitrage de maintien de préemption, watchdog 45s & dégagement
│   ├── test_evp_map_topology.py    # Correspondance topologique, approches entrantes & mappage d'étapes
│   ├── test_evp_fleet_persistence.py # Opérations CRUD sur flottes autorisées & mise en cache des plaques
│   ├── test_evp_config_repo.py     # Dépôt de configuration EVP & persistance des seuils
│   ├── test_evp_fleet_controller.py # Logique métier & validation de gestion de flotte
│   ├── test_evp_fleet_csv.py       # Export CSV de flotte & analyse d'import en masse
│   ├── test_evp_fleet_save_flow.py # Flux complet d'enregistrement formulaire IHM flotte & commit base
│   ├── test_evp_hardware_parity_persistence.py # Parité d'état matériel entre moteurs de base de données
│   ├── test_evp_settings_handler.py # Persistance des paramètres EVP dans settings.ini & .env
│   ├── test_evp_vehicle_marker.py  # Glyphes de marqueurs canvas Flet & animations stroboscopiques EVP
│   ├── test_local_agent.py         # Sélection d'action de l'Agent Tactique PPO & boucle de mise à jour
│   ├── test_guardian_agent.py      # Sentinelle de sécurité D3QN & validation des seuils de risque
│   ├── test_strategist_agent.py    # Coordinateur artériel par Attention sur Graphes ST-GATv2 Lite
│   ├── test_settings_modular.py    # SettingsService modulaire, Schéma, Fournisseurs & INI
│   ├── test_settings_view.py       # Vue des paramètres Flet & persistance d'IHM
│   ├── test_monitor_client.py      # Client MonitorClient polymorphe, transports HTTP & MQTT
│   ├── test_monitor_disconnect.py  # Re tentative de télémétrie, vidage de tampon & flux de déconnexion
│   ├── test_core_components.py     # Tests de DecisionCoordinator & ActionAuthorizer
│   ├── test_go_gateway_bridge.py   # Sous-processus Passerelle Go & pont IPC par tubes
│   ├── test_traffic_light_driver.py # Abstraction de haut niveau de pilote de feu de signalisation
│   ├── test_traffic_modular_components.py # Composants modulaires de feu de signalisation
│   ├── test_driver_factory_brand_model.py # Instanciation de pilotes (NTCIP / UTMC / Go)
│   ├── test_hardware_event_listener.py    # Écouteurs de trappes SNMP & analyse de pannes
│   ├── test_connection_db_persistence.py  # Persistance des points de terminaison de contrôleurs
│   ├── test_connection_manager_orchestrator.py # Orchestration de la machine à états de connexion
│   ├── test_fenix_supervisor.py    # Cycle de vie superviseur FENIX, récupération & résurrection
│   ├── test_fenix_process_runner.py # Contrôle de sous-processus runner (SIGTERM/SIGKILL)
│   ├── test_fenix_recovery_policy.py # Politique de récupération après crash fenêtrée & backoff exponentiel
│   ├── test_fenix_state_reconciler.py # Transfert sur frontière propre & synchronisation FROZEN_SYNC
│   ├── test_watchdog_fenix_integration.py # Déclencheur expiration Watchdog vers résurrection FENIX
│   ├── test_security_modular.py    # AuthService, UserService, Bcrypt & Verrouillage
│   ├── test_security_manager.py    # Validation de la façade historique SecurityManager
│   ├── test_captum_analyzer.py     # Tests d'attribution par Gradients Intégrés
│   ├── test_xai_report_builder.py  # Génération de rapports Word ABNT avec équations OMML
│   ├── test_multi_agent_modular_builder.py # Assemblage modulaire de blocs de rapport multi-agents
│   ├── test_mfd_processor.py       # Processeur central du Diagramme Fondamental Macroscopique
│   ├── test_mfd_report_generator.py # Génération de rapports MFD et ajustement de courbe
│   ├── test_mfd_db_reconstruction.py # Reconstruction MFD à partir des tables PostgreSQL
│   ├── test_mfd_new_report.py      # Pipeline de génération de nouveaux rapports MFD
│   ├── test_sas_report_generator.py # Tests de mandats du Smart Analysis System
│   ├── test_sas_data_transducer.py # Transducteur de données de télémétrie SAS
│   ├── test_sas_helpers.py         # Fonctions d'aide aux calculs mathématiques SAS
│   ├── test_sas_mfd_db_cache.py    # Mise en cache de base de données MFD pour SAS
│   ├── test_semantic_transducer_device.py # Transducteur SLM hors ligne & allocation VRAM
│   ├── test_planning_view.py       # Tests d'IHM de la Vue de Planification Flet
│   ├── test_planning_architecture.py # Présentateur de canvas de planification & gestionnaires d'export
│   ├── test_planning_export_handler.py # Gestionnaires d'export CSV des plans de feux
│   ├── test_planning_panel_presenter.py # Présentateur d'IHM de panneau de planification
│   ├── test_live_canvas_map_widget.py # Dessin personnalisé de routes et feux sur canvas Flet
│   ├── test_map_interaction_precision.py # Calculs de zoom, dérive de coordonnées & cache de clic rue
│   ├── test_map_event_router_precision.py # Désambiguïsation de clic entre feu tricolore et rue
│   ├── test_interactive_map_precision.py # Précision de clic InteractiveMap et sélection de calque
│   ├── test_planning_map_sync.py   # Rayon de sélection PlanningMapRenderer & synchro canvas
│   ├── test_live_data_provider_ipc.py # Flux de files IPC en mémoire LiveDataProvider
│   ├── test_watchdog.py            # Logique de pulsation Watchdog et temporisateurs de processus
│   ├── test_consolidation_purge.py # Purge et consolidation du stockage delta de dynamique des fluides
│   ├── test_csv_template_export_import.py # Import/export CSV de modèles de contrôleurs
│   ├── test_db_schema_isolation.py # Isolation de schémas de base de données pour les tests
│   ├── test_infrastructure_client.py # Client pour mandats d'infrastructure
│   ├── test_intersection_state_manager.py # Suivi d'état multi-carrefours
│   ├── test_main_components.py     # Composants principaux du contrôleur central
│   ├── test_manual_override_hft.py # Dérogations manuelles de phase haute fréquence
│   ├── test_pushdown_query.py      # Évaluation de requêtes SQL pushdown
│   ├── test_tls_state_provider.py  # Fournisseur d'état des feux de signalisation
│   ├── test_ui_main_orchestrator.py # Tests d'orchestration principale de l'IHM
│   ├── test_window_manager.py      # Gestion du cycle de vie des fenêtres bureautiques
│   ├── test_population_manager_pbt.py # Isolation de cohorte PBT intra-phase & sécurité de tenseurs
│   ├── test_performance_margin_calculator.py # Marge de graduation de dynamique des fluides
│   ├── test_reward_weights_calculator.py # Équilibrage physique des récompenses (traversée HCM)
│   ├── test_maturity_pacing_calculator.py # Rythme automatique d'épisodes selon topologie réseau
│   ├── test_yellow_schedule_manager.py # Évaluateur d'horaires de clignotant jaune nocturne
│   └── test_yellow_schedule_card.py # Carte IHM de programmation jaune & contrôles horaires
│
└── integration/                    # Tests d'Intégration Système de Bout en Bout (5 Modules)
    ├── test_system_integration.py    # Cycle complet télémétrie-vers-actionnement gRPC
    ├── test_gateway_ipc_pipeline.py  # Pipeline IPC par tube anonyme NDJSON de la Passerelle Go
    ├── test_hft_performance_sla.py   # Latence de boucle HFT sous la milliseconde & validation SLA
    ├── test_postgres_migrations.py   # Migrations de schéma PostgreSQL Alembic & rollback
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
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
