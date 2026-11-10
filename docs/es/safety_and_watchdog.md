---
tags: [seguridad, guardian, watchdog, veto, failsafe, neuro-simbolico]
aliases: [Arquitectura de Seguridad, Veto de Guardian, Sistema Watchdog, Auditor de Seguridad]
---

# 🛡️ Arquitectura de Seguridad, Firewall de Guardian y Watchdog

Este documento detalla el Firewall de Seguridad Neuro-Simbólico de doble etapa de CARINA ([`GuardianAgent`](../../src/agents/guardian_agent.py) y [`SafetyAuditor`](../../src/core/safety_auditor.py)), los mecanismos de seguridad fail-safe de hardware y el proceso determinista en tiempo real [`Watchdog`](../../src/watchdog/watchdog_process.py).

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🚨 Ver [Preempción EVP](evp_and_preemption.md) | 🚦 Ver [Controladores de Hardware](hardware_drivers.md) | 🧠 Ver [Formulaciones Neuronales](research_notes.md) | 🧪 Ver [Pruebas y Validación](testing.md)

---

## 1. Visión General del Firewall de Seguridad en Doble Etapa

CARINA desacopla completamente la seguridad pública física del rendimiento del aprendizaje por refuerzo profundo. Las políticas neuronales pueden proponer acciones, pero todas las acciones deben ser formalmente validadas y autorizadas a través de un firewall de seguridad antes de su despacho al hardware físico:

```text
Acción de Fase Propuesta ──> [0. Interceptación EVP] ──> [1. Reglas Simbólicas] ──> [2. Veto Neuronal] ──> Actuación
                                     │                            │                        │
                                     ├── Corredor de Emergencia   ├── Verde Mín / Amarillo └── Spillback (Q > 0.8)
                                     └── Despeje Obligatorio      └── Veto de Conflicto    └── Desahogo Emergencia
```

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

## 3. Veto Neuronal contra Desbordamiento / Spillback (`GuardianAgent`)

El **Guardian Agent** ([`src/agents/guardian_agent.py`](../../src/agents/guardian_agent.py)) ejecuta una red neuronal Dueling Deep Q-Network sobre representaciones temporales TCN para estimar el **Riesgo de Desbordamiento / Spillback** ($Q_{risk} \in [0.0, 1.0]$):

- **Umbral ($\tau_{risk}$):** $0.80$ (configurable en `config/settings.ini`).
- **Anulación de Emergencia:** Si $Q(s, a_{propuesta}) > 0.80$, la propuesta del agente táctico es vetada. El Guardian inyecta una fase de despeje de emergencia para desahogar el enlace arterial congestionado antes de que ocurra un bloqueo aguas arriba.

---

## 4. Watchdog de Procesos en Tiempo Real (`src/watchdog/`)

El microservicio `Watchdog` ([`src/watchdog/watchdog_process.py`](../../src/watchdog/watchdog_process.py) y [`src/watchdog/watchdog_logic.py`](../../src/watchdog/watchdog_logic.py)) monitorea la vitalidad de los 8 microservicios de CARINA:

- **Intervalo de Latido:** 100 ms vía la cola IPC `wd`.
- **Tiempo de Espera (Timeout) de Latido:** 5.0 segundos (período inicial de gracia: 10 segundos).
- **Mecanismo Fail-Safe:** Si el `AI_Process` o el `CentralController` se bloquean, caen o pierden latidos consecutivos:
  1. El Watchdog notifica a la bandeja de sistema (tray) de la interfaz de escritorio.
  2. Envía inmediatamente una señal al [`FailsafeManager`](../../src/controller/failsafe_manager.py) para liberar las retenciones de fase en los controladores físicos.
  3. Los controladores de tráfico físicos revierten de forma autónoma a sus planes locales de tiempo fijo o al modo de destello amarillo.
  4. Dispara el **Supervisor de Procesos F.E.N.I.X.** (`on_fenix_trigger`) para iniciar la recuperación autónoma y la reconciliación del estado.
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

### 5.3 Traspaso en Límites Limpios (`StateReconciler`)
Ubicado en [`src/fenix/state_reconciler.py`](../../src/fenix/state_reconciler.py):
- **Peligro de Colisión a Mitad de Fase:** Cuando el proceso de IA resucita, inyectar comandos a mitad de fase en una intersección física podría vulnerar intervalos de despeje o provocar cambios bruscos de señal.
- **Handshake de Cero Riesgo:** El reconciliador interroga las fases actuales de los controladores físicos (`reconcile_with_field`).
- **Desbloqueo en Transición de Fase:** El control neuronal solo se desbloquea (`on_stage_transition_detected`) cuando el controlador físico transiciona naturalmente a su siguiente fase local, garantizando una reanudación suave y sin riesgo de colisión.

---

Para detalles de comunicación con controladores físicos, consulte [Controladores de Hardware](hardware_drivers.md).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
