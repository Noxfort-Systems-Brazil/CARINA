---
tags: [security, auth, bcrypt, users, rbac, 12-factor]
aliases: [Security & Authentication, User Management, Access Control, Security Manager]
---

# 🔐 Architecture de Sécurité, Authentification & Gestion des Utilisateurs

Ce document spécifie l'architecture de sécurité d'entreprise de CARINA située dans [`src/utils/security/`](../../src/utils/security) et [`src/utils/security_manager.py`](../../src/utils/security_manager.py). Il détaille l'authentification des utilisateurs, le hachage cryptographique des mots de passe, la défense contre les attaques par force brute, l'isolation des schémas de base de données et le paradigme de configuration 12-Factor App.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🗄️ Voir [Base de Données & Schémas](database_and_schemas.md) | 🛠️ Voir [Guides du Développeur](developer_guides.md)

---

## 1. Vue d'Ensemble de l'Architecture de Sécurité

CARINA régit des infrastructures municipales critiques en matière de sécurité. Tout accès non autorisé ou élévation de privilèges pourrait compromettre les contrôleurs de feux de signalisation, entraînant des collisions ou des blocages massifs de circulation. Pour se prémunir contre ces menaces, le système applique :

1. **Hachage Déterministe des Mots de Passe :** Hachage cryptographique `bcrypt` salé avec facteur de travail paramétrable.
2. **Défense Anti-Force Brute (Moteur de Verrouillage) :** Limitation de débit par IP et nom d'utilisateur avec périodes de refroidissement exponentielles.
3. **Contrôle d'Accès Basé sur les Rôles (RBAC) :** Droits d'accès différenciés pour `OPERATOR`, `ENGINEER` et `ADMIN`.
4. **Isolation des Secrets 12-Factor :** Découplage absolu des secrets sensibles du code source via les variables `.env`.

```text
 Client (IHM Flet / CLI)
          │
          ▼
 ┌──────────────────┐      Valide les Identifiants      ┌──────────────────┐
 │   AuthService    │ ────────────────────────────────> │  Hacheur Bcrypt  │
 └────────┬─────────┘                                   └──────────────────┘
          │
          ├──> [Contrôle Force Brute] ──> LockdownManager (Max 5 tentatives, verrouillage 15m)
          │
          └──> [Récupération Profil]  ──> UserRepository (Schéma Isolé PostgreSQL / SQLite)
```

---

## 2. Décomposition des Modules Principaux

### 2.1 Hachage de Mots de Passe & Cryptographie (`hasher.py`)
Situé dans [`src/utils/security/hasher.py`](../../src/utils/security/hasher.py) :
- Implémente le hachage sécurisé avec `bcrypt`.
- Génération automatique de sel ($2^{12}$ tours par défaut).
- Comparaison de chaînes en temps constant résistante aux attaques temporelles pour la vérification des mots de passe.

### 2.2 Protection Anti-Force Brute (`lockdown.py`)
Situé dans [`src/utils/security/lockdown.py`](../../src/utils/security/lockdown.py) :
- Suit les tentatives de connexion infructueuses par nom d'utilisateur et source cliente.
- Déclenche un verrouillage automatique du compte après 5 échecs consécutifs.
- Impose une période d'exclusion progressive (par défaut : 15 minutes).

### 2.3 Service Utilisateur & Dépôt (`user_service.py` & `user_repository.py`)
- [`src/utils/security/user_repository.py`](../../src/utils/security/user_repository.py) : Persistance SQL directe pour les enregistrements d'utilisateurs, les sessions actives et les journaux d'accès.
- [`src/utils/security/migrator.py`](../../src/utils/security/migrator.py) : Initialise et migre automatiquement les tables `users` et `audit_log` sur les schémas SQLite et PostgreSQL.

---

## 3. Configuration 12-Factor & Variables d'Environnement

Tous les identifiants et clés sensibles doivent être définis dans [`.env`](../../.env.example) et ne doivent jamais être validés dans git :

```bash
# --- Mode d'Exécution ---
# 'development' : autorise les identifiants de démo GitHub par défaut (admin / Admin@Carina2026!).
# 'production' : BLOQUE STRICTEMENT les identifiants par défaut ; exige des secrets hachés.
CARINA_ENV=production

# --- Initialisation du Superutilisateur ---
CARINA_SUPERUSER_USER=admin_traffic
CARINA_SUPERUSER_PASSWORD=YourStrongPasswordHere!
CARINA_SUPERUSER_HASH=$2b$12$e8x...

# --- Identifiants de Base de Données ---
CARINA_DB_USER=carina_sec
CARINA_DB_PASSWORD=database_secure_password
CARINA_DB_HOST=127.0.0.1
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_DB_SCHEMA=schema_carina

# --- Secret SNMP / Contrôleurs Physiques ---
CARINA_SNMP_COMMUNITY=YourSnmpCommunityString

# --- Identifiants de Télémétrie Monitor Externe ---
CARINA_MQTT_HOST=127.0.0.1                     # Courtier local ou https://tunnel.ngrok-free.dev/api/telemetry
CARINA_MQTT_PORT=1883
CARINA_MQTT_USER=
CARINA_MQTT_PASSWORD=
```

---

## 4. Directives de Durcissement de Sécurité en Production

1. **Rotation des Chaînes de Communauté SNMP :** Ne jamais utiliser la chaîne par défaut `"public"` dans les déploiements de production.
2. **Restriction des Liaisons IPC & gRPC :** En production, lier les interfaces gRPC (`50051`) et WebSocket (`8080`) à des VLANs locaux privés ou à `127.0.0.1` sauf si elles sont placées derrière un proxy inverse avec terminaison TLS.
3. **Moindre Privilège de Base de Données :** Accorder à l'utilisateur de base de données de l'application uniquement `SELECT`, `INSERT` et `UPDATE` sur les schémas opérationnels.
4. **Repli de Sécurité des Contrôleurs Physiques :** S'assurer que tous les contrôleurs physiques disposent de modes de clignotement internes configurés selon l'heure de la journée en cas d'interruption des communications.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
