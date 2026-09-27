# ⚡ Spécification d'API Synapse HFT et Files IPC

Ce document présente l'interface gRPC Synapse HFT et la topologie des canaux IPC de CARINA.

⬅️ [Hub de Documentation](../README.md) | 🏛️ [Architecture](architecture.md)

---

## 1. Protocole gRPC Synapse HFT (`proto/synapse_hft.proto`)
- **Port d'écoute :** `50051`.
- **Méthodes :**
  - `Ping` : Contrôle de disponibilité sous 1 ms.
  - `LoadScenario` : Transmission de la géométrie du réseau routier.
  - `SystemControl` : Pilotage opérationnel (`START`, `PAUSE`, `STOP`, `RESET`).
  - `StreamTraffic` : Flux continu de données de voies (occupations, vitesses moyennes, files d'attente).

---

## 2. Canaux IPC Mémoire
Isolation complète des tâches critiques via 10 files de mémoire partagée gérées par `ProcessManager` (découplage IA, interface Flet, base de données et supervision).
