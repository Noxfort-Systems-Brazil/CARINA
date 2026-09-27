# 🛡️ Seguridad Neuro-Simbólica, Watchdog y F.E.N.I.X.

Este documento especifica el cortafuegos de seguridad de doble etapa de CARINA (`SafetyAuditor` simbólico y `GuardianAgent` neural), el proceso de supervisión en tiempo real `Watchdog` y el subsistema de auto-sanación `F.E.N.I.X.`.

⬅️ [Centro de Documentación](../README.md) | 🚦 [Controladores de Hardware](hardware_drivers.md) | 🧪 [Pruebas](testing.md)

---

## 1. Cortafuegos de Seguridad en Dos Etapas

```text
Acción Propuesta ──> [1. Reglas Simbólicas] ──> [2. Veto Neural Spillback] ──> Actuación en Hardware
                              │                               │
                              ├── Veto (Verde Mín / Ámbar)    └── Veto (Riesgo > 0.80)
                              └── Forzar Mantener Fase        └── Forzar Fase de Despeje
```

---

## 2. Reglas Simbólicas Inviolables (`SafetyAuditor`)

| Regla | Nombre | Restricción Física | Acción ante Violación |
| :--- | :--- | :--- | :--- |
| **SR-01** | **Verde Mínimo** | La fase verde debe permanecer al menos $7.0\text{ s}$ para evacuar vehículos en cola. | Forzar mantener fase. |
| **SR-02** | **Despeje Ámbar** | Toda transición exige un intervalo obligatorio de $3.0\text{ s}$ de ámbar. | Interceptar e inyectar ámbar. |
| **SR-03** | **Todo Rojo** | Movimientos en conflicto exigen $2.0\text{ s}$ de todo rojo de seguridad. | Inyectar intervalo todo rojo. |
| **SR-04** | **Protección Peatonal** | Botoneras peatonales activadas garantizan tiempo ininterrumpido de cruce. | Bloquear movimientos vehiculares. |
| **SR-05** | **Matriz de Conflictos**| Impide fases verdes simultáneas en movimientos geométricamente cruzados. | Veto estricto; revertir a fase segura. |

---

## 3. Veto Neural por Desbordamiento (`GuardianAgent`)
Red Dueling D3QN que calcula en tiempo real el riesgo de congestión arterial bloqueante ($Q_{risk} \in [0.0, 1.0]$). Si $Q_{risk} > 0.80$, la acción propuesta se anula y se inyecta una fase de despeje de emergencia.

---

## 4. Proceso Watchdog y Auto-Recuperación F.E.N.I.X.
- **Watchdog:** Heartbeats de 100 ms via IPC; si se pierde comunicación por más de 5.0 s, libera retenciones en semáforos y activa `on_fenix_trigger`.
- **F.E.N.I.X. (`src/fenix/`):** Detiene el subproceso colgado, aplica backoff exponencial por ventana de tiempo (`WindowedCrashRecoveryPolicy`), arranca una nueva instancia en modo `FROZEN_SYNC` y sincroniza el traspaso de control únicamente en fronteras naturales de fase (`StateReconciler`).
