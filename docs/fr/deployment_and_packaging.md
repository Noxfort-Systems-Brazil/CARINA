---
tags: [deployment, packaging, docker, debian, systemd]
aliases: [Deployment Guide, Packaging, Docker, Systemd]
---

# 🚀 Déploiement & Configuration de Service

Ce document détaille les options de déploiement en production pour CARINA, y compris la configuration des services Systemd et des environnements d'exécution.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🛠️ Voir [Guides du Développeur](developer_guides.md) | 🗄️ Voir [Base de Données & Schémas](database_and_schemas.md) | 🧪 Voir [Tests & Validation](testing.md) | 🚑 Voir [Préemption EVP](evp_and_preemption.md)

---

## 1. Référence des Ports Réseau & Communications

CARINA coordonne les pipelines multiprocessus locaux, les contrôleurs matériels et les murs d'écrans cloud à l'aide de ports dédiés :

| Port | Protocole | Sous-système / Processus | Description |
| :--- | :--- | :--- | :--- |
| **`50051`** | TCP (gRPC) | CentralController (Synapse HFTLink) | Serveur gRPC externe haute fréquence avec TLS/mTLS & authentification par jeton Bearer optionnels (`CARINA_GRPC_*`). |
| **`8080`** | TCP (WS) | Smart Dashboard Service (SDS) | Serveur WebSocket de télémétrie diffusant les données de file en direct avec contre-pression et délais de 2,0 s. |
| **`2201`** | TCP (HTTP/HTTPS/SSE) | Passerelle Web Go (`src_go/web_gateway`) | Configurable via `CARINA_GATEWAY_PORT` ; en mode fail-closed (`503`) jusqu'à `CARINA_GATEWAY_ENABLED=True` ; protège les points d'accès par jetons & TLS optionnel. |
| **`8085`** | TCP (HTTP/HTTPS) | Récepteur EVP Autonome (`src_go/evp_go`) | Écouteur de télémétrie GPS des véhicules d'urgence prenant en charge l'authentification Bearer/`X-EVP-Token` & TLS. |
| **`42123`** | TCP (Local) | SingleInstanceLock (`single_instance.py`) | Mutex système empêchant les instances d'application dupliquées ; envoie le signal `RESTORE`. |
| **`161`** | UDP (SNMP) | Contrôleurs NTCIP 1202 / UTMC2 | Interrogation SNMPv2c/v3 et maintiens de phase pilotés exclusivement par `CARINA_GATEWAY_ROLE=owner` (`CentralController`). |
| **`162`** | UDP (Trap) | Écouteur de Trappes Matérielles (`traplistener`) | Configurable via `CARINA_TRAP_PORT` ; décode les trappes et informs binaires SNMPv1/v2c/v3. |

---

## 2. Compilation des Sous-Systèmes Clés

Avant de déployer CARINA en production, les binaires natifs et les composants web doivent être compilés :

### 2.1 Compilation de la Passerelle Matérielle & Web Go
Le démon Go compilé gère l'interrogation SNMP des contrôleurs physiques, les maintiens de préemption EVP à la microseconde et la diffusion du mur d'écrans CCO :
```bash
cd src_go
go build -ldflags="-s -w" -o ../bin/carina-go ./cmd/gateway
chmod +x ../bin/carina-go
```

### 2.2 Compilation du Tableau de Bord Web CCO en React
L'interface web Central Control Operator (CCO) réside dans [`src_tsx/`](../../src_tsx) :
```bash
cd src_tsx
npm install
npm run build
```
Vite génère les paquets de production dans `src_tsx/dist/`, qui sont automatiquement servis par la passerelle web Go à l'adresse `http://localhost:2201/cco/`.

---

## 3. Conteneurisation Docker de Production (`Dockerfile`)

CARINA inclut un fichier `Dockerfile` optimisé pour la compilation multi-étapes avec prise en charge de l'accélération GPU :

### 3.1 Construire l'Image Docker
```bash
docker build -t carina-core:latest .
```

### 3.2 Exécuter le Conteneur avec Accélération GPU & Ports Réseau
```bash
docker run -d \
  --name carina_app \
  --gpus all \
  -p 50051:50051 \
  -p 8080:8080 \
  -p 2201:2201 \
  -p 8085:8085 \
  -v /var/log/carina:/app/logs \
  -v /etc/carina:/app/config \
  carina-core:latest
```

---

## 4. Configuration du Démon Linux Systemd

Pour exécuter CARINA en tant que démon système sous Ubuntu/Debian Linux :

Créer le fichier `/etc/systemd/system/carina.service` :

```ini
[Unit]
Description=CARINA AI Real-Time Traffic Orchestrator
After=network.target postgresql.service

[Service]
Type=simple
User=carina
WorkingDirectory=/opt/carina
ExecStart=/usr/bin/python3 /opt/carina/carina.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Recharger et activer le service :
```bash
sudo systemctl daemon-reload
sudo systemctl enable carina
sudo systemctl start carina
```

---

## 5. Passerelle Fail-Closed Zéro-Trust & Déploiement via Tailscale Funnel

Pour les réseaux métropolitains distribués sans IP publique statique :
1. Maintenez `CARINA_GATEWAY_ENABLED=False` (valeur par défaut dans `.env.example` et `config/settings.ini`) jusqu'à ce que les jetons d'authentification et certificats TLS soient provisionnés ; tant qu'elle est désactivée, la Passerelle Web Go renvoie `503 Service Unavailable` sur les points de terminaison CCO/EVP.
2. Générez une clé d'authentification Tailscale dotée des capacités `funnel` depuis la console d'administration Tailscale ainsi que des jetons Bearer robustes pour EVP, CCO et Synapse gRPC.
3. Configurez `.env` :
   ```bash
   CARINA_GATEWAY_ENABLED=True
   CARINA_GATEWAY_PORT=2201
   CARINA_TRAP_PORT=162
   CARINA_EVP_AUTH_TOKEN=<strong-evp-token>
   CARINA_CCO_AUTH_TOKEN=<strong-cco-token>
   CARINA_CCO_ALLOWED_ORIGIN=https://<node-name>.<tailnet>.ts.net
   CARINA_GATEWAY_TLS_CERT=/etc/carina/certs/gateway.crt
   CARINA_GATEWAY_TLS_KEY=/etc/carina/certs/gateway.key
   CARINA_GRPC_AUTH_TOKEN=<strong-grpc-token>
   CARINA_GRPC_TLS_ENABLED=True
   CARINA_OUTPUT_DIR=/var/lib/carina
   CARINA_CONFIG_DIR=/etc/carina
   CARINA_TAILSCALE_AUTH_KEY=tskey-auth-kXXXXX-XXXXXXXX
   ```
4. `CentralController` démarre avec `CARINA_GATEWAY_ROLE=owner` (transmettant les jetons et paramètres TLS à `bin/carina-go`), tandis que les workers UI/AI/SDS s'exécutent en `remote`. [`src_go/web_gateway/tailscale.go`](../../src_go/web_gateway/tailscale.go) enregistre le nœud et déploie un tunnel HTTPS Funnel sur `https://<node-name>.<tailnet>.ts.net:2201`.

---

## 6. Empaquetage & Distribution Hermétique Debian (`.deb`)

CARINA propose un générateur hermétique multi-étapes basé sur Docker et Docker Buildx ([`scripts/build_deb.sh`](../../scripts/build_deb.sh) et [`packaging/Dockerfile.build`](../../packaging/Dockerfile.build)) :

- **Étape 1 (Frontend) :** Compile l'interface cartographique web CCO en React/TypeScript en paquets de production (`node:20-bookworm-slim`).
- **Étape 2 (Passerelle Go) :** Compile `bin/carina-go` nativement sans dépendances CGO (`golang:1.24-alpine`).
- **Étape 3 (Environnement Virtuel Python) :** Configure un environnement isolé dans `/opt/carina/venv` avec Python 3.12, les optimisations processeur de PyTorch et l'ensemble des dépendances (`ubuntu:24.04`).
- **Étape 4 (Empaqueteur Debian) :** Assemble les binaires, configurations, services systemd (`carina.service`) et raccourcis de bureau dans un paquet Debian autonome (`dist/carina_1.0.0_amd64.deb`).

### Compilation du Paquet
Pour compiler un paquet d'installation propre et reproductible :
```bash
./scripts/build_deb.sh
```

### Installation du Paquet
```bash
sudo dpkg -i dist/carina_1.0.0_amd64.deb
sudo apt-get install -f  # Résout les dépendances système facultatives (SUMO, libgl1, etc.)
```
L'installateur configure automatiquement `/opt/carina`, enregistre le service systemd `carina` et crée le lien symbolique vers `/usr/local/bin/carina`.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3 ou ultérieure (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
