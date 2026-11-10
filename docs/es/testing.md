---
tags: [pruebas, pytest, cobertura, mocks, seguridad, validacion]
aliases: [Directrices de Pruebas, Pruebas Unitarias, Mocks de Seguridad, Aseguramiento de Calidad]
---

# 🧪 Directrices de Pruebas y Validación

CARINA gobierna infraestructura municipal de tráfico crítica para la seguridad vial. La confiabilidad absoluta, las pruebas unitarias deterministas, los mocks de controladores y la validación continua de vetos de seguridad son obligatorios antes de implementar cambios.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🛡️ Ver [Seguridad y Watchdog](safety_and_watchdog.md) | 🚦 Ver [Controladores de Hardware](hardware_drivers.md) | 🛠️ Ver [Guías para Desarrolladores](developer_guides.md) | 🚑 Ver [Preempción EVP](evp_and_preemption.md)

---

## 1. Ejecución de la Suite de Pruebas (`pytest`)

CARINA cuenta con una suite de pruebas exhaustiva con **861 pruebas automatizadas** (verificadas mediante `pytest --collect-only`), garantizando seguridad, cero regresiones y conmutación por error en microsegundos determinista en cada subsistema. Todas las pruebas se encuentran en [`tests/`](../../tests).

### 1.1 Ejecutar Todas las Pruebas
```bash
pytest tests/ -v
```

### 1.2 Generar Informes de Cobertura
Para medir la cobertura de ramas y declaraciones en `src/`:
```bash
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```
El informe HTML de cobertura se genera en `htmlcov/index.html`.

### 1.3 Ejecutar Pruebas Unitarias del Gateway de Hardware en Go (`go test`)
Para ejecutar las pruebas unitarias nativas en Go que cubren NTCIP, UTMC, traps y descubrimiento:
```bash
cd src_go && go test -v ./...
```

---

## 2. Estructura Real del Directorio de Pruebas

```text
tests/
├── conftest.py                     # Fixtures compartidos de pytest, BDs temporales y entornos mock
├── mock_junctions.py               # Grafo sintético de topología y definiciones de nodos
├── benchmark.py                    # Benchmarks de rendimiento (rendimiento y latencia)
│
├── unit/                           # Pruebas Unitarias Aisladas (861 Pruebas Totales Recopiladas)
│   ├── test_evp_service.py         # Ciclo de vida de EVPService, tubería de ingestión y disparadores
│   ├── test_evp_kinematics.py      # Distancia Haversine, velocidad, rumbo y compuertas de aproximación
│   ├── test_evp_preemption_engine.py # Retención de preempción, watchdog de 45s y despejes
│   ├── test_evp_map_topology.py    # Coincidencia topológica, aproximaciones entrantes y mapeo de fases
│   ├── test_evp_fleet_persistence.py # Operaciones CRUD de flota autorizada y caché de matrículas
│   ├── test_evp_config_repo.py     # Repositorio de configuración de EVP y persistencia de umbrales
│   ├── test_evp_fleet_controller.py # Lógica de negocio y validación de gestión de flotas
│   ├── test_evp_fleet_csv.py       # Exportación CSV e importación masiva de flotas
│   ├── test_evp_fleet_save_flow.py # Flujo de guardado de formulario de UI y commit en base de datos
│   ├── test_evp_hardware_parity_persistence.py # Paridad de estado de hardware entre motores de BD
│   ├── test_evp_settings_handler.py # Persistencia de ajustes de EVP en settings.ini y .env
│   ├── test_evp_vehicle_marker.py  # Glifos de vehículos EVP en canvas Flet y animaciones estroboscópicas
│   ├── test_local_agent.py         # Selección de acciones del Agente Táctico PPO y bucle de actualización
│   ├── test_guardian_agent.py      # Centinela de seguridad D3QN y validación de umbrales de riesgo
│   ├── test_strategist_agent.py    # Coordinador arterial ST-GATv2 Lite con Atención en Grafos
│   ├── test_settings_modular.py    # SettingsService modular, esquema, proveedores e INI
│   ├── test_settings_view.py       # Vista de Ajustes en Flet y persistencia en UI
│   ├── test_monitor_client.py      # MonitorClient polimórfico, transportes HTTP y MQTT
│   ├── test_monitor_disconnect.py  # Reintentos de telemetría, vaciado de búfer y desconexión
│   ├── test_core_components.py     # Pruebas de DecisionCoordinator y ActionAuthorizer
│   ├── test_go_gateway_bridge.py   # Subproceso del Gateway Go y puente IPC por tuberías
│   ├── test_traffic_light_driver.py # Abstracción de alto nivel de controladores semafóricos
│   ├── test_traffic_modular_components.py # Componentes modulares de controladores semafóricos
│   ├── test_driver_factory_brand_model.py # Instanciación de controladores (NTCIP / UTMC / Go)
│   ├── test_hardware_event_listener.py    # Receptores de traps SNMP y análisis de fallos
│   ├── test_connection_db_persistence.py  # Persistencia de endpoints de controladores
│   ├── test_connection_manager_orchestrator.py # Orquestación de máquinas de estados de conexión
│   ├── test_fenix_supervisor.py    # Ciclo de vida del supervisor FENIX, recuperación y resurrección
│   ├── test_fenix_process_runner.py # Control de procesos en subprocesos (SIGTERM/SIGKILL)
│   ├── test_fenix_recovery_policy.py # Política de recuperación en ventana móvil y backoff exponencial
│   ├── test_fenix_state_reconciler.py # Traspaso en límites limpios y sincronización FROZEN_SYNC
│   ├── test_watchdog_fenix_integration.py # Disparo por timeout de Watchdog a resurrección FENIX
│   ├── test_security_modular.py    # AuthService, UserService, PBKDF2 y Bloqueo por Fuerza Bruta
│   ├── test_security_manager.py    # Validación de la fachada heredada SecurityManager
│   ├── test_captum_analyzer.py     # Pruebas de atribución por Gradientes Integrados
│   ├── test_xai_report_builder.py  # Generación de informes Word ABNT con ecuaciones OMML
│   ├── test_multi_agent_modular_builder.py # Ensamblaje modular de bloques de informes multiagente
│   ├── test_mfd_processor.py       # Procesador central del Diagrama Fundamental Macroscópico
│   ├── test_mfd_report_generator.py # Generación de informes MFD y ajuste de curvas
│   ├── test_mfd_db_reconstruction.py # Reconstrucción de MFD a partir de tablas PostgreSQL
│   ├── test_mfd_new_report.py      # Flujo de generación de nuevos informes MFD
│   ├── test_sas_report_generator.py # Pruebas de justificaciones del Smart Analysis System
│   ├── test_sas_data_transducer.py # Transductor de telemetría de SAS
│   ├── test_sas_helpers.py         # Auxiliares de cálculo matemático de SAS
│   ├── test_sas_mfd_db_cache.py    # Caché de base de datos de MFD en SAS
│   ├── test_semantic_transducer_device.py # Transductor SLM offline y asignación de VRAM
│   ├── test_planning_view.py       # Pruebas de UI de la Vista de Planificación en Flet
│   ├── test_planning_architecture.py # Presentador de canvas de planificación y exportadores
│   ├── test_planning_export_handler.py # Exportadores CSV de planes de tiempos semafóricos
│   ├── test_planning_panel_presenter.py # Presentador de UI del panel de planificación
│   ├── test_live_canvas_map_widget.py # Canvas personalizado en Flet para vías y señales
│   ├── test_map_interaction_precision.py # Matemática de zoom, deriva de coordenadas y acierto en vías
│   ├── test_map_event_router_precision.py # Desambiguación de clics entre semáforos y vías
│   ├── test_interactive_map_precision.py # Precisión de pulsación y capas en InteractiveMap
│   ├── test_planning_map_sync.py   # Radio de acierto de PlanningMapRenderer y sincronización
│   ├── test_live_data_provider_ipc.py # Streaming en memoria por colas IPC de LiveDataProvider
│   ├── test_watchdog.py            # Lógica de latidos del Watchdog y temporizadores de procesos
│   ├── test_consolidation_purge.py # Consolidación de almacenamiento delta de dinámica de fluidos
│   ├── test_csv_template_export_import.py # Importación/exportación CSV de endpoints
│   ├── test_db_schema_isolation.py # Aislamiento de esquemas para suites de pruebas
│   ├── test_infrastructure_client.py # Cliente para justificaciones de infraestructura
│   ├── test_intersection_state_manager.py # Seguimiento de etapas multi-intersección
│   ├── test_main_components.py     # Componentes principales del controlador central
│   ├── test_manual_override_hft.py # Anulaciones manuales de fase en alta frecuencia
│   ├── test_pushdown_query.py      # Evaluación de consultas SQL con pushdown
│   ├── test_tls_state_provider.py  # Proveedor de estados de semáforos
│   ├── test_ui_main_orchestrator.py # Pruebas del orquestador principal de UI
│   ├── test_window_manager.py      # Gestión del ciclo de vida de la ventana de escritorio
│   ├── test_population_manager_pbt.py # Aislamiento intra-fase PBT y seguridad dimensional
│   ├── test_performance_margin_calculator.py # Margen de graduación por fluidos y telemetría infantil
│   ├── test_reward_weights_calculator.py # Balance físico de recompensas (tiempo de tramo HCM)
│   ├── test_maturity_pacing_calculator.py # Regulación automática de duración por topología de red
│   ├── test_yellow_schedule_manager.py # Evaluador de horarios de destello amarillo nocturno
│   └── test_yellow_schedule_card.py # Tarjeta de UI y controles de ventana de destello amarillo
│
└── integration/                    # Pruebas de Integración Extremo a Extremo (5 Módulos)
    ├── test_system_integration.py    # Ciclo completo de telemetría a actuación por gRPC
    ├── test_gateway_ipc_pipeline.py  # Tubería IPC de NDJSON por tuberías anónimas del Gateway Go
    ├── test_hft_performance_sla.py   # Latencia del bucle HFT en sub-milisegundos y SLA
    ├── test_postgres_migrations.py   # Migraciones y reversión de esquemas PostgreSQL con Alembic
    └── test_watchdog_resilience.py   # Conmutación por fallo de latido del Watchdog y resurrección
```

---

## 3. Creación de Pruebas de Veto de Seguridad (`SafetyAuditor`)

Cada nueva acción o transición de fase debe validarse frente a [`src/core/safety_auditor.py`](../../src/core/safety_auditor.py):

```python
import pytest
from core.safety_auditor import SafetyAuditor

def test_symbolic_min_green_veto():
    """Verifica que el auditor vete cambios prematuros de fase antes de que expire el verde mínimo."""
    auditor = SafetyAuditor(min_green_time_seconds=7.0)

    # Simular estado actual: La Fase 1 ha estado activa solo 3.0 segundos
    current_state = {"active_phase": 1, "phase_duration_seconds": 3.0}
    proposed_action = 2  # Intentando cambiar a Fase 2 prematuramente

    # Auditar acción
    authorized_action, is_vetoed, reason = auditor.audit(current_state, proposed_action)

    assert is_vetoed is True
    assert authorized_action == 1  # Forzado a mantener la fase activa
    assert "Minimum Green" in reason


def test_evp_preemption_overrides_rl_action():
    """Verifica la Regla SR-00: la preempción activa fuerza el corredor verde respetando el despeje de amarillo."""
    auditor = SafetyAuditor(min_green_time_seconds=7.0)

    current_state = {
        "active_phase": 2,
        "phase_duration_seconds": 15.0,
        "evp_active": True,
        "evp_target_stage": 1,
        "yellow_clearance_completed": True
    }
    proposed_action = 3  # El agente de RL solicitaba la Fase 3

    authorized_action, is_vetoed, reason = auditor.audit(current_state, proposed_action)

    assert is_vetoed is True
    assert authorized_action == 1  # Forzado a la Fase 1 objetivo de EVP
    assert "SR-00" in reason or "Preemption" in reason
```

---

## 4. Simulación de Controladores de Hardware mediante Mocks

Al realizar pruebas sin hardware físico conectado, utilice los fixtures de simulación provistos en [`tests/conftest.py`](../../tests/conftest.py) para simular respuestas SNMP UDP:

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
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
