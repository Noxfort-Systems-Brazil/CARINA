---
tags: [security, auth, pbkdf2, users, rbac, 12-factor]
aliases: [Security & Authentication, User Management, Access Control, Security Manager]
---

# 🔐 Security Architecture, Authentication & User Management

This document specifies CARINA's enterprise security architecture located in [`src/security/`](../src/security). It details user authentication, cryptographic password hashing, brute-force defense, hybrid JSON/SQL storage, field encryption, and the 12-Factor App configuration paradigm.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🗄️ See [Database & Schemas](DATABASE_AND_SCHEMAS.md) | 🛠️ See [Developer Guides](DEVELOPER_GUIDES.md)

---

## 1. Security Architecture Overview

CARINA governs safety-critical municipal infrastructure. Unauthorized access or privilege escalation could compromise traffic light controllers, leading to collisions or gridlock. To protect against these threats, the security subsystem enforces a Clean Architecture / DDD design:

1. **Deterministic Password Hashing:** Salted `PBKDF2PasswordHasher` utilizing PBKDF2 HMAC SHA-256 with 100,000 iterations and 16-byte cryptographically secure random salts (with `Argon2PasswordHasher` support). Master fallback verification uses SHA-256 hex digest comparison in constant time (`hmac.compare_digest`).
2. **Brute-Force Defense (Lockdown Engine):** Persistent tracking of failed authentication attempts via [`FileLockdownManager`](../src/security/lockdown_manager.py) and [`LockdownEnforcer`](../src/security/lockdown_enforcer.py). After 3 consecutive failed attempts (`MAX_FAILED_ATTEMPTS = 3`), the engine creates a `lockdown.flag` file and updates `system_security_state`, preventing further standard logins until unlocked by a `SUPERUSER` or `MASTER` override.
3. **Role-Based Access Control (RBAC):** Strict binary privilege tiers:
   - `OPERATOR`: Routine intersection monitoring, manual signal phase calls, telemetry inspection, and read-only diagnostics.
   - `SUPERUSER`: Full administrative access, user creation/deletion, policy alteration, and lockdown clearing.
4. **Hybrid Credential Storage (Offline-First & Relational):** Supports decoupled local JSON storage (`security.json` via [`JsonUserRepository`](../src/security/json_user_repo.py)), relational database persistence (`system_users` and `system_security_state` tables via [`SqlUserRepository`](../src/security/sql_user_repo.py)), and synchronized failover via [`HybridUserRepository`](../src/security/hybrid_user_repo.py).
5. **Field Encryption & Audit Trails:** Sensitive settings and credentials encrypted at rest via [`FieldEncryptor`](../src/security/field_encryptor.py) and recorded through [`AuditLogger`](../src/security/audit_logger.py) (with pooled transactional writes via `db_transaction`).
6. **Transport, Endpoint & SQL Hardening:**
   - **Synapse gRPC (`:50051`) Security ([`grpc_security.py`](../src/communication/grpc_security.py)):** Supports TLS/mTLS (`grpc.ssl_server_credentials`) and constant-time Bearer / `x-carina-token` validation (`BearerTokenServerInterceptor`).
   - **Fail-Closed Web Gateway & EVP Auth ([`auth.go`](../src_go/web_gateway/auth.go), [`evp_http_server.go`](../src_go/evp_go/evp_http_server.go)):** `gateway_enabled` defaults to `False` (returning `503 Service Unavailable` when inactive), enforces constant-time token matching (`subtle.ConstantTimeCompare`), explicit CORS (`CARINA_CCO_ALLOWED_ORIGIN`), and HTTPS/TLS termination.
   - **SHA-256 Certificate Pinning ([`cco_tls_transport.py`](../src/sds/cco_tls_transport.py)):** `PinnedHTTPSConnection` verifies CA trust and optionally pins the leaf certificate SHA-256 digest when SDS pushes `/cco/broadcast`.
   - **Parameterized SQL Intervals:** PostgreSQL queries use `make_interval(...)` rather than string interpolation.
7. **12-Factor Secrets Isolation:** Absolute decoupling of sensitive secrets from source code via `.env`.

```text
 Client (Desktop UI / CCO / CLI)
          │
          ▼
 ┌──────────────────────┐      Validates Credentials       ┌────────────────────────┐
 │ AuthenticateService  │ ───────────────────────────────> │  PBKDF2PasswordHasher  │
 └──────────┬───────────┘                                  │      (crypto.py)       │
            │                                              └────────────────────────┘
            ├──> [Brute-Force Check] ──> LockdownManager (Max 3 attempts -> lockdown.flag)
            │
            └──> [User Retrieval]    ──> HybridUserRepository
                                           ├── JsonUserRepository (security.json offline)
                                           └── SqlUserRepository (system_users table)
```

---

## 2. Core Modules Breakdown (`src/security/`)

### 2.1 Password Hashing & Cryptography (`crypto.py`)
Located in [`src/security/crypto.py`](../src/security/crypto.py):
- Implements `PBKDF2PasswordHasher` using `hashlib.pbkdf2_hmac("sha256", ..., iterations=100000)`.
- Generates 16 bytes of cryptographically secure random salt (`os.urandom(16)`).
- Serializes hashes in the standardized format: `salt_hex:key_hex`.
- Uses timing-attack-resistant constant-time comparison (`hmac.compare_digest`).
- Provides emergency master password authentication comparing SHA-256 digests against `CARINA_SUPERUSER_HASH` or master override secrets via `MasterCredentialValidator`.

### 2.2 Brute-Force Protection & Lockdown (`lockdown_manager.py` & `lockdown_enforcer.py`)
Located in [`src/security/lockdown_manager.py`](../src/security/lockdown_manager.py) and [`src/security/lockdown_enforcer.py`](../src/security/lockdown_enforcer.py):
- Tracks failed authentication attempts in memory and state files (`JsonAttemptStore`, `MemoryAttemptStore`).
- Automatically engages system lockdown upon reaching 3 failed attempts (`MAX_FAILED_ATTEMPTS = 3`).
- Writes a persistent `lockdown.flag` containing timestamp, machine identifier, and failure context.
- Raises `LockdownActiveError` on all standard authentication attempts while the flag exists.
- System lockdown can only be lifted through privileged intervention by a validated `SUPERUSER` or emergency master credential.

### 2.3 User Service & Repositories (`authenticate_service.py`, `account_manager.py`, `json_user_repo.py`, `sql_user_repo.py`)
- [`src/security/authenticate_service.py`](../src/security/authenticate_service.py): Core authentication service (`AuthenticateService` / alias `AuthService`).
- [`src/security/account_manager.py`](../src/security/account_manager.py): Manages user account lifecycle, creation, deletion, role assignment, and updates (`UserAccountManager` / alias `UserManagementService`).
- [`src/security/password_policy.py`](../src/security/password_policy.py): Enforces password complexity rules (`ModernPasswordPolicy` and `PasswordValidator` requiring minimum 8 characters, uppercase, lowercase, digits, and special characters).
- [`src/security/json_user_repo.py`](../src/security/json_user_repo.py): Implements `JsonUserRepository` for local file-based offline persistence in `security.json`.
- [`src/security/sql_user_repo.py`](../src/security/sql_user_repo.py): Implements `SqlUserRepository` for PostgreSQL and SQLite persistence in table `system_users`.
- [`src/security/hybrid_user_repo.py`](../src/security/hybrid_user_repo.py): Implements `HybridUserRepository` providing seamless bidirectional synchronization between SQL and offline JSON.
- [`src/security/field_encryptor.py`](../src/security/field_encryptor.py): Provides Fernet/AES-GCM field encryption for sensitive tokens at rest.
- [`src/security/audit_logger.py`](../src/security/audit_logger.py): Logs structured security events (`UserAuthenticatedEvent`, `AuthenticationFailedEvent`, `LockdownTriggeredEvent`).

---

## 3. 12-Factor Configuration & Environment Variables

All sensitive credentials must be set in [`.env`](../.env.example) and must never be committed to git:

```bash
# --- Execution Mode ---
# 'development': allows default GitHub demo credentials (admin / Admin@Carina2026!).
# 'production': STRICTLY BLOCKS default credentials; requires hashed secrets.
CARINA_ENV=production

# --- Superuser Initialization ---
CARINA_SUPERUSER_USER=admin_traffic
CARINA_SUPERUSER_PASSWORD=YourStrongPasswordHere!
CARINA_SUPERUSER_HASH=5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8

# --- Database Credentials ---
CARINA_DB_USER=carina_sec
CARINA_DB_PASSWORD=database_secure_password
CARINA_DB_HOST=127.0.0.1
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_DB_SCHEMA=schema_carina

# --- SNMP / Physical Controller Secret ---
CARINA_SNMP_COMMUNITY=YourSnmpCommunityString

# --- External Monitor Telemetry Credentials ---
CARINA_MQTT_HOST=127.0.0.1                     # Local broker or https://tunnel.ngrok-free.dev/api/telemetry
CARINA_MQTT_PORT=1883
CARINA_MQTT_USER=
CARINA_MQTT_PASSWORD=

# --- Remote Gateway & CCO/EVP Transport Security ---
CARINA_GATEWAY_ENABLED=False                   # Fail-closed until tokens are configured
CARINA_EVP_AUTH_TOKEN=
CARINA_CCO_AUTH_TOKEN=
CARINA_CCO_ALLOWED_ORIGIN=                     # Explicit CORS origin for CCO endpoints
CARINA_GATEWAY_TLS_CERT=
CARINA_GATEWAY_TLS_KEY=
CARINA_GATEWAY_TLS_CA=
CARINA_GATEWAY_TLS_SERVER_NAME=

# --- Synapse gRPC (:50051) Security ---
CARINA_GRPC_AUTH_TOKEN=
CARINA_GRPC_TLS_ENABLED=False
CARINA_GRPC_TLS_CERT=
CARINA_GRPC_TLS_KEY=
CARINA_GRPC_TLS_CA=
CARINA_GRPC_REQUIRE_CLIENT_CERT=False
```

---

## 4. Production Security Hardening Guidelines

1. **Rotate SNMP Community Strings & Enable SNMPv3:** Avoid default `"public"` communities in production; prefer **SNMPv3 `AuthPriv`** (`SHA256` + `AES`) configured via `snmp_config` in `hardware_controller_connections`.
2. **Enable gRPC & Web Gateway TLS + Tokens:** Never flip `CARINA_GATEWAY_ENABLED=True` in production without setting strong `CARINA_EVP_AUTH_TOKEN`, `CARINA_CCO_AUTH_TOKEN`, `CARINA_CCO_ALLOWED_ORIGIN`, and `CARINA_GRPC_AUTH_TOKEN` + TLS certificates.
3. **Database Least-Privilege:** Grant the application database user only `SELECT`, `INSERT`, `UPDATE`, and `DELETE` (for retention purges) on operational schemas.
4. **Physical Controller Fail-Safe:** Ensure all physical controllers have active internal time-of-day flash modes configured if communication drops.
5. **Secure Permission on JSON Vault:** Ensure file permissions on `security.json` and `lockdown.flag` are restricted to the application service user (`chmod 600`).

---

<div align="center">
  <img src="assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
