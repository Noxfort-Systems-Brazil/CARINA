---
tags: [security, auth, pbkdf2, users, rbac, 12-factor]
aliases: [Безопасность и аутентификация, Управление пользователями, Контроль доступа, Менеджер безопасности]
---

# 🔐 Архитектура безопасности, аутентификация и управление доступом

Данный документ описывает архитектуру корпоративной безопасности CARINA, расположенную в каталоге [`src/security/`](../../src/security). В нем подробно рассматриваются аутентификация пользователей, криптографическое хеширование паролей, защита от атак методом подбора (brute-force), гибридное хранилище JSON/SQL, шифрование полей и парадигма конфигурации 12-Factor App.

⬅️ Назад в [Главный хаб документации](carina_moc.md) | 🗄️ См. [База данных и схемы](database_and_schemas.md) | 🛠️ См. [Руководства разработчика](developer_guides.md)

---

## 1. Обзор архитектуры безопасности

CARINA управляет критически важной муниципальной инфраструктурой жизнеобеспечения. Несанкционированный доступ или повышение привилегий злоумышленником могут нарушить работу светофорных контроллеров, спровоцировав ДТП или транспортный коллапс. Для предотвращения подобных угроз подсистема безопасности реализует архитектуру Clean Architecture / DDD:

1. **Детерминированное хеширование паролей:** Криптографический класс `PBKDF2PasswordHasher` с использованием алгоритма PBKDF2 HMAC SHA-256 со 100 000 итерациями и криптографически стойкой псевдослучайной солью длиной 16 байт (с поддержкой `Argon2PasswordHasher`). Резервная аутентификация Master выполняется постоянным по времени сравнением дайджестов SHA-256 (`hmac.compare_digest`).
2. **Защита от перебора паролей (Lockdown Engine):** Непрерывное отслеживание неудачных попыток входа с помощью [`FileLockdownManager`](../../src/security/lockdown_manager.py) и [`LockdownEnforcer`](../../src/security/lockdown_enforcer.py). После 3 последовательных неудачных попыток (`MAX_FAILED_ATTEMPTS = 3`) движок создает постоянный файл флага `lockdown.flag` и обновляет `system_security_state`, полностью блокируя стандартные попытки входа до разблокировки суперпользователем (`SUPERUSER`) или мастер-ключом (`MASTER`).
3. **Ролевая модель доступа (RBAC):** Строгая бинарная градация прав:
   - `OPERATOR`: Рутинный мониторинг перекрестков, ручной вызов фаз, просмотр телеметрии и диагностика в режиме только чтения.
   - `SUPERUSER`: Полный административный доступ, создание/удаление пользователей, изменение политик безопасности и снятие блокировок (`lockdown`).
4. **Гибридное хранилище учетных данных (Offline-First и SQL):** Поддерживает автономное локальное хранилище (`security.json` через [`JsonUserRepository`](../../src/security/json_user_repo.py)), реляционную персистентность в PostgreSQL и SQLite (`system_users` и `system_security_state` через [`SqlUserRepository`](../../src/security/sql_user_repo.py)) и отказоустойчивую синхронизацию через [`HybridUserRepository`](../../src/security/hybrid_user_repo.py).
5. **Шифрование полей и аудит безопасности:** Конфиденциальные параметры шифруются в покое с помощью [`FieldEncryptor`](../../src/security/field_encryptor.py), а ключевые события фиксируются в [`AuditLogger`](../../src/security/audit_logger.py).
6. **Изоляция секретов по методологии 12-Factor:** Полное исключение конфиденциальных параметров из исходного кода через переменные файла `.env`.

```text
 Клиент (Desktop UI / CCO / CLI)
          │
          ▼
 ┌──────────────────────┐       Проверка учетных данных        ┌────────────────────────┐
 │ AuthenticateService  │ ───────────────────────────────────> │  PBKDF2PasswordHasher  │
 └──────────┬───────────┘                                      │      (crypto.py)       │
            │                                                  └────────────────────────┘
            ├──> [Проверка на перебор] ──> LockdownManager (Макс. 3 попытки -> lockdown.flag)
            │
            └──> [Извлечение польз.]   ──> HybridUserRepository
                                               ├── JsonUserRepository (security.json offline)
                                               └── SqlUserRepository (таблица system_users)
```

---

## 2. Обзор базовых модулей (`src/security/`)

### 2.1 Хеширование паролей и криптография (`crypto.py`)
Расположен в [`src/security/crypto.py`](../../src/security/crypto.py):
- Реализует класс `PBKDF2PasswordHasher` через вызов `hashlib.pbkdf2_hmac("sha256", ..., iterations=100000)`.
- Генерирует 16 байт криптографически стойкой случайной соли (`os.urandom(16)`).
- Формирует строку хеша в стандартизированном формате: `salt_hex:key_hex`.
- Применяет устойчивое к атакам по времени сравнение строк в постоянное время (`hmac.compare_digest`).
- Предоставляет аварийную аутентификацию по мастер-паролю путем сравнения дайджеста SHA-256 со значением `CARINA_SUPERUSER_HASH` через `MasterCredentialValidator`.

### 2.2 Защита от перебора паролей и блокировка (`lockdown_manager.py` и `lockdown_enforcer.py`)
Расположен в [`src/security/lockdown_manager.py`](../../src/security/lockdown_manager.py) и [`src/security/lockdown_enforcer.py`](../../src/security/lockdown_enforcer.py):
- Фиксирует неудачные попытки аутентификации в оперативной памяти и файлах состояния (`JsonAttemptStore`, `MemoryAttemptStore`).
- Автоматически инициирует блокировку системы при достижении 3 неудачных попыток (`MAX_FAILED_ATTEMPTS = 3`).
- Записывает постоянный файл-флаг `lockdown.flag` с меткой времени, идентификатором хоста и контекстом сбоя.
- Вызывает исключение `LockdownActiveError` на любые стандартные попытки входа, пока существует флаг.
- Снятие блокировки возможно исключительно привилегированным действием валидированного пользователя `SUPERUSER` или мастер-ключом.

### 2.3 Сервис пользователей и репозитории (`authenticate_service.py`, `account_manager.py`, `json_user_repo.py`, `sql_user_repo.py`)
- [`src/security/authenticate_service.py`](../../src/security/authenticate_service.py): Основной сервис аутентификации (`AuthenticateService` / псевдоним `AuthService`).
- [`src/security/account_manager.py`](../../src/security/account_manager.py): Управление жизненным циклом пользователей, ролями и учетными записями (`UserAccountManager` / псевдоним `UserManagementService`).
- [`src/security/password_policy.py`](../../src/security/password_policy.py): Проверяет пароли на соответствие критериям сложности (`ModernPasswordPolicy` и `PasswordValidator`).
- [`src/security/json_user_repo.py`](../../src/security/json_user_repo.py): Реализует `JsonUserRepository`, сохраняя учетные записи в локальном файле `security.json`.
- [`src/security/sql_user_repo.py`](../../src/security/sql_user_repo.py): Реализует `SqlUserRepository` для персистентности в PostgreSQL и SQLite в таблице `system_users`.
- [`src/security/hybrid_user_repo.py`](../../src/security/hybrid_user_repo.py): Реализует `HybridUserRepository`, обеспечивая синхронизацию между SQL и автономным JSON.
- [`src/security/field_encryptor.py`](../../src/security/field_encryptor.py): Шифрование чувствительных полей и токенов (Fernet/AES-GCM).
- [`src/security/audit_logger.py`](../../src/security/audit_logger.py): Неизменяемый журнал событий безопасности и аудита.

---

## 3. Конфигурация 12-Factor и переменные окружения

Все конфиденциальные параметры должны определяться исключительно в файле [`.env`](../../.env.example) и ни в коем случае не фиксироваться в репозитории Git:

```bash
# --- Режим выполнения ---
# 'development': разрешает демонстрационные учетные данные по умолчанию (admin / Admin@Carina2026!).
# 'production': СТРОГО БЛОКИРУЕТ стандартные пароли; требует безопасных хешей.
CARINA_ENV=production

# --- Инициализация суперпользователя ---
CARINA_SUPERUSER_USER=admin_traffic
CARINA_SUPERUSER_PASSWORD=ВашНадежныйПарольЗдесь!
CARINA_SUPERUSER_HASH=5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8

# --- Учетные данные базы данных ---
CARINA_DB_USER=carina_sec
CARINA_DB_PASSWORD=database_secure_password
CARINA_DB_HOST=127.0.0.1
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_DB_SCHEMA=schema_carina

# --- Пароль сообщества SNMP физического контроллера ---
CARINA_SNMP_COMMUNITY=ВашаНадежнаяСтрокаСообщества

# --- Параметры внешней телеметрии (Монитор) ---
CARINA_MQTT_HOST=127.0.0.1                     # Локальный брокер или https://tunnel.ngrok-free.dev/api/telemetry
CARINA_MQTT_PORT=1883
CARINA_MQTT_USER=
CARINA_MQTT_PASSWORD=
```

---

## 4. Рекомендации по усилению безопасности в промышленной среде

1. **Регулярная смена строки сообщества SNMP:** Никогда не используйте значение по умолчанию `"public"` на реальных дорожных сетях.
2. **Ограничение сетевых интерфейсов IPC и gRPC:** В промышленной эксплуатации привязывайте порты gRPC (`50051`) и WebSocket (`8080`) к изолированным VLAN или локальному интерфейсу `127.0.0.1`, если они не защищены обратным прокси-сервером с TLS.
3. **Принцип минимальных привилегий для БД:** Пользователю базы данных приложения должны быть предоставлены только права `SELECT`, `INSERT` и `UPDATE` в рабочей схеме.
4. **Отказоустойчивость дорожных контроллеров:** Убедитесь, что все дорожные контроллеры настроены на автоматический переход в локальный план жесткого цикла или желтое мигание при потере связи.
5. **Безопасные права доступа к JSON-хранилищу:** Файлы `security.json` и `lockdown.flag` должны иметь права доступа только для системного пользователя сервиса CARINA (`chmod 600`).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Интеллектуальная организация движения • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Лицензировано под AGPLv3 или новее (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
