# 🛡️ Arquitetura de Segurança, Firewall Guardian, Watchdog e F.E.N.I.X.

Este documento detalha o Firewall Neuro-Simbólico de Segurança em dois estágios do CARINA (`GuardianAgent` e `SafetyAuditor`), os mecanismos de fail-safe de hardware, o processo em tempo real `Watchdog` e o subsistema de auto-cura `F.E.N.I.X.`.

⬅️ [Central de Documentação](../README.md) | 🚦 [Controladores de Hardware](hardware_drivers.md) | 🧪 [Testes e Validação](testing.md)

---

## 1. Visão Geral do Firewall de Segurança em Dois Estágios

O CARINA desacopla completamente a segurança física pública do desempenho do aprendizado por reforço profundo. As políticas neurais sugerem ações, mas toda ação deve ser formalmente autorizada por duas barreiras intransponíveis:

```text
Ação Proposta pela IA ──> [1. Regras Simbólicas] ──> [2. Veto Neural de Spillback] ──> Atuação no Hardware
                                   │                              │
                                   ├── Veto (Verde Mín / Amarelo) └── Veto (Risco Spillback > 0.8)
                                   └── Força Manter Fase          └── Força Fase de Limpeza
```

---

## 2. Inventário de Regras de Veto Simbólico (`SafetyAuditor`)

O `SafetyAuditor` (`src/core/safety_auditor.py`) aplica restrições físicas que nunca podem ser relaxadas ou contornadas por otimização neural:

| ID Regra | Nome | Descrição da Restrição | Ação em Caso de Violação |
| :--- | :--- | :--- | :--- |
| **SR-01** | **Tempo de Verde Mínimo** | A fase verde ativa deve durar no mínimo $T_{min} = 7,0\text{ s}$ para escoamento de fila. | Força `ACTION_KEEP_PHASE`. |
| **SR-02** | **Tempo de Amarelo** | Qualquer mudança de fase exige um intervalo obrigatório de $3,0\text{ s}$ de amarelo. | Intercepta ação e injeta amarelo. |
| **SR-03** | **Intervalo de Vermelho Total** | Movimentos conflitantes exigem $2,0\text{ s}$ de vermelho total de segurança. | Injeta estágio de vermelho total. |
| **SR-04** | **Proteção de Pedestres** | Botoeiras ativadas garantem tempo ininterrupto de travessia segura de pedestres. | Bloqueia movimentos veiculares conflitantes. |
| **SR-05** | **Matriz de Conflitos** | Impede indicações simultâneas de verde em movimentos conflitantes da interseção. | Veto rígido; reverte para estágio seguro. |

---

## 3. Veto Neural de Spillback (`GuardianAgent`)

O **Guardian Agent** (`src/agents/guardian_agent.py`) opera uma rede Dueling Deep Q-Network sobre representações temporais TCN para estimar o **Risco de Enfileiramento Bloqueante (Spillback)** ($Q_{risk} \in [0.0, 1.0]$):
- **Limiar ($\tau_{risk}$):** $0,80$ (configurável em `config/settings.ini`).
- **Intervenção de Emergência:** Caso $Q(s, a_{proposto}) > 0,80$, a proposta da IA tática é vetada e o Guardian injeta uma fase de desobstrução imediata do corredor arterial antes que ocorra travamento em cadeia (*gridlock*).

---

## 4. Watchdog em Tempo Real (`src/watchdog/`)

O microprocesso `Watchdog` (`src/watchdog/watchdog_logic.py`) monitora a atividade vital dos 8 microsserviços do CARINA:
- **Intervalo de Heartbeat:** 100 ms via fila IPC `wd`.
- **Timeout de Heartbeat:** 5,0 segundos (período de tolerância inicial: 10 segundos).
- **Mecanismo de Fail-Safe:** Se o motor de IA ou o `CentralController` travar ou falhar:
  1. Notifica a bandeja do sistema (System Tray).
  2. Dispara sinal ao `FailsafeManager` para liberar as retenções físicas nos controladores.
  3. Controladores revertem autonomamente para seus planos locais em tempo integral.
  4. Aciona o **Supervisor de Processos F.E.N.I.X.** (`on_fenix_trigger`).

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

### 5.2 Handover Limpo em Fronteira de Estágio (`StateReconciler`)
Ao ressuscitar, injetar ações no meio de um estágio semafórico ativo causaria perigo de colisão ou quebra de entreverdes. O `StateReconciler` sincroniza com o estágio atual e só desbloqueia a atuação no momento exato em que o controlador físico avança para o próximo estágio natural.
