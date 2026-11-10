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
| **`50051`** | TCP (gRPC) | CentralController $\leftrightarrow$ Microservices | Bus RPC interne pour les trames de télémétrie et les requêtes d'actions neuronales. |
| **`8080`** | TCP (WS) | Smart Dashboard Service (SDS) | Serveur WebSocket de télémétrie diffusant les données de file en direct aux clients web. |
| **`2201`** | TCP (HTTP/SSE) | Passerelle Web Go (`src_go/web_gateway`) | Entrée principale périphérique : `POST /api/v1/evp/telemetry` (HTTP 204), `GET /cco/stream` (SSE) et tableau de bord CCO. |
| **`8085`** | TCP (HTTP) | Récepteur EVP Autonome (`src/evp`) | Écouteur de repli pour la télémétrie GPS des véhicules d'urgence lorsque la passerelle Go est inactive. |
| **`42123`** | TCP (Local) | SingleInstanceLock (`single_instance.py`) | Mutex système empêchant les instances d'application dupliquées ; envoie le signal `RESTORE`. |
| **`161`** | UDP (SNMP) | Contrôleurs de Terrain NTCIP 1202 / UTMC | Interrogation et contrôle de maintien de phase (`ascPhaseHold`) envoyés aux têtes de feux tricolores. |
| **`162`** | UDP (Trap) | Écouteur de Trappes Matérielles (`traplistener`) | Ingestion des trappes de pannes matérielles asynchrones et des activations de détecteurs. |

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

## 5. Déploiement Réseau Zéro-Trust via Tailscale Funnel

Pour les réseaux métropolitains distribués sans IP publique statique :
1. Générer une clé d'authentification Tailscale avec les fonctionnalités `funnel` depuis la console d'administration Tailscale.
2. Configurer `.env` :
   ```bash
   CARINA_GATEWAY_ENABLED=true
   CARINA_GATEWAY_PORT=2201
   CARINA_TAILSCALE_AUTH_KEY=tskey-auth-kXXXXX-XXXXXXXX
   ```
3. Lorsque la passerelle Go démarre, [`src_go/web_gateway/tailscale.go`](../../src_go/web_gateway/tailscale.go) enregistre automatiquement le nœud et démarre un tunnel HTTPS Funnel sur `https://<node-name>.<tailnet>.ts.net:2201`, exposant l'API EVP et le mur d'écrans CCO via TLS public sans aucune modification de pare-feu.

---

## 6. Empaquetage & Distribution

Les solutions historiques d'empaquetage PyInstaller et paquets `.deb` via `build_installer.sh` ont été dépréciées et retirées. Un pipeline moderne de distribution et d'installation entièrement conteneurisé est prévu pour les prochaines versions.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
