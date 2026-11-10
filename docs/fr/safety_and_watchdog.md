---
tags: [safety, guardian, watchdog, veto, failsafe, neuro-symbolic]
aliases: [Safety Architecture, Guardian Veto, Watchdog System, Safety Auditor]
---

# 🛡️ Architecture de Sécurité, Pare-Feu Guardian & Watchdog

Ce document détaille le pare-feu de sécurité neuro-symbolique à double étage de CARINA ([`GuardianAgent`](../../src/agents/guardian_agent.py) & [`SafetyAuditor`](../../src/core/safety_auditor.py)), les mécanismes de repli de sécurité matériel (*fail-safe*) et le processus déterministe temps réel [`Watchdog`](../../src/watchdog/watchdog_process.py).

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🚨 Voir [Préemption EVP](evp_and_preemption.md) | 🚦 Voir [Pilotes Matériels](hardware_drivers.md) | 🧠 Voir [Formulations Neuronales](research_notes.md) | 🧪 Voir [Tests & Validation](testing.md)

---

## 1. Vue d'Ensemble du Pare-Feu de Sécurité à Double Étage

CARINA découple entièrement la sécurité publique physique des performances de l'apprentissage par renforcement profond. Les politiques neuronales peuvent proposer des actions, mais toutes les actions doivent obligatoirement être validées formellement par un pare-feu de sécurité avant d'être expédiées au matériel physique :

```text
Action de Phase Proposée ──> [0. Interception Priorité EVP] ──> [1. Règles Symboliques] ──> [2. Veto Neuronal] ──> Actionnement
                                     │                                  │                           │
                                     ├── Couloir d'Urgence (HOLD)       ├── Vert Min / Jaune        └── Remontée de File (Q > 0.8)
                                     └── Contrôle Dégagement Obligatoire └── Veto de Conflit         └── Dégagement d'Urgence
```

---

## 2. Inventaire des Règles de Veto Symbolique (`SafetyAuditor`)

Le [`SafetyAuditor`](../../src/core/safety_auditor.py) applique des contraintes physiques strictes qui ne peuvent jamais être relâchées, modifiées ou contournées par l'optimisation des réseaux neuronaux :

| ID Règle | Nom | Description de la Contrainte | Action en Cas de Violation |
| :--- | :--- | :--- | :--- |
| **SR-00** | **Préemption d'Urgence (EVP)** | Véhicule d'urgence actif (SAMU/Pompiers/Police) en approche avec sirène enclenchée. | Intercepter l'action ; appliquer un dégagement jaune/rouge intégral sécurisé, puis injecter `ACTION_HOLD` sur le couloir vert cible. |
| **SR-01** | **Temps Vert Minimal** | La phase active doit rester verte pendant au moins $T_{min} = 7.0\text{ s}$ pour évacuer les véhicules en file. | Forcer `ACTION_KEEP_PHASE`. |
| **SR-02** | **Dégagement Jaune** | Toute transition de phase doit obligatoirement respecter un intervalle d'avertissement jaune de $3.0\text{ s}$. | Intercepter l'action ; injecter la phase Jaune. |
| **SR-03** | **Intervalle Tout-Rouge** | Les mouvements directionnels en conflit nécessitent un intervalle de dégagement tout-rouge de $2.0\text{ s}$. | Injecter l'état de dégagement Tout-Rouge. |
| **SR-04** | **Protection Piétons** | Les boutons-poussoirs piétons activés garantissent un intervalle piéton/clignotant ininterrompu. | Bloquer les mouvements véhiculaires conflictuels. |
| **SR-05** | **Matrice de Conflit** | Empêche l'affichage simultané d'indications vertes sur des voies conflictuelles ou sécantes. | Veto strict ; repli vers l'état de repos sécurisé. |

---

## 3. Veto Neuronal de Remontée de File (*Spillback*) (`GuardianAgent`)

L'**Agent Guardian** ([`src/agents/guardian_agent.py`](../../src/agents/guardian_agent.py)) exécute un réseau Dueling Deep Q-Network sur les représentations temporelles TCN afin d'estimer le **Risque de Remontée de File** ($Q_{risk} \in [0.0, 1.0]$) :

- **Seuil ($\tau_{risk}$) :** $0.80$ (configurable dans `config/settings.ini`).
- **Dérogation d'Urgence :** Si $Q(s, a_{proposee}) > 0.80$, la proposition de l'agent tactique est rejetée par veto. Le Guardian injecte une phase d'évacuation d'urgence pour décharger l'artère congestionnée avant que le blocage amont ne se produise.

---

## 4. Watchdog de Processus Temps Réel (`src/watchdog/`)

Le microservice `Watchdog` ([`src/watchdog/watchdog_process.py`](../../src/watchdog/watchdog_process.py) et [`src/watchdog/watchdog_logic.py`](../../src/watchdog/watchdog_logic.py)) surveille la vivacité des 8 microservices de CARINA :

- **Intervalle de Pulsation (*Heartbeat*) :** 100 ms via la file IPC `wd`.
- **Délai d'Expiration de Pulsation :** 5,0 secondes (période de grâce initiale : 10 secondes).
- **Mécanisme Fail-Safe :** Si `AI_Process` ou `CentralController` plante, subit un interblocage (*deadlock*) ou manque des pulsations consécutives :
  1. Le Watchdog notifie la zone de notification de l'IHM bureautique.
  2. Il signale immédiatement au [`FailsafeManager`](../../src/controller/failsafe_manager.py) de relâcher les maintiens de phase sur les contrôleurs physiques.
  3. Les contrôleurs de feux physiques basculent de manière autonome vers des plans locaux à temps fixe ou en clignotant jaune.
  4. Déclenche le **Superviseur de Processus F.E.N.I.X.** (`on_fenix_trigger`) pour engager la récupération autonome et la réconciliation d'état.
  5. **Watchdog de Maintien de Préemption :** En parallèle, [`EVPPreemptionEngine`](../../src/evp/evp_preemption_engine.py) impose un délai maximal strict de préemption de $45.0\text{ s}$, libérant les blocages artériels si la sortie du véhicule (*checkout*) tarde ou est omise.

---

## 5. Architecture d'Auto-Guérison F.E.N.I.X. & Récupération après Crash (`src/fenix/`)

Pour parvenir à une résilience autonome 24h/24 et 7j/7 sans intervention manuelle d'un opérateur, CARINA intègre **F.E.N.I.X.** (*Fault-tolerant Engine for Networked Intelligent eXecution*) dans [`src/fenix/`](../../src/fenix).

```text
       Délai Expiré Watchdog / Crash de Processus
                      │
                      ▼
           ┌─────────────────────┐
           │   FenixSupervisor   │ (Façade de l'Orchestrateur)
           └──────────┬──────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
 ┌──────────────────┐     ┌──────────────────────┐
 │  RecoveryPolicy  │     │   SubprocessRunner   │
 │(Backoff Fenêtré) │     │(SIGTERM -> SIGKILL)  │
 └──────────────────┘     └──────────┬───────────┘
                                     │ Génère Nouveau Processus Enfant
                                     ▼
                          ┌──────────────────────┐
                          │   StateReconciler    │
                          │(Mode FROZEN_SYNC)    │
                          └──────────┬───────────┘
                                     │ Attente Prochaine Transition (Zéro Risque de Collision)
                                     ▼
                          ┌──────────────────────┐
                          │    NORMAL (Actif)    │
                          └──────────────────────┘
```

### 5.1 États du Cycle de Vie F.E.N.I.X. (`FenixState`)
Définis dans [`src/fenix/protocols.py`](../../src/fenix/protocols.py) :
- **`IDLE`** : État initial avant le démarrage de la supervision des processus.
- **`NORMAL`** : Le moteur d'IA supervisé fonctionne nominalement avec une autorité d'actionnement totale.
- **`SUSPECT`** : Pulsation de processus manquée ou télémétrie anormale détectée par le Watchdog.
- **`RESTARTING`** : Processus zombie terminé ; en attente de la fenêtre de temporisation (*backoff*) avant relance.
- **`FROZEN_SYNC`** : Le processus ressuscité reçoit la télémétrie en direct, mais l'inférence neuronale et les commandes d'actionnement sont strictement verrouillées (`is_inference_allowed = False`).
- **`SHADOW_WARMUP`** : Les passes avant en arrière-plan préchauffent les caches PyTorch et les plongements de nœuds GATv2.
- **`HANDOVER_PENDING`** : Attente que les contrôleurs physiques effectuent la transition vers une limite d'étape sécurisée.
- **`FAILSAFE_ACTIVE`** : Mode de repli dans lequel les contrôleurs physiques exécutent des plans autonomes à temps fixe pendant l'exécution de la récupération.
- **`HALTED`** : Quota maximal de plantages dépassé dans la fenêtre glissante ; verrouille le système en repli sécurisé et alerte les opérateurs.

### 5.2 Politique de Récupération après Crash Fenêtrée (`WindowedCrashRecoveryPolicy`)
Situé dans [`src/fenix/recovery_policy.py`](../../src/fenix/recovery_policy.py) :
- Enregistre les plantages de processus dans une fenêtre temporelle glissante (par défaut : $300\text{ s}$).
- Calcule un recul exponentiel entre les tentatives de redémarrage ($2.0\text{ s} \to 4.0\text{ s} \to 8.0\text{ s}$).
- Prévient les boucles infinies de redémarrage : si le taux de plantage dépasse $M$ défaillances (par défaut : 5), bascule vers `HALTED`.

### 5.3 Transfert d'Autorité sur Limite Sécurisée (`StateReconciler`)
Situé dans [`src/fenix/state_reconciler.py`](../../src/fenix/state_reconciler.py) :
- **Risque de Collision en Mi-Étape :** Lorsque le processus IA ressuscite, injecter des commandes au milieu d'une étape d'un carrefour physique pourrait violer les intervalles de dégagement ou causer des changements brutaux de feux.
- **Négociation à Zéro Risque (*Handshake*) :** Le réconciliateur interroge les étapes actuelles des contrôleurs physiques (`reconcile_with_field`).
- **Déverrouillage lors de la Transition de Phase :** Le contrôle neuronal n'est déverrouillé (`on_stage_transition_detected`) que lorsque le contrôleur physique effectue naturellement sa transition vers sa prochaine étape locale, garantissant une reprise sans heurts et sans risque de collision.

---

Pour les détails sur la communication avec les contrôleurs physiques, voir [Pilotes Matériels](hardware_drivers.md).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
