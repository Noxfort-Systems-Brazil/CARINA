---
tags: [safety, watchdog, fenix, guardian, veto, failsafe, resilience, evp]
aliases: [Segurança e Watchdog, Firewall Guardian, Auto-Cura FENIX, Regras Simbólicas]
---

# 🛡️ Arquitetura de Segurança, Firewall Guardian, Watchdog e F.E.N.I.X.

Este documento detalha o Firewall Neuro-Simbólico de Segurança em múltiplos estágios do CARINA ([`GuardianAgent`](../../src/agents/guardian_agent.py) e [`SafetyAuditor`](../../src/core/safety_auditor.py)), a intercepção de prioridade de emergência (Regra SR-00), os mecanismos de fail-safe de hardware, o processo em tempo real `Watchdog` e o subsistema de auto-cura `F.E.N.I.X.`.

⬅️ Voltar ao [Portal Central MOC](carina_moc.md) | 🏛️ Ver [Arquitetura do Sistema](architecture.md) | 🚦 Ver [Controladores de Hardware](hardware_drivers.md) | 🚑 Ver [Preempção EVP](evp_and_preemption.md)

---

## 1. Visão Geral do Firewall de Segurança

O CARINA desacopla completamente a segurança pública e viária do aprendizado por reforço profundo. As políticas neurais sugerem ações, mas toda ação passa por mascaramento físico de logits e verificação de segurança em múltiplos estágios antes do despacho para o hardware:

```text
Estado + Latente PAE ──> [PhysicalActionMasker] ──> [ActionVetoResolver] ──> Atuação
                          (Logits Entreverde/MinG)   ├── 0. Intercepção EVP (SR-00)
                                                     ├── 1. Regras Simbólicas (SR-01..SR-06)
                                                     └── 2. Veto de Risco QR-D3QN + Noisy-OR
```

- [`PhysicalActionMasker`](../../src/engine/physical_action_masker.py): Restringe os logits FP32 de `ActorCriticNet` antes da amostragem, proibindo trocas prematuras durante intervalos de limpeza amarelo/vermelho total ou abaixo do verde mínimo, e forçando transições acima do verde máximo.
- [`ActionVetoResolver`](../../src/engine/action_veto_resolver.py): Orquestra sobrescritas de preempção EVP (`SR-00`) e vetos de spillback do `GuardianAgent` (`ACTION_KEEP_STAGE`) no pipeline de execução de passo.

---

## 2. Inventário de Regras de Veto Simbólico (`SafetyAuditor`)

O `SafetyAuditor` ([`src/core/safety_auditor.py`](../../src/core/safety_auditor.py)) e o `GuardianSymbolicAuditor` ([`src/safety/guardian_symbolic_auditor.py`](../../src/safety/guardian_symbolic_auditor.py)) aplicam restrições físicas e legais que nunca podem ser relaxadas ou contornadas por otimização de IA:

| ID Regra | Nome | Descrição da Restrição | Ação em Caso de Violação |
| :--- | :--- | :--- | :--- |
| **SR-00** | **Preempção de Emergência (EVP)** | Prioridade de passagem a viaturas com sirene ativa no gate ($60\text{--}160\text{ m}$) segundo Art. 29 CTB. | Intercepta IA; força verde de socorro respeitando amarelo e all-red. |
| **SR-01** | **Tempo de Verde Mínimo** | A fase verde ativa deve durar no mínimo $T_{min} = 7,0\text{ s}$ para escoamento seguro de fila. | Força `ACTION_KEEP_PHASE`. |
| **SR-02** | **Tempo de Amarelo** | Qualquer mudança de fase exige um intervalo regulamentar obrigatório de $3,0\text{ s}$ de amarelo. | Intercepta ação e injeta amarelo. |
| **SR-03** | **Intervalo de Vermelho Total** | Movimentos conflitantes exigem $2,0\text{ s}$ de vermelho total de segurança (*all-red*). | Injeta estágio de vermelho total. |
| **SR-04** | **Tempo de Vermelho Mínimo** | Movimentos não atendidos devem cumprir intervalo mínimo de retenção antes de serem chamados. | Inibe reativação prematura da fase. |
| **SR-05** | **Teto de Verde Máximo (Anti-Starvation)** | Impede que uma fase monopolize o verde além do teto máximo havendo fila em aproximações concorrentes. | Força encerramento da fase e transição para demanda retida. |
| **SR-06** | **Matriz de Conflitos e Ghost Green** | Impede indicações simultâneas de verde em movimentos conflitantes ou espúrios da interseção. | Veto rígido; reverte para estágio seguro. |

---

## 3. Veto Neural de Spillback Calibrado (`GuardianAgent` & `src/safety/`)

O **Guardian Agent** ([`src/agents/guardian_agent.py`](../../src/agents/guardian_agent.py)) integra uma rede **Distributional Quantile-Regression Dueling Double DQN (`D3QN_TCN`, `num_quantiles = 32`)** com física cinemática consciente de capacidade e fusão de risco não-compensatória:

- **Estimação Quantílica de Risco de Cauda ($\text{CVaR}_{\alpha}$):** `GuardianNeuralPredictor` avalia os piores quantis inferiores ($\alpha = 0.20$) em vez de depender apenas dos Q-values médios.
- **Estimação Física Cinemática & PAE ([`GuardianPhysicsEstimator`](../../src/safety/guardian_physics_estimator.py)):** Fatiamento estrito de tripletos de sensores de vias de entrada (`edge_feature_dim`), normaliza filas pelas capacidades físicas de veículos das vias (`edge_capacities`), projeta o crescimento de saturação ao longo do horizonte de entreverde $H = \text{yellow} + \text{all\_red}$ e consulta previsões contrafactuais do PAE (`decode_with_uncertainty` para `ADVANCE` vs `KEEP`).
- **Calibração Invariante à Escala & Fusão Noisy-OR ([`GuardianRiskCalibrator`](../../src/safety/guardian_risk_calibrator.py)):** Calibra a dispersão dos quantis via regressão logística regularizada e ajuste de limiar por $F_2$-score na graduação de `CHILD`, combinando os riscos físico, PAE e QR-D3QN com Noisy-OR não-compensatório ($1 - \prod_i (1 - c_i r_i)$) e um piso rígido de spillback físico/PAE.
- **Treinamento em Sombra Seguro Apenas na Fase `CHILD` & Congelamento ([`GuardianShadowTrainer`](../../src/safety/guardian_shadow_trainer.py) & [`GuardianCheckpointService`](../../src/safety/guardian_checkpoint_service.py)):** Treina o QR-D3QN off-policy exclusivamente durante `Maturity.CHILD` enquanto os semáforos físicos seguem planos de tempo fixo; na promoção para `TEEN`/`ADULT`, executa `finalize_child_calibration()` e `freeze_for_deployment()` (liberando `target_net`, `optimizer` e buffers PER) e persiste atomicamente `guardian_{tl_id}.pth`.

---

## 4. Watchdog em Tempo Real (`src/watchdog/`)

O microprocesso `Watchdog` ([`src/watchdog/watchdog_process.py`](../../src/watchdog/watchdog_process.py) e [`src/watchdog/watchdog_logic.py`](../../src/watchdog/watchdog_logic.py)) monitora a atividade vital dos 8 microsserviços do CARINA:
- **Intervalo de Heartbeat:** 100 ms via fila IPC `wd`.
- **Timeout de Heartbeat:** 5,0 segundos (período de tolerância inicial: 10 segundos).
- **Mecanismo de Fail-Safe:** Se o `AI_Process` ou o `CentralController` travar ou falhar:
  1. Notifica a bandeja do sistema (System Tray).
  2. Dispara sinal para [`FailsafeManager`](../../src/controller/failsafe_manager.py) -> `HardwareGatewayCoordinator.on_failsafe_triggered()`, invocando `EmergencyReleaseControlAll()` no gateway Go (liberando as retenções de fase enquanto mantém drivers SNMP e trap listener prontos para `resume_control` na recuperação).
  3. Controladores revertem autonomamente para seus planos locais em tempo fixo ou amarelo piscante.
  4. Aciona o **Supervisor de Processos F.E.N.I.X.** (`on_fenix_trigger` via fila `fenix` e [`fenix_supervision_loop.py`](../../src/launcher/fenix_supervision_loop.py)) para iniciar a recuperação autônoma e reconciliação de estado em malha fechada.
  5. **Dwell Watchdog de Preempção ($45,0\text{ s}$):** Em paralelo, [`EVPPreemptionEngine`](../../src/evp/evp_preemption_engine.py) impõe um timeout máximo estrito de $45,0\text{ s}$ de preempção, liberando retenções arteriais caso o checkout da viatura atrase ou falhe.

---

## 5. Arquitetura de Auto-Cura F.E.N.I.X. (`src/fenix/`)

O subsistema **F.E.N.I.X.** (Fault-tolerant Engine for Networked Intelligent eXecution) provê recuperação autônoma contínua 24/7 sem necessidade de operador humano.

```text
       Timeout do Watchdog / Queda de Processo
                         │
                         ▼
              ┌─────────────────────┐
              │   FenixSupervisor   │ (Fachada Orquestradora)
              └──────────┬──────────┘
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
    ┌──────────────────┐     ┌──────────────────────┐
    │  RecoveryPolicy  │     │   SubprocessRunner   │
    │(Backoff Janela)  │     │(SIGTERM -> SIGKILL)  │
    └──────────────────┘     └──────────┬───────────┘
                                        │ Spawna Novo Processo
                                        ▼
                             ┌──────────────────────┐
                             │   StateReconciler    │
                             │ (Modo FROZEN_SYNC)   │
                             └──────────┬───────────┘
                                        │ Aguarda Próxima Transição
                                        ▼
                             ┌──────────────────────┐
                             │    NORMAL (Ativo)    │
                             └──────────────────────┘
```

### 5.1 Estados do Ciclo de Vida (`FenixState`)
- **`IDLE`**: Estado inicial antes do início da supervisão.
- **`NORMAL`**: Processo de IA operando nominalmente com autoridade de comando.
- **`SUSPECT`**: Falha momentânea de heartbeat identificada pelo Watchdog.
- **`RESTARTING`**: Processo zumbi encerrado; aguardando período de backoff.
- **`FROZEN_SYNC`**: Processo ressuscitado recebe telemetria viva, mas inferência e atuação estão estritamente bloqueadas (`is_inference_allowed = False`).
- **`SHADOW_WARMUP`**: Aquecimento de caches do PyTorch e tensores GATv2 em background.
- **`HANDOVER_PENDING`**: Aguardando fronteira de estágio segura dos controladores de rua.
- **`FAILSAFE_ACTIVE`**: Controladores operando em plano local fixo durante a recuperação.
- **`HALTED`**: Limite máximo de reinícios excedido na janela deslizante (alerta crítico aos operadores).

### 5.2 Handover Limpo em Fronteira de Estágio (`StateReconciler` & `FenixStageDispatcher`)
Localizado em [`src/fenix/state_reconciler.py`](../../src/fenix/state_reconciler.py) e [`src/controller/fenix_stage_dispatcher.py`](../../src/controller/fenix_stage_dispatcher.py):
- **Risco de Colisão em Meio de Estágio:** Ao ressuscitar o processo de IA, injetar ações no meio de um estágio semafórico ativo violaria intervalos de entreverdes ou causaria trocas abruptas nos semáforos.
- **Handshake de Campo em Malha Fechada:** `FenixStageDispatcher` consulta snapshots atualizados dos controladores no gateway Go, decodifica os estágios ativos em campo via [`HardwareTelemetryDecoder`](../../src/drivers/hardware_telemetry_decoder.py) e reconcilia o `StateReconciler` (`reconcile_with_field` via `fenix_post_resurrection`).
- **Desbloqueio na Transição de Fase:** O controle neural só é desbloqueado (`on_stage_transition_detected`) quando o controlador físico avança para uma fronteira segura de estágio, emitindo `fenix_handover_complete` -> `HANDOVER_COMPLETE` para que o `FenixSupervisor` confirme a ressurreição e retome os heartbeats (`resume_control`).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Mobilidade Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
