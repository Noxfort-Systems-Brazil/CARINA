---
tags: [security, auth, pbkdf2, users, rbac, 12-factor]
aliases: [安全机制与身份认证, 用户管理, 权限控制, 安全管理器]
---

# 🔐 安全架构、身份认证与用户权限管理

本文档详尽规范了 CARINA 位于 [`src/security/`](../../src/security) 的企业级系统安全架构。深入阐述了用户身份认证、基于密码学的加盐散列密码存储、防暴力破解锁定机制、JSON/SQL 混合仓储、字段加密以及遵循 12-Factor 规范的敏感机密管理体系。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🗄️ 查阅 [数据库与模式](database_and_schemas.md) | 🛠️ 查阅 [开发者指南](developer_guides.md)

---

## 1. 系统安全架构全景概览

CARINA 直接管控城市关键市政交通基础设施。任何未经授权的非法入侵或越权提权行为，均可能导致物理交通机失控，造成严重的交通事故碰撞或城市路网瘫痪。为防御各类网络与系统安全威胁，安全子系统采用 Clean Architecture / DDD 规范实施以下安全基线：

1. **确定性强密码哈希：** 采用 `PBKDF2PasswordHasher`，基于 PBKDF2 HMAC SHA-256 算法进行加盐散列（100,000 次迭代，16 字节高熵随机盐，支持 `Argon2PasswordHasher`）。Master 应急备用认证通过恒定时间字符串比较（`hmac.compare_digest`）直接比对 SHA-256 摘要完成。
2. **防暴力破解防御机制 (Lockdown Engine)：** 通过 [`FileLockdownManager`](../../src/security/lockdown_manager.py) 与 [`LockdownEnforcer`](../../src/security/lockdown_enforcer.py) 持久化跟踪认证失败次数。当连续失败达到 3 次（`MAX_FAILED_ATTEMPTS = 3`）时，系统自动生成持久化标志文件 `lockdown.flag` 并同步更新 `system_security_state`，全面拦截所有标准登录请求，直至经过验证的超级管理员（`SUPERUSER`）或主控覆盖（`MASTER`）解除锁定。
3. **基于角色的细粒度访问控制 (RBAC)：** 严格的二元特权层级：
   - `OPERATOR`：日常路口监测、手动相位调用、查看遥测数据及只读诊断。
   - `SUPERUSER`：完全管理权限、用户增删、安全策略配置以及解除系统锁定（`lockdown`）。
4. **混合型凭据存储（离线优先与关系型持久化）：** 支持本地独立 JSON 文件存储（`security.json`，由 [`JsonUserRepository`](../../src/security/json_user_repo.py) 管理）、PostgreSQL/SQLite 关系型表持久化（`system_users` 和 `system_security_state`，由 [`SqlUserRepository`](../../src/security/sql_user_repo.py) 管理）以及双向韧性同步机制（[`HybridUserRepository`](../../src/security/hybrid_user_repo.py)）。
5. **字段级加密与安全审计：** 敏感配置及令牌在静止状态下由 [`FieldEncryptor`](../../src/security/field_encryptor.py) 实施对称加密，关键操作通过 [`AuditLogger`](../../src/security/audit_logger.py)（借助 `db_transaction` 实现池化事务写入）生成不可篡改的审计追踪。
6. **传输、端点与 SQL 安全加固：**
   - **Synapse gRPC (`:50051`) 安全机制 ([`grpc_security.py`](../../src/communication/grpc_security.py))：** 支持 TLS/mTLS（`grpc.ssl_server_credentials`）以及恒定时间 Bearer / `x-carina-token` 令牌校验（`BearerTokenServerInterceptor`）。
   - **默认关闭的 Web 网关与 EVP 认证 ([`auth.go`](../../src_go/web_gateway/auth.go), [`evp_http_server.go`](../../src_go/evp_go/evp_http_server.go))：** `gateway_enabled` 默认设置为 `False`（未启用时返回 `503 Service Unavailable`），强制执行恒定时间令牌匹配（`subtle.ConstantTimeCompare`）、显式 CORS（`CARINA_CCO_ALLOWED_ORIGIN`）以及 HTTPS/TLS 终止。
   - **SHA-256 证书指纹固定 ([`cco_tls_transport.py`](../../src/sds/cco_tls_transport.py))：** 当 SDS 向 `/cco/broadcast` 推送数据时，`PinnedHTTPSConnection` 会校验 CA 信任链并支持对叶证书 SHA-256 摘要进行指纹固定。
   - **参数化 SQL 时间间隔：** PostgreSQL 查询全部采用 `make_interval(...)` 而非字符串拼接。
7. **12-Factor 机密彻底隔离：** 杜绝在任何源代码中硬编码机密凭据，所有敏感信息统一由 `.env` 环境注入。

```text
 客户端终端 (桌面 UI / CCO 平台 / CLI 工具)
          │
          ▼
 ┌──────────────────────┐      校验身份安全凭据       ┌────────────────────────┐
 │ AuthenticateService  │ ───────────────────────────> │  PBKDF2PasswordHasher  │
 └──────────┬───────────┘                              │      (crypto.py)       │
            │                                          └────────────────────────┘
            ├──> [防爆破安全校验] ──> LockdownManager (最多允许 3 次错误尝试 -> lockdown.flag)
            │
            └──> [用户信息检索]   ──> HybridUserRepository
                                           ├── JsonUserRepository (独立存储于 security.json)
                                           └── SqlUserRepository (持久化于 system_users 表)
```

---

## 2. `src/security/` 核心安全模块

### 2.1 密码哈希与密码学引擎 (`crypto.py`)
位于 [`src/security/crypto.py`](../../src/security/crypto.py)：
- 实现 `PBKDF2PasswordHasher`，基于 `hashlib.pbkdf2_hmac("sha256", ..., iterations=100000)`。
- 生成 16 字节密码学安全随机盐（`os.urandom(16)`）。
- 将哈希值序列化为标准化格式：`salt_hex:key_hex`。
- 采用恒定时间（Constant-time）字符串比较逻辑（`hmac.compare_digest`），彻底免疫基于时序分析的侧信道旁路攻击（Timing Attacks）。
- 提供紧急 Master 认证支持，将 SHA-256 摘要与环境变量 `CARINA_SUPERUSER_HASH` 进行对比，通过 `MasterCredentialValidator` 执行验证。

### 2.2 防暴力破解锁定引擎 (`lockdown_manager.py` 与 `lockdown_enforcer.py`)
位于 [`src/security/lockdown_manager.py`](../../src/security/lockdown_manager.py) 与 [`src/security/lockdown_enforcer.py`](../../src/security/lockdown_enforcer.py)：
- 在内存与磁盘状态中跟踪连续失败登录尝试（`JsonAttemptStore`, `MemoryAttemptStore`）。
- 当达到 3 次失败（`MAX_FAILED_ATTEMPTS = 3`）时立即触发全系统锁定。
- 写入持久化标记文件 `lockdown.flag`（记录时间戳、主机标识和失败上下文）。
- 锁定生效期间，所有标准登录尝试均会抛出 `LockdownActiveError`。
- 只有经过特权验证的 `SUPERUSER` 或紧急 Master 凭据才能清除此锁定标志。

### 2.3 用户管理服务与仓储层 (`authenticate_service.py`, `account_manager.py`, `json_user_repo.py`, `sql_user_repo.py`)
- [`src/security/authenticate_service.py`](../../src/security/authenticate_service.py)：核心身份认证服务（`AuthenticateService` / 别名 `AuthService`）。
- [`src/security/account_manager.py`](../../src/security/account_manager.py)：管理用户全生命周期、账号创建、角色分配与变更（`UserAccountManager` / 别名 `UserManagementService`）。
- [`src/security/password_policy.py`](../../src/security/password_policy.py)：执行密码复杂度规则校验（`ModernPasswordPolicy` 与 `PasswordValidator`）。
- [`src/security/json_user_repo.py`](../../src/security/json_user_repo.py)：实现 `JsonUserRepository`，在本地 `security.json` 文件中离线持久化用户凭据。
- [`src/security/sql_user_repo.py`](../../src/security/sql_user_repo.py)：实现 `SqlUserRepository`，在 PostgreSQL / SQLite 的 `system_users` 表中持久化用户数据。
- [`src/security/hybrid_user_repo.py`](../../src/security/hybrid_user_repo.py)：实现 `HybridUserRepository`，提供 SQL 与离线 JSON 之间的高韧性双向同步。
- [`src/security/field_encryptor.py`](../../src/security/field_encryptor.py)：基于安全密钥提供敏感字段及令牌的对称加密保护。
- [`src/security/audit_logger.py`](../../src/security/audit_logger.py)：记录不可篡改的安全审计与身份认证事件日志。

---

## 3. 12-Factor 原则配置与环境变量规范

所有生产级通信机密必须且只能在根目录的 [`.env`](../../.env.example) 文件中声明，严禁提交至公共 Git 版本控制仓库：

```bash
# --- 运行模式 ---
# 'development': 允许默认演示账号 (admin / Admin@Carina2026!)。
# 'production': 严格禁止默认弱口令，强制校验安全散列值。
CARINA_ENV=production

# --- 超级管理员账户初始化 ---
CARINA_SUPERUSER_USER=admin_traffic
CARINA_SUPERUSER_PASSWORD=YourStrongPasswordHere!
CARINA_SUPERUSER_HASH=5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8

# --- 数据库接入凭据 ---
CARINA_DB_USER=carina_sec
CARINA_DB_PASSWORD=database_secure_password
CARINA_DB_HOST=127.0.0.1
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_DB_SCHEMA=schema_carina

# --- SNMP / 物理信号机通信私钥 ---
CARINA_SNMP_COMMUNITY=YourSnmpCommunityString

# --- 外部监控平台遥测连接凭据 ---
CARINA_MQTT_HOST=127.0.0.1                     # 本地 Broker 或 https://tunnel.ngrok-free.dev/api/telemetry
CARINA_MQTT_PORT=1883
CARINA_MQTT_USER=
CARINA_MQTT_PASSWORD=

# --- 远程网关与 CCO/EVP 传输安全 ---
CARINA_GATEWAY_ENABLED=False                   # 默认故障安全关闭，直至完成令牌配置
CARINA_EVP_AUTH_TOKEN=
CARINA_CCO_AUTH_TOKEN=
CARINA_CCO_ALLOWED_ORIGIN=                     # CCO 端点的显式 CORS 来源
CARINA_GATEWAY_TLS_CERT=
CARINA_GATEWAY_TLS_KEY=
CARINA_GATEWAY_TLS_CA=
CARINA_GATEWAY_TLS_SERVER_NAME=

# --- Synapse gRPC (:50051) 安全配置 ---
CARINA_GRPC_AUTH_TOKEN=
CARINA_GRPC_TLS_ENABLED=False
CARINA_GRPC_TLS_CERT=
CARINA_GRPC_TLS_KEY=
CARINA_GRPC_TLS_CA=
CARINA_GRPC_REQUIRE_CLIENT_CERT=False
```

---

## 4. 生产环境安全加固指南

1. **轮换 SNMP 共同体名称并启用 SNMPv3：** 生产环境严禁保留默认共同体 `"public"`；建议通过 `hardware_controller_connections` 中的 `snmp_config` 配置 **SNMPv3 `AuthPriv`**（`SHA256` + `AES`）。
2. **启用 gRPC 与 Web 网关 TLS 及令牌认证：** 在未设置强 `CARINA_EVP_AUTH_TOKEN`、`CARINA_CCO_AUTH_TOKEN`、`CARINA_CCO_ALLOWED_ORIGIN` 以及 `CARINA_GRPC_AUTH_TOKEN` + TLS 证书之前，绝不可在生产环境将 `CARINA_GATEWAY_ENABLED` 设为 `True`。
3. **数据库最小特权原则：** 仅授予应用程序数据库账号在业务模式下的 `SELECT`、`INSERT`、`UPDATE` 以及 `DELETE`（用于过期数据保留清理）权限。
4. **物理交通机故障安全机制：** 确保所有现场交通机均配置了在丢失上位机心跳通信时自动切换至本地黄闪或定时配时的硬件机制。
5. **保护 JSON 密码库文件权限：** 确保 `security.json` 和 `lockdown.flag` 文件的访问权限严格限制为仅应用程序运行系统用户可读写（`chmod 600`）。

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智慧交通移动工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本开源 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
