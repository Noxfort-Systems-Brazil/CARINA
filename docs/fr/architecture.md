# 🏛️ CARINA: Architecture Système et Modèle Multiprocessus

Ce document décrit l'architecture technique du système CARINA : l'orchestration de 8 microservices concurrents isolés par processus, le réseau de neurones profonds spatio-temporel ST-GATv2 Lite, le dimensionnement topologique automatique $O(1)$, l'Agent Consultant PAE et la compression delta sur PostgreSQL.

⬅️ [Hub de Documentation](../README.md) | 🚦 [Pilotes Matériels](hardware_drivers.md) | 🛡️ [Sécurité et Watchdog](safety_and_watchdog.md)

---

## 1. Concurrence Multiprocessus de Haute Performance
Pour contourner le verrou global de l'interpréteur Python (GIL) et garantir des temps de réponse sous la milliseconde, CARINA s'appuie sur une séparation stricte des processus orchestrés par `carina.py` et `src/launcher/process_manager.py` :
- `CentralController` : Contrôle gRPC et coordination temps réel.
- `AI_Process` : Inférence et optimisation des agents d'apprentissage par renforcement.
- `Watchdog` : Surveillance de santé (< 500 ms) et déclencheur de secours.
- `DashboardService (SDS)` : Pont de données pour l'interface Flet et WebSockets.
- `StepDecisionWorker & DatabaseWorker` : Écriture asynchrone non-bloquante.
- `XAI_Worker` : Génération de rapports d'explicabilité et modèles de langage locaux.
- `MFD_Worker` : Calculs du diagramme fondamental macroscopique.

---

## 2. Réseaux de Neurones et Inférence
- **Tactique locale (PPO-TCN) :** Convolutions temporelles causales dilatées pour le réglage dynamique des durées de vert.
- **Coordination spatiale (ST-GATv2 Lite) :** Synchronisation dynamique des ondes vertes à travers les avenues urbaines.
- **Consultant Global (PAE) :** Auto-encodeur prédictif à 128 canaux projetant les tendances de trafic futures.
- **Accélération AMP :** Inférence native en FP16 via TensorCores NVIDIA (empreinte VRAM ~20 Mo).

---

## 3. Stockage Delta et Passerelle Go
- **PostgreSQL Delta Compression :** 97.9% de réduction de stockage grâce à l'encodage par plages de valeurs identiques.
- **Passerelle Go (`bin/carina-go`) :** Gestion exclusive des ports UDP 161 (SNMP) et 162 (Traps) via des tubes anonymes sans ouverture de port réseau sur l'hôte.
- **Auto-Résilience F.E.N.I.X. :** Supervision de processus et reprise en douceur sur transition de phase sans risque de collision.
