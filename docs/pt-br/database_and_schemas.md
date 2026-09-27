# 🗄️ Arquitetura de Banco de Dados e Esquemas Relacionais

Este documento detalha a camada de persistência do CARINA, a arquitetura de pooling de conexões, a ingestão assíncrona não-bloqueante de telemetria (`StepDecisionWorker`), os segredos 12-Factor App e os esquemas relacionais no PostgreSQL e SQLite.

⬅️ [Central de Documentação](../README.md) | 🏛️ [Arquitetura](architecture.md) | 🛡️ [Segurança e Watchdog](safety_and_watchdog.md)

---

## 1. Arquitetura Não-Bloqueante Assíncrona

Para evitar que comandos `INSERT` no banco bloqueiem o ciclo de inferência de sub-milissegundo da IA ($< 1\text{ ms}$), todo registro é enfileirado na memória RAM e descarregado em lote por workers de background:
- **Sobrecarga de Ingestão:** $< 0,001\text{ ms}$ para push na fila RAM.
- **Tamanho do Lote:** 50 registros ou intervalo máximo de 3,0 segundos.
- **Compressão Delta:** Agrupa estados idênticos consecutivos, alcançando **97,9% de redução no volume de armazenamento em disco** (~380 MB/dia para 200 cruzamentos).

---

## 2. Esquemas das Tabelas Relacionais

### 2.1 Tabela: `step_decisions`
Registra decisões dos agentes, vetos do Guardian e cronômetros com enums Smallint compactos de 1 byte.

```sql
CREATE TABLE IF NOT EXISTS step_decisions (
    id BIGSERIAL PRIMARY KEY,
    simulation_time REAL NOT NULL,
    step_number INTEGER NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    maturity_stage SMALLINT NOT NULL DEFAULT 2,     -- 0=CHILD, 1=TEEN, 2=ADULT
    suggested_action SMALLINT NOT NULL DEFAULT 0,   -- 0=KEEP, 1=CHANGE, 2=OVERRIDE
    final_decision SMALLINT NOT NULL DEFAULT 0,     -- 0=APPROVED, 1=DENIED (VETOED)
    veto_reason_code SMALLINT NOT NULL DEFAULT 0,   -- 0=NONE, 1=MIN_GREEN, 2=YELLOW, 3=SPILLBACK, 4=GRIDLOCK
    step_count INTEGER NOT NULL DEFAULT 1,          -- Contador de Compressão Delta
    total_step_time_ms REAL,
    guardian_time_ms REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 Tabela: `synapse_fluid_dynamics`
Armazena a dinâmica de fluidos de tráfego de alta frequência por segmento de via (densidade, velocidade, extensão de filas).

### 2.3 Tabela: `hardware_controller_connections`
Armazena endereços IP, portas, protocolos (`NTCIP_1202`, `UTMC`, `SNMP`) e status dos controladores físicos de tráfego.

### 2.4 Tabela: `users` (Camada de Segurança)
Gerenciada por `src/utils/security/user_repository.py` com hashes bcrypt salgados e proteção de lockout por tentativas falhas.
