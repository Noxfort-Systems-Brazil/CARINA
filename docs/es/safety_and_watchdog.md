---
tags: [seguridad, guardian, watchdog, veto, failsafe, neuro-simbolico]
aliases: [Arquitectura de Seguridad, Veto de Guardian, Sistema Watchdog, Auditor de Seguridad]
---

# 🛡️ Arquitectura de Seguridad, Firewall de Guardian y Watchdog

Este documento detalla el Firewall de Seguridad Neuro-Simbólico de doble etapa de CARINA ([`GuardianAgent`](../../src/agents/guardian_agent.py) y [`SafetyAuditor`](../../src/core/safety_auditor.py)), los mecanismos de seguridad fail-safe de hardware y el proceso determinista en tiempo real [`Watchdog`](../../src/watchdog/watchdog_process.py).

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🚨 Ver [Preempción EVP](evp_and_preemption.md) | 🚦 Ver [Controladores de Hardware](hardware_drivers.md) | 🧠 Ver [Formulaciones Neuronales](research_notes.md) | 🧪 Ver [Pruebas y Validación](testing.md)

---

## 1. Visión General del Firewall de Seguridad en Doble Etapa

CARINA desacopla completamente la seguridad pública física del rendimiento del aprendizaje por refuerzo profundo. Las políticas neuronales pueden proponer acciones, pero todas las acciones pasan por un enmascaramiento físico de logits y una verificación de seguridad multietapa antes de su despacho al hardware físico:

```text
Estado + Latente PAE ──> [PhysicalActionMasker] ──> [ActionVetoResolver] ──> Actuación
                          (Logits Despeje/VerdeMín)   ├── 0. Interceptación EVP (SR-00)
                                                      ├── 1. Reglas Simbólicas (SR-01..SR-06)
                                                      └── 2. Veto de Riesgo QR-D3QN + Noisy-OR
```

- [`PhysicalActionMasker`](../../src/engine/physical_action_masker.py): Restringe los logits FP32 de `ActorCriticNet` antes del muestreo, prohibiendo conmutaciones prematuras durante el despeje de amarillo/todo-rojo o por debajo del verde mínimo y forzando transiciones por encima del verde máximo.
- [`ActionVetoResolver`](../../src/engine/action_veto_resolver.py): Orquesta las anulaciones de preempción EVP (`SR-00`) y los vetos por desbordamiento de `GuardianAgent` (`ACTION_KEEP_STAGE`) en la canalización de paso.

---

## 2. Inventario de Reglas de Veto Simbólico (`SafetyAuditor`)

El [`SafetyAuditor`](../../src/core/safety_auditor.py) y [`GuardianSymbolicAuditor`](../../src/safety/guardian_symbolic_auditor.py) imponen restricciones físicas estrictas que nunca pueden ser relajadas, modificadas ni omitidas por la optimización de las redes neuronales:

| ID Regla | Nombre | Descripción de la Restricción | Acción ante Violación |
| :--- | :--- | :--- | :--- |
| **SR-00** | **Preempción de Emergencia (EVP)** | Vehículo de emergencia activo (SAMU/Bomberos/Policía) aproximándose con sirena encendida. | Intercepta la acción; aplica despeje seguro de amarillo y todo-rojo, luego inyecta `ACTION_HOLD` en el corredor verde de destino. |
| **SR-01** | **Tiempo Verde Mínimo** | La fase activa debe permanecer en verde al menos $T_{min} = 7.0\text{ s}$ para evacuar los vehículos en cola. | Fuerza `ACTION_KEEP_PHASE`. |
| **SR-02** | **Despeje de Amarillo** | Cualquier transición de fase debe ejecutar un intervalo obligatorio de aviso de $3.0\text{ s}$ de amarillo. | Intercepta la acción; inyecta fase Amarilla. |
| **SR-03** | **Intervalo Todo-Rojo** | Los movimientos direccionales en conflicto requieren un intervalo de despeje todo-rojo de $2.0\text{ s}$. | Inyecta estado de despeje Todo-Rojo. |
| **SR-04** | **Tiempo Rojo Mínimo** | Los movimientos no atendidos deben cumplir un intervalo mínimo de rojo antes de ser reactivados. | Inhibe la reactivación prematura de la fase. |
| **SR-05** | **Techo Máximo de Verde (Anti-Inanición)** | La fase no puede superar la duración máxima de verde si existen aproximaciones en competencia con colas en espera. | Fuerza la terminación de la fase y la transición a la demanda en espera. |
| **SR-06** | **Matriz de Conflictos y Verde Fantasma** | Previene indicaciones simultáneas de verde en movimientos en conflicto o en vías sin flujo vehicular. | Veto estricto; revierte al estado de reposo seguro. |

---

## 3. Veto Neuronal Calibrado contra Desbordamiento (`GuardianAgent` y `src/safety/`)

El **Guardian Agent** ([`src/agents/guardian_agent.py`](../../src/agents/guardian_agent.py)) integra una **Dueling Double DQN Distributiva por Regresión Cuantílica (`D3QN_TCN`, `num_quantiles = 32`)** con física cinemática consciente de la capacidad y fusión de riesgos no compensatoria:

- **Estimación Cuantílica de Riesgo de Cola ($\text{CVaR}_{\alpha}$):** `GuardianNeuralPredictor` evalúa los cuantiles inferiores en el peor caso ($\alpha = 0.20$) en lugar de únicamente valores Q medios.
- **Estimación Física Cinemática y PAE ([`GuardianPhysicsEstimator`](../../src/safety/guardian_physics_estimator.py)):** Segmenta estrictamente los tripletes de sensores de aristas entrantes (`edge_feature_dim`), normaliza las colas frente a la capacidad vehicular física de la vía (`edge_capacities`), proyecta el crecimiento de saturación sobre el horizonte de despeje entre verdes $H = \text{yellow} + \text{all\_red}$ y consulta pronósticos contrafactuales del PAE (`decode_with_uncertainty` para `ADVANCE` vs `KEEP`).
- **Calibración Invariante a la Escala y Fusión Noisy-OR ([`GuardianRiskCalibrator`](../../src/safety/guardian_risk_calibrator.py)):** Calibra las dispersiones cuantílicas mediante regresión logística regularizada y ajuste de umbral por puntuación $F_2$ al graduarse de `CHILD`, combinando los riesgos físico, PAE y QR-D3QN mediante Noisy-OR no compensatorio ($1 - \prod_i (1 - c_i r_i)$) y un piso estricto de desbordamiento físico/PAE.
- **Entrenamiento Seguro en Sombra Solo en `CHILD` y Congelamiento ([`GuardianShadowTrainer`](../../src/safety/guardian_shadow_trainer.py) y [`GuardianCheckpointService`](../../src/safety/guardian_checkpoint_service.py)):** Entrena QR-D3QN *off-policy* exclusivamente durante `Maturity.CHILD` mientras las señales físicas siguen planes de tiempo fijo; al promocionar a `TEEN`/`ADULT`, ejecuta `finalize_child_calibration()` y `freeze_for_deployment()` (liberando `target_net`, `optimizer` y buffers PER) y persiste atómicamente `guardian_{tl_id}.pth`.

---

## 4. Watchdog de Procesos en Tiempo Real (`src/watchdog/`)

El microservicio `Watchdog` ([`src/watchdog/watchdog_process.py`](../../src/watchdog/watchdog_process.py) y [`src/watchdog/watchdog_logic.py`](../../src/watchdog/watchdog_logic.py)) monitorea la vitalidad de los 8 microservicios de CARINA:

- **Intervalo de Latido:** 100 ms vía la cola IPC `wd`.
- **Tiempo de Espera (Timeout) de Latido:** 5.0 segundos (período inicial de gracia: 10 segundos).
- **Mecanismo Fail-Safe:** Si el `AI_Process` o el `CentralController` se bloquean, caen o pierden latidos consecutivos:
  1. El Watchdog notifica a la bandeja de sistema (tray) de la interfaz de escritorio.
  2. Envía una señal a [`FailsafeManager`](../../src/controller/failsafe_manager.py) -> `HardwareGatewayCoordinator.on_failsafe_triggered()`, invocando `EmergencyReleaseControlAll()` en el gateway Go (liberando retenciones mientras mantiene los drivers SNMP y el receptor de traps listos para `resume_control` al recuperarse).
  3. Los controladores de tráfico físicos revierten de forma autónoma a sus planes locales de tiempo fijo o al modo de destello amarillo.
  4. Dispara el **Supervisor de Procesos F.E.N.I.X.** (`on_fenix_trigger` mediante la cola `fenix` y [`fenix_supervision_loop.py`](../../src/launcher/fenix_supervision_loop.py)) para iniciar la recuperación autónoma y la reconciliación de estado en lazo cerrado.
  5. **Watchdog de Permanencia de Preempción:** En paralelo, [`EVPPreemptionEngine`](../../src/evp/evp_preemption_engine.py) aplica un estricto timeout de permanencia máxima de preempción de $45.0\text{ s}$, liberando las retenciones arteriales si el checkout del vehículo se retrasa o se pierde.

---

## 5. Arquitectura de Auto-Recuperación ante Fallos F.E.N.I.X. (`src/fenix/`)

Para lograr resiliencia autónoma continua 24/7 sin intervención manual de operadores, CARINA implementa **F.E.N.I.X.** (Fault-tolerant Engine for Networked Intelligent eXecution) en [`src/fenix/`](../../src/fenix).

```text
        Watchdog Timeout / Caída de Proceso
                         │
                         ▼
              ┌─────────────────────┐
              │   FenixSupervisor   │ (Fachada Orquestadora)
              └──────────┬──────────┘
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
    ┌──────────────────┐     ┌──────────────────────┐
    │  RecoveryPolicy  │     │   SubprocessRunner   │
    │(Backoff Ventana) │     │(SIGTERM -> SIGKILL)  │
    └──────────────────┘     └──────────┬───────────┘
                                        │ Genera Nuevo Hijo
                                        ▼
                             ┌──────────────────────┐
                             │   StateReconciler    │
                             │(Modo FROZEN_SYNC)    │
                             └──────────┬───────────┘
                                        │ Espera Siguiente Transición (Cero Riesgo de Colisión)
                                        ▼
                             ┌──────────────────────┐
                             │    NORMAL (Activo)   │
                             └──────────────────────┘
```

### 5.1 Estados del Ciclo de Vida de F.E.N.I.X. (`FenixState`)
Definidos en [`src/fenix/protocols.py`](../../src/fenix/protocols.py):
- **`IDLE`**: Estado inicial antes de que comience la supervisión de procesos.
- **`NORMAL`**: El motor de IA supervisado opera nominalmente con plena autoridad de actuación.
- **`SUSPECT`**: Latido de proceso perdido o telemetría anómala detectada por el Watchdog.
- **`RESTARTING`**: Proceso zombi terminado; aguardando la ventana de retroceso (backoff) antes del reintento.
- **`FROZEN_SYNC`**: El proceso resucitado recibe telemetría en vivo, pero la inferencia neuronal y los comandos de actuación están estrictamente bloqueados (`is_inference_allowed = False`).
- **`SHADOW_WARMUP`**: Pasadas hacia adelante en segundo plano calientan las cachés de PyTorch y los embeddings de nodos GATv2.
- **`HANDOVER_PENDING`**: Esperando a que los controladores físicos transicionen a un límite de fase seguro.
- **`FAILSAFE_ACTIVE`**: Modo de respaldo donde los controladores físicos ejecutan planes autónomos de tiempo fijo mientras se completa la recuperación.
- **`HALTED`**: Cuota máxima de fallos excedida dentro de la ventana deslizante; bloquea el sistema en respaldo seguro y alerta a los operadores.

### 5.2 Política de Recuperación ante Fallos en Ventana Móvil (`WindowedCrashRecoveryPolicy`)
Ubicada en [`src/fenix/recovery_policy.py`](../../src/fenix/recovery_policy.py):
- Registra caídas del proceso dentro de una ventana de tiempo deslizante (predeterminado: $300\text{ s}$).
- Calcula el retroceso exponencial entre intentos de reinicio ($2.0\text{ s} \to 4.0\text{ s} \to 8.0\text{ s}$).
- Evita bucles de reinicio infinitos: si la tasa de caídas supera $M$ fallos (predeterminado: 5), transiciona a `HALTED`.

### 5.3 Traspaso en Límites Limpios (`StateReconciler` y `FenixStageDispatcher`)
Ubicado en [`src/fenix/state_reconciler.py`](../../src/fenix/state_reconciler.py) y [`src/controller/fenix_stage_dispatcher.py`](../../src/controller/fenix_stage_dispatcher.py):
- **Peligro de Colisión a Mitad de Fase:** Cuando el proceso de IA resucita, inyectar comandos a mitad de fase en una intersección física podría vulnerar intervalos de despeje o provocar cambios bruscos de señal.
- **Handshake de Campo en Lazo Cerrado:** `FenixStageDispatcher` consulta instantáneas recientes de los controladores desde el gateway Go, decodifica las etapas físicas activas mediante [`HardwareTelemetryDecoder`](../../src/drivers/hardware_telemetry_decoder.py) y reconcilia `StateReconciler` (`reconcile_with_field` mediante `fenix_post_resurrection`).
- **Desbloqueo en Transición de Fase:** El control neuronal solo se desbloquea (`on_stage_transition_detected`) cuando el controlador físico transiciona hacia un límite de etapa seguro, emitiendo `fenix_handover_complete` -> `HANDOVER_COMPLETE` para que `FenixSupervisor` confirme la resurrección y reanude los latidos (`resume_control`).

---

Para detalles de comunicación con controladores físicos, consulte [Controladores de Hardware](hardware_drivers.md).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
