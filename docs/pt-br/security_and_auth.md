---
tags: [seguranca, autenticacao, bcrypt, usuarios, rbac, 12-factor]
aliases: [Segurança e Autenticação, Gestão de Usuários, Controle de Acesso, Security Manager]
---

# 🔐 Arquitetura de Segurança, Autenticação e Gestão de Usuários

Este documento especifica a arquitetura de segurança corporativa do CARINA localizada em `src/utils/security/` e `src/utils/security_manager.py`. Ele detalha a autenticação de usuários, hashing criptográfico de senhas, defesa contra força bruta, isolamento de esquemas de banco de dados e o paradigma de configuração 12-Factor App.

⬅️ [Central de Documentação](README.md) | 🗄️ [Banco de Dados e Schemas](database_and_schemas.md) | 🛠️ [Guias de Desenvolvimento](developer_guides.md)

---

## 1. Visão Geral da Arquitetura de Segurança

O CARINA gerencia infraestrutura municipal de segurança crítica para a vida humana. O acesso não autorizado ou a escalada indevida de privilégios poderia comprometer controladores de tráfego, causando colisões ou estrangulamento da cidade. Para proteger o ecossistema, o sistema impõe:

1. **Hashing Criptográfico Determinístico:** Algoritmo `bcrypt` com salt gerado aleatoriamente e fator de trabalho configurável.
2. **Defesa contra Ataques de Força Bruta (Lockdown):** Limitação de taxa (*rate limiting*) por IP e usuário com tempos de bloqueio exponenciais.
3. **Controle de Acesso Baseado em Papéis (RBAC):** Níveis granulares para `OPERATOR`, `ENGINEER` e `ADMIN`.
4. **Isolamento de Segredos (Padrão 12-Factor):** Desacoplamento absoluto de credenciais do código-fonte através do `.env`.

```text
 Cliente (Interface Flet / CLI)
          │
          ▼
 ┌──────────────────┐      Valida Credenciais          ┌──────────────────┐
 │   AuthService    │ ───────────────────────────────> │  Hasher Bcrypt   │
 └────────┬─────────┘                                  └──────────────────┘
          │
          ├──> [Checagem Força Bruta] ──> LockdownManager (Máx 5 tentativas, 15m lockout)
          │
          └──> [Busca de Usuário]     ──> UserRepository (PostgreSQL / SQLite Isolado)
```

---

## 2. Detalhamento dos Módulos Centrais

### 2.1 Criptografia e Hashing de Senhas (`hasher.py`)
Localizado em `src/utils/security/hasher.py`:
- Implementa hashing seguro com `bcrypt`.
- Geração automática de salt ($2^{12}$ rodadas por padrão).
- Comparação de strings em tempo constante para mitigar ataques de temporização (*timing attacks*).

### 2.2 Proteção contra Força Bruta (`lockdown.py`)
Localizado em `src/utils/security/lockdown.py`:
- Rastreia tentativas consecutivas de login inválidas por usuário e origem de rede.
- Bloqueia automaticamente a conta após 5 falhas consecutivas.
- Aplica um período de quarentena progressivo (padrão: 15 minutos).

### 2.3 Serviço e Repositório de Usuários (`user_service.py` e `user_repository.py`)
- `src/utils/security/user_repository.py`: Persistência direta em SQL de registros de contas, sessões ativas e logs de auditoria.
- `src/utils/security/migrator.py`: Criação e migração automática das tabelas `users` e `audit_log` em dialetos PostgreSQL e SQLite.

---

## 3. Configuração 12-Factor e Variáveis de Ambiente

Todas as credenciais sensíveis devem ser configuradas exclusivamente no `.env` e jamais comitadas no Git:

```bash
# --- Modo de Execução ---
# 'development': permite credenciais padrão de demonstração do GitHub (admin / Admin@Carina2026!).
# 'production': BLOQUEIA ESTRITAMENTE credenciais padrão; exige hashes seguros.
CARINA_ENV=production

# --- Inicialização do Superusuário ---
CARINA_SUPERUSER_USER=admin_traffic
CARINA_SUPERUSER_PASSWORD=SuaSenhaForteAqui!
CARINA_SUPERUSER_HASH=$2b$12$e8x...

# --- Credenciais de Banco de Dados ---
CARINA_DB_USER=carina_sec
CARINA_DB_PASSWORD=senha_segura_banco
CARINA_DB_HOST=127.0.0.1
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_DB_SCHEMA=schema_carina

# --- Segredo do Controlador Físico / SNMP ---
CARINA_SNMP_COMMUNITY=SuaStringCommunitySNMP

# --- Telemetria e Monitor Externo ---
CARINA_MQTT_HOST=127.0.0.1                     # Broker local ou https://tunnel.ngrok-free.dev/api/telemetry
CARINA_MQTT_PORT=1883
CARINA_MQTT_USER=
CARINA_MQTT_PASSWORD=
```

---

## 4. Diretrizes de Endurecimento (*Hardening*) em Produção

1. **Rotação de Community Strings SNMP:** Jamais utilize a string padrão `"public"` em controladores reais de rua.
2. **Restrição de Portas e Bindings gRPC:** Em produção, vincule as interfaces gRPC (`50051`) e WebSocket (`8080`) estritamente a VLANs privadas ou `127.0.0.1`, isoladas por proxies reversos com terminação TLS.
3. **Privilégio Mínimo de Banco de Dados:** Conceda ao usuário da aplicação apenas permissões `SELECT`, `INSERT` e `UPDATE` nos esquemas de operação.
4. **Fail-Safe Físico nos Controladores:** Assegure que os controladores reais de campo possuam plano de emergência por relógio interno (amarelo piscante) caso percam comunicação com o CARINA.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Segurança e Governança de Infraestrutura • CARINA CORE v1.2.0</i>
</div>
