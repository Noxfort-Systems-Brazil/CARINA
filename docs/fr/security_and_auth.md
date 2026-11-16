---
tags: [security, auth, pbkdf2, users, rbac, 12-factor]
aliases: [Architecture de Sécurité, Authentification, Gestion des Utilisateurs, Security Manager]
---

# 🔐 Architecture de Sécurité, Authentification & Gestion des Utilisateurs

Ce document spécifie l'architecture de sécurité d'entreprise de CARINA située dans [`src/security/`](../../src/security). Il détaille l'authentification des utilisateurs, le hachage cryptographique des mots de passe, la défense contre les attaques par force brute, le stockage hybride JSON/SQL, le chiffrement de champs et le paradigme de configuration 12-Factor App.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🗄️ Voir [Base de Données & Schémas](database_and_schemas.md) | 🛠️ Voir [Guides du Développeur](developer_guides.md)

---

## 1. Vue d'Ensemble de l'Architecture de Sécurité

CARINA régit des infrastructures municipales critiques en matière de sécurité. Tout accès non autorisé ou élévation de privilèges pourrait compromettre les contrôleurs de feux de signalisation physiques, entraînant des collisions ou des blocages massifs de circulation. Pour se prémunir contre ces menaces, le sous-système de sécurité adopte une architecture propre (Clean Architecture / DDD) :

1. **Hachage Déterministe des Mots de Passe :** Hachage cryptographique salé `PBKDF2PasswordHasher` utilisant PBKDF2 HMAC SHA-256 avec 100 000 itérations et des sels aléatoires cryptographiquement sûrs de 16 octets (avec support pour `Argon2PasswordHasher`). L'authentification de secours Master utilise la comparaison d'empreintes SHA-256 en temps constant (`hmac.compare_digest`).
2. **Défense Anti-Force Brute (Moteur de Verrouillage) :** Suivi persistant des tentatives infructueuses via [`FileLockdownManager`](../../src/security/lockdown_manager.py) et [`LockdownEnforcer`](../../src/security/lockdown_enforcer.py). Après 3 tentatives infructueuses consécutives (`MAX_FAILED_ATTEMPTS = 3`), le moteur crée le fichier d'indicateur persistant `lockdown.flag` et met à jour `system_security_state`, bloquant toute connexion standard jusqu'au déverrouillage par un `SUPERUSER` ou un remplacement `MASTER`.
3. **Contrôle d'Accès Basé sur les Rôles (RBAC) :** Niveaux stricts de privilèges :
   - `OPERATOR` : Surveillance de routine des carrefours, appels manuels de phases, inspection de télémétrie et diagnostics en lecture seule.
   - `SUPERUSER` : Accès administratif complet, création/suppression d'utilisateurs, modification des politiques et levée des blocages (`lockdown`).
4. **Stockage Hybride des Identifiants (Offline-First & Relationnel) :** Supporte le stockage local découplé (`security.json` géré par [`JsonUserRepository`](../../src/security/json_user_repo.py)), la persistance relationnelle sous PostgreSQL et SQLite (`system_users` et `system_security_state` gérés par [`SqlUserRepository`](../../src/security/sql_user_repo.py)) et la synchronisation résiliente via [`HybridUserRepository`](../../src/security/hybrid_user_repo.py).
5. **Chiffrement de Champs et Traces d'Audit :** Données sensibles chiffrées au repos par [`FieldEncryptor`](../../src/security/field_encryptor.py) et enregistrées via [`AuditLogger`](../../src/security/audit_logger.py) (avec écritures transactionnelles en pool via `db_transaction`).
6. **Durcissement du Transport, des Points de Terminaison & du SQL :**
   - **Sécurité gRPC Synapse (`:50051`) ([`grpc_security.py`](../../src/communication/grpc_security.py)) :** Prend en charge TLS/mTLS (`grpc.ssl_server_credentials`) et la validation en temps constant Bearer / `x-carina-token` (`BearerTokenServerInterceptor`).
   - **Passerelle Web Fail-Closed & Authentification EVP ([`auth.go`](../../src_go/web_gateway/auth.go), [`evp_http_server.go`](../../src_go/evp_go/evp_http_server.go)) :** `gateway_enabled` vaut `False` par défaut (retournant `503 Service Unavailable` lorsqu'elle est inactive), applique une comparaison de jetons en temps constant (`subtle.ConstantTimeCompare`), un CORS explicite (`CARINA_CCO_ALLOWED_ORIGIN`) et la terminaison HTTPS/TLS.
   - **Épinglage de Certificat SHA-256 ([`cco_tls_transport.py`](../../src/sds/cco_tls_transport.py)) :** `PinnedHTTPSConnection` vérifie la confiance de la CA et épingle optionnellement l'empreinte SHA-256 du certificat feuille lorsque SDS pousse vers `/cco/broadcast`.
   - **Intervalles SQL Paramétrés :** Les requêtes PostgreSQL utilisent `make_interval(...)` plutôt que l'interpolation de chaînes.
7. **Isolation des Secrets 12-Factor :** Découplage absolu des secrets sensibles du code source via les variables d'environnement `.env`.

```text
 Client (IHM Desktop / CCO / CLI)
          │
          ▼
 ┌──────────────────────┐      Valide les Identifiants      ┌────────────────────────┐
 │ AuthenticateService  │ ────────────────────────────────> │  PBKDF2PasswordHasher  │
 └──────────┬───────────┘                                   │      (crypto.py)       │
            │                                               └────────────────────────┘
            ├──> [Contrôle Force Brute] ──> LockdownManager (Max 3 tentatives -> lockdown.flag)
            │
            └──> [Récupération Profil]  ──> HybridUserRepository
                                               ├── JsonUserRepository (security.json offline)
                                               └── SqlUserRepository (table system_users)
```

---

## 2. Décomposition des Modules Principaux (`src/security/`)

### 2.1 Hachage de Mots de Passe & Cryptographie (`crypto.py`)
Situé dans [`src/security/crypto.py`](../../src/security/crypto.py) :
- Implémente `PBKDF2PasswordHasher` via `hashlib.pbkdf2_hmac("sha256", ..., iterations=100000)`.
- Génère 16 octets de sel aléatoire cryptographiquement sûr (`os.urandom(16)`).
- Sérialise les empreintes au format standardisé : `salt_hex:key_hex`.
- Utilise une comparaison en temps constant résistante aux attaques temporelles (`hmac.compare_digest`).
- Fournit l'authentification d'urgence par mot de passe maître en comparant les empreintes SHA-256 à `CARINA_SUPERUSER_HASH` ou aux secrets de remplacement maître via `MasterCredentialValidator`.

### 2.2 Protection Anti-Force Brute & Verrouillage (`lockdown_manager.py` et `lockdown_enforcer.py`)
Situé dans [`src/security/lockdown_manager.py`](../../src/security/lockdown_manager.py) et [`src/security/lockdown_enforcer.py`](../../src/security/lockdown_enforcer.py) :
- Enregistre les tentatives de connexion infructueuses en mémoire et dans les fichiers d'état (`JsonAttemptStore`, `MemoryAttemptStore`).
- Déclenche automatiquement le verrouillage dès l'atteinte de 3 échecs (`MAX_FAILED_ATTEMPTS = 3`).
- Génère le fichier persistant `lockdown.flag` contenant l'horodatage, l'identifiant machine et le contexte de l'échec.
- Déclenche une exception `LockdownActiveError` pour toute tentative de connexion standard tant que le fichier subsiste.
- Le déverrouillage nécessite l'intervention d'un `SUPERUSER` validé ou d'identifiants maîtres d'urgence.

### 2.3 Service Utilisateur & Dépôts (`authenticate_service.py`, `account_manager.py`, `json_user_repo.py`, `sql_user_repo.py`)
- [`src/security/authenticate_service.py`](../../src/security/authenticate_service.py) : Service central d'authentification (`AuthenticateService` / alias `AuthService`).
- [`src/security/account_manager.py`](../../src/security/account_manager.py) : Gère le cycle de vie des utilisateurs, rôles et privilèges (`UserAccountManager` / alias `UserManagementService`).
- [`src/security/password_policy.py`](../../src/security/password_policy.py) : Applique les critères de complexité (`ModernPasswordPolicy` et `PasswordValidator`).
- [`src/security/json_user_repo.py`](../../src/security/json_user_repo.py) : Implémente `JsonUserRepository` pour la persistance locale dans `security.json`.
- [`src/security/sql_user_repo.py`](../../src/security/sql_user_repo.py) : Implémente `SqlUserRepository` pour la persistance SQL sous PostgreSQL et SQLite dans la table `system_users`.
- [`src/security/hybrid_user_repo.py`](../../src/security/hybrid_user_repo.py) : Implémente `HybridUserRepository`, fournissant une synchronisation bidirectionnelle résiliente entre SQL et JSON.
- [`src/security/field_encryptor.py`](../../src/security/field_encryptor.py) : Chiffrement symétrique des clés et jetons sensibles.
- [`src/security/audit_logger.py`](../../src/security/audit_logger.py) : Journalisation immuable des événements de sécurité.

---

## 3. Configuration 12-Factor & Variables d'Environnement

Tous les identifiants et clés sensibles doivent être définis dans [`.env`](../../.env.example) et ne doivent jamais être validés dans git :

```bash
# --- Mode d'Exécution ---
# 'development' : autorise les identifiants de démonstration par défaut (admin / Admin@Carina2026!).
# 'production' : BLOQUE STRICTEMENT les identifiants par défaut ; requiert des secrets hachés.
CARINA_ENV=production

# --- Initialisation du Superutilisateur ---
CARINA_SUPERUSER_USER=admin_traffic
CARINA_SUPERUSER_PASSWORD=VotreMotDePasseRobusteIci!
CARINA_SUPERUSER_HASH=5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8

# --- Identifiants de Base de Données ---
CARINA_DB_USER=carina_sec
CARINA_DB_PASSWORD=database_secure_password
CARINA_DB_HOST=127.0.0.1
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_DB_SCHEMA=schema_carina

# --- Secret SNMP / Contrôleur Physique ---
CARINA_SNMP_COMMUNITY=VotreChaineCommunauteSnmp

# --- Identifiants de Télémétrie Externe (Moniteur) ---
CARINA_MQTT_HOST=127.0.0.1                     # Broker local ou https://tunnel.ngrok-free.dev/api/telemetry
CARINA_MQTT_PORT=1883
CARINA_MQTT_USER=
CARINA_MQTT_PASSWORD=

# --- Sécurité Passerelle Distante & Transport CCO/EVP ---
CARINA_GATEWAY_ENABLED=False                   # Fail-closed tant que les jetons ne sont pas configurés
CARINA_EVP_AUTH_TOKEN=
CARINA_CCO_AUTH_TOKEN=
CARINA_CCO_ALLOWED_ORIGIN=                     # Origine CORS explicite pour les points d'accès CCO
CARINA_GATEWAY_TLS_CERT=
CARINA_GATEWAY_TLS_KEY=
CARINA_GATEWAY_TLS_CA=
CARINA_GATEWAY_TLS_SERVER_NAME=

# --- Sécurité gRPC Synapse (:50051) ---
CARINA_GRPC_AUTH_TOKEN=
CARINA_GRPC_TLS_ENABLED=False
CARINA_GRPC_TLS_CERT=
CARINA_GRPC_TLS_KEY=
CARINA_GRPC_TLS_CA=
CARINA_GRPC_REQUIRE_CLIENT_CERT=False
```

---

## 4. Directives de Durcissement (Hardening) en Production

1. **Rotation des Chaînes de Communauté SNMP & Activation SNMPv3 :** Évitez les communautés par défaut `"public"` en production ; privilégiez **SNMPv3 `AuthPriv`** (`SHA256` + `AES`) configuré via `snmp_config` dans `hardware_controller_connections`.
2. **Activation TLS + Jetons pour gRPC & Passerelle Web :** Ne passez jamais `CARINA_GATEWAY_ENABLED=True` en production sans définir des jetons robustes `CARINA_EVP_AUTH_TOKEN`, `CARINA_CCO_AUTH_TOKEN`, `CARINA_CCO_ALLOWED_ORIGIN`, ainsi que `CARINA_GRPC_AUTH_TOKEN` + certificats TLS.
3. **Moindre Privilège en Base de Données :** Accorder à l'utilisateur applicatif uniquement les droits `SELECT`, `INSERT`, `UPDATE` et `DELETE` (pour les purges de rétention) sur les schémas opérationnels.
4. **Mécanisme Fail-Safe des Contrôleurs Physiques :** S'assurer que tous les contrôleurs physiques disposent de plans de clignotement jaune configurés en cas de coupure de communication.
5. **Permissions Sécurisées sur le Coffre-Fort JSON :** Restreindre les permissions de lecture/écriture de `security.json` et `lockdown.flag` au seul utilisateur système du service applicatif (`chmod 600`).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3 ou ultérieure (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
