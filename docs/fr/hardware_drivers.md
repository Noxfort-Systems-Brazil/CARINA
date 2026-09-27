# 🚦 Pilotes Matériels et Passerelle Go

Ce document spécifie la couche de communication avec les contrôleurs physiques de feux de circulation (Econolite, Siemens, Peek, SWARCO, Yunex) au sein de CARINA.

⬅️ [Hub de Documentation](../README.md) | 🏛️ [Architecture](architecture.md) | 🛡️ [Sécurité](safety_and_watchdog.md)

---

## 1. Passerelle Matérielle Go Dédiée (`bin/carina-go`)
Afin d'éliminer toute latence liée au ramasse-miettes ou au GIL Python, CARINA délègue toutes les communications réseau bas niveau (ports UDP 161 et 162) à un binaire natif autonome développé en Go :
- **Tubes anonymes IPC :** Échanges en NDJSON via les flux `stdin`/`stdout` du noyau Linux. Zéro port TCP/UDP ouvert sur la machine de contrôle.
- **Sécurité et Repli Atomique :** Si le processus Python s'arrête, la fermeture du tube provoque la détection immédiate d'un `EOF` par le démon Go, qui libère instantanément les contrôleurs de terrain via SNMP vers leurs plans de feux fixes locaux.

---

## 2. Standards NTCIP 1202 et UTMC2
- **NTCIP 1202 :** Maintien de vert (`ascPhaseHold`), forçage d'extinction (`ascPhaseForceOff`) et appels virtuels de véhicules.
- **UTMC2 (Norme UK) :** Demandes d'étapes (Stage 1..8) et vérification d'acquittement.
- **Proxy Liskov en Python (`GoTrafficDriverProxy`) :** Intégration transparente avec la classe d'abstraction `BaseTrafficDriver`.
