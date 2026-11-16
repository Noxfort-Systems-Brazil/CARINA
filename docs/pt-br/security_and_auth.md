---
tags: [seguranca, autenticacao, pbkdf2, usuarios, rbac, 12-factor]
aliases: [Segurança e Autenticação, Gestão de Usuários, Controle de Acesso, Security Manager]
---

# 🔐 Arquitetura de Segurança, Autenticação e Gestão de Usuários

Este documento especifica a arquitetura de segurança corporativa do CARINA localizada em [`src/security/`](../../src/security). Ele detalha a autenticação de usuários, hashing criptográfico de senhas, defesa contra força bruta, armazenamento híbrido JSON/SQL, criptografia de campos e o paradigma de configuração 12-Factor App.

⬅️ [Central de Documentação](README.md) | 🗄️ [Banco de Dados e Schemas](database_and_schemas.md) | 🛠️ [Guias de Desenvolvimento](developer_guides.md)

---

## 1. Visão Geral da Arquitetura de Segurança

O CARINA gerencia infraestrutura municipal de segurança crítica para a vida humana. O acesso não autorizado ou a escalada indevida de privilégios poderia comprometer controladores de tráfego, causando colisões ou estrangulamento da cidade. Para proteger o ecossistema, o subsistema de segurança adota uma arquitetura limpa (Clean Architecture / DDD):

1. **Hashing Criptográfico Determinístico:** Algoritmo `PBKDF2PasswordHasher` baseado em PBKDF2 HMAC SHA-256 com 100.000 iterações e salt aleatório de 16 bytes (`os.urandom(16)`), com suporte a `Argon2PasswordHasher`. O mecanismo de fallback para senha mestre utiliza comparação de digest SHA-256 em tempo constante (`hmac.compare_digest`).
2. **Defesa contra Força Bruta (Lockdown):** Rastreamento de tentativas com [`FileLockdownManager`](../../src/security/lockdown_manager.py) e [`LockdownEnforcer`](../../src/security/lockdown_enforcer.py). Após 3 falhas consecutivas (`MAX_FAILED_ATTEMPTS = 3`), é gerado o arquivo `lockdown.flag` e atualizado `system_security_state`, bloqueando novas tentativas de login padrão até o desbloqueio por credencial `SUPERUSER` ou `MASTER`.
3. **Controle de Acesso Baseado em Papéis (RBAC):** Níveis binários estritos:
   - `OPERATOR`: Monitoramento de interseções, acionamento manual de fases, inspeção de telemetria e diagnósticos de leitura.
   - `SUPERUSER`: Acesso administrativo pleno, criação/remoção de contas, alteração de diretrizes e liberação de lockdown.
4. **Armazenamento Híbrido de Credenciais (Offline-First e Relacional):** Suporta armazenamento local desacoplado (`security.json` via [`JsonUserRepository`](../../src/security/json_user_repo.py)), persistência em banco relacional (`system_users` e `system_security_state` via [`SqlUserRepository`](../../src/security/sql_user_repo.py)) e sincronização resiliente via [`HybridUserRepository`](../../src/security/hybrid_user_repo.py).
5. **Criptografia de Campos e Auditoria:** Credenciais e tokens sensíveis protegidos em repouso por [`FieldEncryptor`](../../src/security/field_encryptor.py) e trilhas gravadas via [`AuditLogger`](../../src/security/audit_logger.py) (com escritas transacionais em pool via `db_transaction`).
6. **Endurecimento (*Hardening*) de Transporte, Endpoints e SQL:**
   - **Segurança Synapse gRPC (`:50051`) ([`grpc_security.py`](../../src/communication/grpc_security.py)):** Suporta TLS/mTLS (`grpc.ssl_server_credentials`) e validação em tempo constante de Bearer / `x-carina-token` (`BearerTokenServerInterceptor`).
   - **Web Gateway Fail-Closed & Auth EVP ([`auth.go`](../../src_go/web_gateway/auth.go), [`evp_http_server.go`](../../src_go/evp_go/evp_http_server.go)):** `gateway_enabled` assume `False` por padrão (retornando `503 Service Unavailable` quando inativo), impõe verificação de tokens em tempo constante (`subtle.ConstantTimeCompare`), CORS explícito (`CARINA_CCO_ALLOWED_ORIGIN`) e terminação HTTPS/TLS.
   - **Pinning de Certificado SHA-256 ([`cco_tls_transport.py`](../../src/sds/cco_tls_transport.py)):** `PinnedHTTPSConnection` verifica a confiança na CA e opcionalmente fixa o resumo SHA-256 do certificado folha quando o SDS envia `/cco/broadcast`.
   - **Intervalos SQL Parametrizados:** Consultas PostgreSQL usam `make_interval(...)` em vez de interpolação de strings.
7. **Isolamento de Segredos (Padrão 12-Factor):** Desacoplamento absoluto de credenciais do código-fonte através do `.env`.

```text
 Cliente (Interface Desktop / CCO / CLI)
          │
          ▼
 ┌──────────────────────┐      Valida Credenciais          ┌────────────────────────┐
 │ AuthenticateService  │ ───────────────────────────────> │  PBKDF2PasswordHasher  │
 └──────────┬───────────┘                                  │      (crypto.py)       │
            │                                              └────────────────────────┘
            ├──> [Checagem Força Bruta] ──> LockdownManager (Máx 3 tentativas -> lockdown.flag)
            │
            └──> [Busca de Usuário]     ──> HybridUserRepository
                                               ├── JsonUserRepository (security.json offline)
                                               └── SqlUserRepository (tabela system_users)
```

---

## 2. Detalhamento dos Módulos Centrais (`src/security/`)

### 2.1 Criptografia e Hashing de Senhas (`crypto.py`)
Localizado em [`src/security/crypto.py`](../../src/security/crypto.py):
- Implementa `PBKDF2PasswordHasher` com `hashlib.pbkdf2_hmac("sha256", ..., iterations=100000)`.
- Geração automática de salt criptográfico seguro de 16 bytes.
- Formato de serialização padronizado: `salt_hex:key_hex`.
- Comparação de strings em tempo constante com `hmac.compare_digest` para mitigar ataques de temporização (*timing attacks*).
- Autenticação de contingência para senha mestre com digest SHA-256 via `CARINA_SUPERUSER_HASH` e validação com `MasterCredentialValidator`.

### 2.2 Proteção contra Força Bruta e Bloqueio (`lockdown_manager.py` e `lockdown_enforcer.py`)
Localizado em [`src/security/lockdown_manager.py`](../../src/security/lockdown_manager.py) e [`src/security/lockdown_enforcer.py`](../../src/security/lockdown_enforcer.py):
- Rastreia tentativas consecutivas de login inválidas em memória e disco (`JsonAttemptStore`, `MemoryAttemptStore`).
- Bloqueia automaticamente o sistema após 3 falhas consecutivas (`MAX_FAILED_ATTEMPTS = 3`).
- Grava um arquivo persistente `lockdown.flag` contendo carimbo temporal e justificativa de segurança.
- Dispara `LockdownActiveError` em todas as tentativas normais enquanto o arquivo persistir.
- O bloqueio só pode ser cancelado via intervenção de um `SUPERUSER` ou credencial mestra.

### 2.3 Serviço e Repositórios de Usuários (`authenticate_service.py`, `account_manager.py`, `json_user_repo.py`, `sql_user_repo.py`)
- [`src/security/authenticate_service.py`](../../src/security/authenticate_service.py): Serviço de autenticação central (`AuthenticateService` / alias `AuthService`).
- [`src/security/account_manager.py`](../../src/security/account_manager.py): Gerenciamento do ciclo de vida de contas de usuários (`UserAccountManager` / alias `UserManagementService`).
- [`src/security/password_policy.py`](../../src/security/password_policy.py): Validação de regras e complexidade de senhas (`ModernPasswordPolicy` e `PasswordValidator`).
- [`src/security/json_user_repo.py`](../../src/security/json_user_repo.py): Implementa `JsonUserRepository`, persistindo credenciais e papéis no arquivo `security.json`.
- [`src/security/sql_user_repo.py`](../../src/security/sql_user_repo.py): Implementa `SqlUserRepository`, gerenciando persistência SQL em PostgreSQL e SQLite na tabela `system_users`.
- [`src/security/hybrid_user_repo.py`](../../src/security/hybrid_user_repo.py): Implementa `HybridUserRepository`, promovendo sincronização resiliente entre armazenamento SQL e arquivo JSON local.
- [`src/security/field_encryptor.py`](../../src/security/field_encryptor.py): Criptografia de campos e tokens via chave simétrica segura (Fernet/AES).
- [`src/security/audit_logger.py`](../../src/security/audit_logger.py): Registro imutável de eventos de auditoria e segurança.

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
CARINA_SUPERUSER_HASH=5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8

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

# --- Segurança de Transporte do Remote Gateway & CCO/EVP ---
CARINA_GATEWAY_ENABLED=False                   # Fail-closed até que os tokens sejam configurados
CARINA_EVP_AUTH_TOKEN=
CARINA_CCO_AUTH_TOKEN=
CARINA_CCO_ALLOWED_ORIGIN=                     # Origem CORS explícita para endpoints do CCO
CARINA_GATEWAY_TLS_CERT=
CARINA_GATEWAY_TLS_KEY=
CARINA_GATEWAY_TLS_CA=
CARINA_GATEWAY_TLS_SERVER_NAME=

# --- Segurança do Synapse gRPC (:50051) ---
CARINA_GRPC_AUTH_TOKEN=
CARINA_GRPC_TLS_ENABLED=False
CARINA_GRPC_TLS_CERT=
CARINA_GRPC_TLS_KEY=
CARINA_GRPC_TLS_CA=
CARINA_GRPC_REQUIRE_CLIENT_CERT=False
```

---

## 4. Diretrizes de Endurecimento (*Hardening*) em Produção

1. **Rotação de Community Strings SNMP & Uso de SNMPv3:** Evite a string padrão `"public"` em produção; dê preferência a **SNMPv3 `AuthPriv`** (`SHA256` + `AES`) configurado via `snmp_config` em `hardware_controller_connections`.
2. **Habilitação de TLS + Tokens no gRPC e Web Gateway:** Nunca altere `CARINA_GATEWAY_ENABLED=True` em produção sem definir `CARINA_EVP_AUTH_TOKEN`, `CARINA_CCO_AUTH_TOKEN`, `CARINA_CCO_ALLOWED_ORIGIN` e `CARINA_GRPC_AUTH_TOKEN` fortes além de certificados TLS.
3. **Privilégio Mínimo de Banco de Dados:** Conceda ao usuário da aplicação apenas permissões `SELECT`, `INSERT`, `UPDATE` e `DELETE` (para expurgos de retenção) nos esquemas de operação.
4. **Fail-Safe Físico nos Controladores:** Assegure que os controladores reais de campo possuam plano de emergência por relógio interno (amarelo piscante) caso percam comunicação com o CARINA.
5. **Permissões Restritas no Cofre JSON:** Defina permissões estritas no arquivo `security.json` e `lockdown.flag` acessíveis unicamente pelo usuário de serviço (`chmod 600`).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Segurança e Governança de Infraestrutura • CARINA CORE v1.2.0</i>
</div>
