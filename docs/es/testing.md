---
tags: [pruebas, pytest, cobertura, mocks, seguridad, validacion]
aliases: [Directrices de Pruebas, Pruebas Unitarias, Mocks de Seguridad, Aseguramiento de Calidad]
---

# 🧪 Directrices de Pruebas y Validación

CARINA gobierna infraestructura municipal de tráfico crítica para la seguridad vial. La confiabilidad absoluta, las pruebas unitarias deterministas, los mocks de controladores y la validación continua de vetos de seguridad son obligatorios antes de implementar cambios.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🛡️ Ver [Seguridad y Watchdog](safety_and_watchdog.md) | 🚦 Ver [Controladores de Hardware](hardware_drivers.md) | 🛠️ Ver [Guías para Desarrolladores](developer_guides.md) | 🚑 Ver [Preempción EVP](evp_and_preemption.md)

---

## 1. Ejecución de la Suite de Pruebas (`pytest`)

CARINA cuenta con una suite de pruebas exhaustiva con **967 pruebas automatizadas en Python** (verificadas mediante `pytest --collect-only`: **935 pruebas unitarias** en 192 archivos, **18 pruebas de integración** en 8 archivos y **14 pruebas** en 4 archivos de prueba raíz) más **46 pruebas unitarias en Go** en 15 archivos `*_test.go`, garantizando seguridad, cero regresiones y conmutación por error en microsegundos determinista en cada subsistema. Todas las pruebas se encuentran en [`tests/`](../../tests) y [`src_go/`](../../src_go).

### 1.1 Ejecutar Pruebas con Guardia de Memoria (`scripts/pytest_limited.sh`)
Para evitar que los fixtures multiproceso de PyTorch/SLM agoten la RAM del host durante ejecuciones completas, utilice preferentemente el ejecutor limitado por kernel [`scripts/pytest_limited.sh`](../../scripts/pytest_limited.sh) emparejado con [`tests/memory_guard.py`](../../tests/memory_guard.py):
```bash
# Aplica límites cgroup v2 de systemd (MemoryHigh=1536M, MemoryMax=2048M, MemorySwapMax=512M)
# o recurre a ulimit -d + guardia RSS de árbol de procesos CARINA_PYTEST_MAX_RAM_MB:
./scripts/pytest_limited.sh tests/ -v
```
- **Reclamación Determinista de Recursos:** `tests/memory_guard.py` muestrea la memoria RSS del árbol de procesos, ejecuta `gc.collect()` / `malloc_trim()` suaves y limpia singletons (`GoGatewayClient`, `HardwareConnectionManager`, `DatabaseManager`, figuras de Matplotlib) mediante `reclaim_test_resources()`.
- **Guardia de Pruebas SLM Offline:** La carga real de LLM GGUF está deshabilitada por defecto durante `pytest`, a menos que se exporte explícitamente `CARINA_ALLOW_REAL_SLM=1`.

### 1.2 Ejecutar Todas las Pruebas Directamente e Informes de Cobertura
```bash
pytest tests/ -v
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```
El informe HTML de cobertura se genera en `htmlcov/index.html`.

### 1.3 Ejecutar Pruebas Unitarias del Gateway de Hardware en Go (`go test`)
Para ejecutar las pruebas unitarias nativas en Go (46 funciones de prueba que cubren NTCIP, UTMC, SNMPv3/codec, traps binarios, descubrimiento, failsafe, EVP y autenticación/TLS del Web Gateway):
```bash
cd src_go && go test -v -race ./...
```

---

## 2. Estructura Real del Directorio de Pruebas

```text
tests/
├── conftest.py                     # Fixtures compartidos de pytest, BDs temporales y entornos mock
├── memory_guard.py                 # Monitor RSS de árbol de procesos, trims GC suaves y reclamación de singletons
├── mock_junctions.py               # Grafo sintético de topología y definiciones de nodos
├── benchmark.py                    # Benchmarks de rendimiento (rendimiento y latencia)
├── test_*.py                       # 4 suites raíz (14 pruebas: sanidad, invariantes, pacing, cobertura semanal)
│
├── unit/                           # Pruebas Unitarias Aisladas (192 archivos / 935 pruebas recopiladas)
│   ├── test_closed_loop_hardware_control.py # Decodificación de máscaras NTCIP/UTMC y sincronización en lazo cerrado
│   ├── test_field_readiness_configs.py # config_path por intersección, reenvío de tokens y temporización de fases
│   ├── test_grpc_security.py       # Pruebas de Synapse gRPC TLS/mTLS y BearerTokenServerInterceptor
│   ├── test_sds_cco_broadcast_security.py # TLS de CCOBroadcastClient + fijación SHA-256 de certificado hoja
│   ├── test_guardian_calibration_and_training.py # Entrenamiento QR-D3QN en CHILD, calibración F2, Noisy-OR y freeze
│   ├── test_db_connection_and_locking.py # PostgresConnectionPool, pragmas SQLite WAL y db_transaction
│   ├── test_nvidia_memory_and_hotpath_optimizations.py # BatchedPAE, torch.vmap, NumPy GAE, ReplayMemory en host
│   ├── test_phase2_db_ipc_optimizations.py # SQL make_interval, ThreadSafePipeConnection y retención EVP
│   ├── test_phase3_slm_xai_render_optimizations.py # slm_process_lock, VRAM pynvml, mpl_utils, caché XAI
│   ├── test_phase4_gateway_evp_ui_optimizations.py # Pausa de MapAnimator en ventana oculta, paginación AuditLog, CCO
│   ├── test_pytest_memory_guard.py # Muestreo RSS de árbol de procesos, trims suaves y reclamación de recursos
│   ├── test_solid_full_audit_refactoring.py # Interfaces segregadas y descomposiciones SOLID de coordinadores
│   ├── test_solid_gateway_and_step_refactoring.py # Pruebas DIP del coordinador de gateway y canalización de paso
│   ├── test_evp_*.py               # 12 módulos EVP (servicio, cinemática, preempción, flota, marcadores UI)
│   ├── test_local_agent.py         # Selección de acciones del Agente Táctico PPO y bucle de actualización
│   ├── test_guardian_agent.py      # Centinela de seguridad D3QN y validación de umbrales de riesgo
│   ├── test_strategist_agent.py    # Coordinador arterial ST-GATv2 Lite con Atención en Grafos
│   ├── test_pae_model.py           # Pruebas de PAE iTransformer condicionado por acción e incertidumbre
│   ├── test_remote_gateway_and_cco.py # Pruebas de Gateway Web Tailscale y stream CCO
│   ├── test_settings_modular.py    # SettingsService modular, esquema, proveedores e INI
│   ├── test_monitor_client.py      # MonitorClient polimórfico, transportes HTTP y MQTT
│   ├── test_go_gateway_bridge.py   # Subproceso del Gateway Go y puente IPC por tuberías
│   ├── test_fenix_*.py             # Supervisor FENIX, runner, política de recuperación y reconciliador de estado
│   ├── security/                   # Criptografía, PBKDF2, política de contraseñas y suites de seguridad SOLID
│   └── ...                         # Cobertura completa en core, mfd, sas, xai, rendering y ui
│
└── integration/                    # Pruebas de Integración Extremo a Extremo (8 Módulos / 18 Pruebas)
    ├── test_system_integration.py    # Ciclo completo de telemetría a actuación por gRPC
    ├── test_gateway_ipc_pipeline.py  # Tubería IPC de NDJSON por tuberías anónimas del Gateway Go
    ├── test_gateway_ownership_and_fenix_roundtrip.py # Propiedad CARINA_GATEWAY_ROLE owner/remote y ciclo FENIX
    ├── test_go_gateway_snmp_hil_loopback.py # Bucle HIL entre binario Go compilado real <-> agente mock SNMP
    ├── test_hft_performance_sla.py   # Latencia del bucle HFT en sub-milisegundos y SLA
    ├── test_postgres_migrations.py   # Migraciones y reversión de esquemas PostgreSQL con Alembic
    ├── test_traffic_light_drivers.py # Verificaciones de integración de drivers NTCIP/UTMC de alto nivel
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
