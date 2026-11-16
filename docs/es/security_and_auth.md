---
tags: [seguridad, autenticacion, pbkdf2, usuarios, rbac, 12-factor]
aliases: [Seguridad y Autenticación, Gestión de Usuarios, Control de Acceso, Security Manager]
---

# 🔐 Arquitectura de Seguridad, Autenticación y Gestión de Usuarios

Este documento especifica la arquitectura de seguridad corporativa de CARINA ubicada en [`src/security/`](../../src/security). Detalla la autenticación de usuarios, el hashing criptográfico de contraseñas, la defensa contra ataques de fuerza bruta, el almacenamiento híbrido JSON/SQL, el cifrado de campos y el paradigma de configuración 12-Factor App.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🗄️ Ver [Base de Datos y Esquemas](database_and_schemas.md) | 🛠️ Ver [Guías de Desarrollo](developer_guides.md)

---

## 1. Visión General de la Arquitectura de Seguridad

CARINA gobierna infraestructura municipal de misión crítica. El acceso no autorizado o la escalada de privilegios podrían comprometer los controladores semafóricos físicos, provocando colisiones o parálisis en la red vial. Para mitigar estas amenazas, el subsistema de seguridad implementa una arquitectura limpia (Clean Architecture / DDD):

1. **Hashing Criptográfico de Contraseñas:** `PBKDF2PasswordHasher` con salting mediante PBKDF2 HMAC SHA-256, 100.000 iteraciones y sales aleatorias criptográficamente seguras de 16 bytes (con soporte para `Argon2PasswordHasher`). La autenticación de respaldo Master utiliza comparación de resúmenes SHA-256 en tiempo constante (`hmac.compare_digest`).
2. **Defensa contra Fuerza Bruta (Motor de Bloqueo):** Seguimiento persistente de intentos fallidos mediante [`FileLockdownManager`](../../src/security/lockdown_manager.py) y [`LockdownEnforcer`](../../src/security/lockdown_enforcer.py). Tras 3 intentos fallidos consecutivos (`MAX_FAILED_ATTEMPTS = 3`), el motor crea el archivo de bandera persistente `lockdown.flag` y actualiza `system_security_state`, impidiendo nuevos inicios de sesión estándar hasta que sea desbloqueado por un `SUPERUSER` o credencial `MASTER`.
3. **Control de Acceso Basado en Roles (RBAC):** Niveles estrictos de privilegios:
   - `OPERATOR`: Monitoreo rutinario de intersecciones, llamadas manuales de fases, inspección de telemetría y diagnósticos de sólo lectura.
   - `SUPERUSER`: Acceso administrativo total, creación/eliminación de usuarios, modificación de políticas y levantamiento de bloqueos (`lockdown`).
4. **Almacenamiento Híbrido de Credenciales (Offline-First y Relacional):** Soporta almacenamiento local desacoplado (`security.json` gestionado por [`JsonUserRepository`](../../src/security/json_user_repo.py)), persistencia relacional en PostgreSQL y SQLite (`system_users` y `system_security_state` mediante [`SqlUserRepository`](../../src/security/sql_user_repo.py)) y sincronización resiliente vía [`HybridUserRepository`](../../src/security/hybrid_user_repo.py).
5. **Cifrado de Campos y Auditoría:** Secretos y tokens cifrados en reposo con [`FieldEncryptor`](../../src/security/field_encryptor.py) y registro inmutable de auditoría mediante [`AuditLogger`](../../src/security/audit_logger.py) (con escrituras transaccionales agrupadas mediante `db_transaction`).
6. **Fortalecimiento de Transporte, Endpoints y SQL:**
   - **Seguridad Synapse gRPC (`:50051`) ([`grpc_security.py`](../../src/communication/grpc_security.py)):** Soporta TLS/mTLS (`grpc.ssl_server_credentials`) y validación en tiempo constante de Bearer / `x-carina-token` (`BearerTokenServerInterceptor`).
   - **Web Gateway *Fail-Closed* y Autenticación EVP ([`auth.go`](../../src_go/web_gateway/auth.go), [`evp_http_server.go`](../../src_go/evp_go/evp_http_server.go)):** `gateway_enabled` tiene por defecto el valor `False` (respondiendo `503 Service Unavailable` cuando está inactivo), impone comparación de tokens en tiempo constante (`subtle.ConstantTimeCompare`), CORS explícito (`CARINA_CCO_ALLOWED_ORIGIN`) y terminación HTTPS/TLS.
   - **Fijación (*Pinning*) de Certificados SHA-256 ([`cco_tls_transport.py`](../../src/sds/cco_tls_transport.py)):** `PinnedHTTPSConnection` verifica la confianza de la CA y fija opcionalmente el resumen SHA-256 del certificado hoja cuando SDS envía `/cco/broadcast`.
   - **Intervalos SQL Parametrizados:** Las consultas PostgreSQL utilizan `make_interval(...)` en lugar de interpolación de cadenas.
7. **Aislamiento de Secretos 12-Factor:** Desacoplamiento absoluto de secretos del código fuente a través de variables de entorno `.env`.

```text
 Cliente (Interfaz Desktop / CCO / CLI)
          │
          ▼
 ┌──────────────────────┐      Valida Credenciales          ┌────────────────────────┐
 │ AuthenticateService  │ ────────────────────────────────> │  PBKDF2PasswordHasher  │
 └──────────┬───────────┘                                   │      (crypto.py)       │
            │                                               └────────────────────────┘
            ├──> [Chequeo Fuerza Bruta] ──> LockdownManager (Máx 3 intentos -> lockdown.flag)
            │
            └──> [Recuperación Usuario] ──> HybridUserRepository
                                               ├── JsonUserRepository (security.json offline)
                                               └── SqlUserRepository (tabla system_users)
```

---

## 2. Desglose de Módulos Principales (`src/security/`)

### 2.1 Hashing de Contraseñas y Criptografía (`crypto.py`)
Ubicado en [`src/security/crypto.py`](../../src/security/crypto.py):
- Implementa `PBKDF2PasswordHasher` mediante `hashlib.pbkdf2_hmac("sha256", ..., iterations=100000)`.
- Genera 16 bytes de sal aleatoria criptográficamente segura (`os.urandom(16)`).
- Serializa hashes en formato estandarizado: `salt_hex:key_hex`.
- Utiliza comparación en tiempo constante resistente a ataques de temporización (`hmac.compare_digest`).
- Proporciona autenticación de emergencia mediante resumen SHA-256 comparado contra `CARINA_SUPERUSER_HASH` o secreto maestro con `MasterCredentialValidator`.

### 2.2 Protección contra Fuerza Bruta y Bloqueo (`lockdown_manager.py` y `lockdown_enforcer.py`)
Ubicado en [`src/security/lockdown_manager.py`](../../src/security/lockdown_manager.py) y [`src/security/lockdown_enforcer.py`](../../src/security/lockdown_enforcer.py):
- Registra intentos de autenticación fallidos en memoria y archivos de estado (`JsonAttemptStore`, `MemoryAttemptStore`).
- Activa automáticamente el bloqueo al alcanzar 3 intentos fallidos (`MAX_FAILED_ATTEMPTS = 3`).
- Escribe el archivo persistente `lockdown.flag` con marca de tiempo, identificador de máquina y contexto del fallo.
- Lanza `LockdownActiveError` en todos los intentos de login estándar mientras la bandera permanezca activa.
- El desbloqueo requiere intervención privilegiada de un `SUPERUSER` validado o credencial maestra de emergencia.

### 2.3 Servicio y Repositorios de Usuarios (`authenticate_service.py`, `account_manager.py`, `json_user_repo.py`, `sql_user_repo.py`)
- [`src/security/authenticate_service.py`](../../src/security/authenticate_service.py): Servicio principal de autenticación (`AuthenticateService` / alias `AuthService`).
- [`src/security/account_manager.py`](../../src/security/account_manager.py): Administra el ciclo de vida de usuarios, creación, roles y bajas (`UserAccountManager` / alias `UserManagementService`).
- [`src/security/password_policy.py`](../../src/security/password_policy.py): Aplica reglas de complejidad (`ModernPasswordPolicy` y `PasswordValidator`).
- [`src/security/json_user_repo.py`](../../src/security/json_user_repo.py): Implementa `JsonUserRepository`, almacenando definiciones de usuario en `security.json`.
- [`src/security/sql_user_repo.py`](../../src/security/sql_user_repo.py): Implementa `SqlUserRepository`, persistiendo usuarios en la tabla `system_users`.
- [`src/security/hybrid_user_repo.py`](../../src/security/hybrid_user_repo.py): Implementa `HybridUserRepository`, proveyendo sincronización bidireccional entre SQL y JSON.
- [`src/security/field_encryptor.py`](../../src/security/field_encryptor.py): Cifrado simétrico de credenciales y campos sensibles.
- [`src/security/audit_logger.py`](../../src/security/audit_logger.py): Registro inmutable de eventos de seguridad y acceso.

---

## 3. Configuración 12-Factor y Variables de Entorno

Todas las credenciales sensibles deben definirse en [`.env`](../../.env.example) y nunca deben confirmarse en Git:

```bash
# --- Modo de Ejecución ---
# 'development': permite credenciales de demostración por defecto (admin / Admin@Carina2026!).
# 'production': BLOQUEA ESTRICTAMENTE credenciales predeterminadas; requiere secretos hasheados.
CARINA_ENV=production

# --- Inicialización del Superusuario ---
CARINA_SUPERUSER_USER=admin_traffic
CARINA_SUPERUSER_PASSWORD=TuPasswordFuerteAqui!
CARINA_SUPERUSER_HASH=5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8

# --- Credenciales de Base de Datos ---
CARINA_DB_USER=carina_sec
CARINA_DB_PASSWORD=database_secure_password
CARINA_DB_HOST=127.0.0.1
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_DB_SCHEMA=schema_carina

# --- Secreto SNMP / Controlador Físico ---
CARINA_SNMP_COMMUNITY=TuComunidadSnmpSegura

# --- Credenciales de Telemetría Externa (Monitor) ---
CARINA_MQTT_HOST=127.0.0.1                     # Broker local o https://tunnel.ngrok-free.dev/api/telemetry
CARINA_MQTT_PORT=1883
CARINA_MQTT_USER=
CARINA_MQTT_PASSWORD=

# --- Seguridad del Gateway Remoto y Transporte CCO/EVP ---
CARINA_GATEWAY_ENABLED=False                   # Fail-closed hasta configurar los tokens
CARINA_EVP_AUTH_TOKEN=
CARINA_CCO_AUTH_TOKEN=
CARINA_CCO_ALLOWED_ORIGIN=                     # Origen CORS explícito para endpoints CCO
CARINA_GATEWAY_TLS_CERT=
CARINA_GATEWAY_TLS_KEY=
CARINA_GATEWAY_TLS_CA=
CARINA_GATEWAY_TLS_SERVER_NAME=

# --- Seguridad Synapse gRPC (:50051) ---
CARINA_GRPC_AUTH_TOKEN=
CARINA_GRPC_TLS_ENABLED=False
CARINA_GRPC_TLS_CERT=
CARINA_GRPC_TLS_KEY=
CARINA_GRPC_TLS_CA=
CARINA_GRPC_REQUIRE_CLIENT_CERT=False
```

---

## 4. Directrices de Fortalecimiento (Hardening) en Producción

1. **Rotar Cadenas de Comunidad SNMP y Habilitar SNMPv3:** Evite comunidades `"public"` predeterminadas en producción; prefiera **SNMPv3 `AuthPriv`** (`SHA256` + `AES`) configurado vía `snmp_config` en `hardware_controller_connections`.
2. **Habilitar TLS + Tokens en gRPC y Web Gateway:** Nunca active `CARINA_GATEWAY_ENABLED=True` en producción sin configurar `CARINA_EVP_AUTH_TOKEN`, `CARINA_CCO_AUTH_TOKEN`, `CARINA_CCO_ALLOWED_ORIGIN` y `CARINA_GRPC_AUTH_TOKEN` robustos junto con certificados TLS.
3. **Mínimo Privilegio en Base de Datos:** Conceder al usuario de la base de datos únicamente permisos `SELECT`, `INSERT`, `UPDATE` y `DELETE` (para purgas de retención) en los esquemas operacionales.
4. **Mecanismo Fail-Safe en Controladores Físicos:** Asegurar que todos los controladores físicos tengan configurados planes de destello amarillo local si se pierde la comunicación.
5. **Permisos Seguros en Bóveda JSON:** Restringir los permisos de archivo en `security.json` y `lockdown.flag` al usuario del servicio de la aplicación (`chmod 600`).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
