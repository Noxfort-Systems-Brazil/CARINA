---
tags: [security, auth, bcrypt, users, rbac, 12-factor]
aliases: [Security & Authentication, User Management, Access Control, Security Manager]
---

# 🔐 Security Architecture, Authentication & User Management

This document specifies CARINA's enterprise security architecture located in [`src/utils/security/`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/utils/security) and [`src/utils/security_manager.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/utils/security_manager.py). It details user authentication, cryptographic password hashing, brute-force defense, database schema isolation, and the 12-Factor App configuration paradigm.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🗄️ See [Database & Schemas](DATABASE_AND_SCHEMAS.md) | 🛠️ See [Developer Guides](DEVELOPER_GUIDES.md)

---

## 1. Security Architecture Overview

CARINA governs safety-critical municipal infrastructure. Unauthorized access or privilege escalation could compromise traffic light controllers, leading to collisions or gridlock. To protect against these threats, the system enforces:

1. **Deterministic Password Hashing:** Salted `bcrypt` cryptographic hashing with configurable work factors.
2. **Brute-Force Defense (Lockdown Engine):** IP and username rate-limiting with exponential cooldowns.
3. **Role-Based Access Control (RBAC):** Differentiated access for `OPERATOR`, `ENGINEER`, and `ADMIN`.
4. **12-Factor Secrets Isolation:** Absolute decoupling of sensitive secrets from source code via `.env`.

```text
 Client (Flet UI / CLI)
          │
          ▼
 ┌──────────────────┐      Validates Credentials       ┌──────────────────┐
 │   AuthService    │ ───────────────────────────────> │  Bcrypt Hasher   │
 └────────┬─────────┘                                  └──────────────────┘
          │
          ├──> [Brute-Force Check] ──> LockdownManager (Max 5 attempts, 15m lockout)
          │
          └──> [User Retrieval]    ──> UserRepository (PostgreSQL / SQLite Isolated Schema)
```

---

## 2. Core Modules Breakdown

### 2.1 Password Hashing & Cryptography (`hasher.py`)
Located in [`src/utils/security/hasher.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/utils/security/hasher.py):
- Implements secure hashing with `bcrypt`.
- Automatic salt generation ($2^{12}$ rounds by default).
- Timing-attack-resistant string comparison for password verification.

### 2.2 Brute-Force Protection (`lockdown.py`)
Located in [`src/utils/security/lockdown.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/utils/security/lockdown.py):
- Tracks failed login attempts per username and client source.
- Triggers automatic account lockout after 5 consecutive failures.
- Enforces an escalating lockout period (default: 15 minutes).

### 2.3 User Service & Repository (`user_service.py` & `user_repository.py`)
- [`src/utils/security/user_repository.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/utils/security/user_repository.py): Direct SQL persistence for user records, active sessions, and access logs.
- [`src/utils/security/migrator.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/utils/security/migrator.py): Auto-initializes and migrates the `users` and `audit_log` tables across SQLite and PostgreSQL schemas.

---

## 3. 12-Factor Configuration & Environment Variables

All sensitive credentials must be set in [`.env`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/.env.example) and must never be committed to git:

```bash
# --- Execution Mode ---
# 'development': allows default demo credentials (admin:admin).
# 'production': STRICTLY BLOCKS default credentials; requires hashed secrets.
CARINA_ENV=production

# --- Superuser Initialization ---
CARINA_SUPERUSER_USER=admin_traffic
CARINA_SUPERUSER_PASSWORD=YourStrongPasswordHere!
CARINA_SUPERUSER_HASH=$2b$12$e8x...

# --- Database Credentials ---
CARINA_DB_USER=carina_sec
CARINA_DB_PASSWORD=database_secure_password
CARINA_DB_HOST=127.0.0.1
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_DB_SCHEMA=schema_carina

# --- SNMP / Physical Controller Secret ---
CARINA_SNMP_COMMUNITY=YourSnmpCommunityString
```

---

## 4. Production Security Hardening Guidelines

1. **Rotate SNMP Community Strings:** Never use the default string `"public"` in production deployments.
2. **Restrict IPC & gRPC Bindings:** In production, bind gRPC (`50051`) and WebSocket (`8080`) interfaces to private local VLANs or `127.0.0.1` unless behind a TLS-terminating reverse proxy.
3. **Database Least-Privilege:** Grant the application database user only `SELECT`, `INSERT`, and `UPDATE` on operational schemas.
4. **Physical Controller Fail-Safe:** Ensure all physical controllers have active internal time-of-day flash modes configured if communication drops.
