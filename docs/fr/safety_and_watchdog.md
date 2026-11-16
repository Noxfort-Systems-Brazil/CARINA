---
tags: [safety, guardian, watchdog, veto, failsafe, neuro-symbolic]
aliases: [Safety Architecture, Guardian Veto, Watchdog System, Safety Auditor]
---

# 🛡️ Architecture de Sécurité, Pare-Feu Guardian & Watchdog

Ce document détaille le pare-feu de sécurité neuro-symbolique à double étage de CARINA ([`GuardianAgent`](../../src/agents/guardian_agent.py) & [`SafetyAuditor`](../../src/core/safety_auditor.py)), les mécanismes de repli de sécurité matériel (*fail-safe*) et le processus déterministe temps réel [`Watchdog`](../../src/watchdog/watchdog_process.py).

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🚨 Voir [Préemption EVP](evp_and_preemption.md) | 🚦 Voir [Pilotes Matériels](hardware_drivers.md) | 🧠 Voir [Formulations Neuronales](research_notes.md) | 🧪 Voir [Tests & Validation](testing.md)

---

## 1. Vue d'Ensemble du Pare-Feu de Sécurité à Double Étage

CARINA découple entièrement la sécurité publique physique des performances de l'apprentissage par renforcement profond. Les politiques neuronales peuvent proposer des actions, mais toutes les actions passent par un masquage physique des logits et une vérification de sécurité multi-étages avant d'être expédiées au matériel physique :

```text
État + Latent PAE ──> [PhysicalActionMasker] ──> [ActionVetoResolver] ──> Actionnement
                       (Masque Dég./VertMin)     ├── 0. Interception Priorité EVP (SR-00)
                                                 ├── 1. Règles Symboliques (SR-01..SR-06)
                                                 └── 2. Veto de Risque QR-D3QN + Noisy-OR
```

- [`PhysicalActionMasker`](../../src/engine/physical_action_masker.py) : Contraint les logits FP32 de `ActorCriticNet` avant l'échantillonnage, interdisant les changements prématurés pendant le dégagement jaune/tout-rouge ou sous le vert minimal, et forçant les transitions au-delà du vert maximal.
- [`ActionVetoResolver`](../../src/engine/action_veto_resolver.py) : Orchestre les dérogations de préemption EVP (`SR-00`) et les vetos anti-remontée de file de `GuardianAgent` (`ACTION_KEEP_STAGE`) dans le pipeline d'exécution par pas.

---

## 2. Inventaire des Règles de Veto Symbolique (`SafetyAuditor`)

Le [`SafetyAuditor`](../../src/core/safety_auditor.py) et le [`GuardianSymbolicAuditor`](../../src/safety/guardian_symbolic_auditor.py) appliquent des contraintes physiques strictes qui ne peuvent jamais être relâchées, modifiées ou contournées par l'optimisation des réseaux neuronaux :

| ID Règle | Nom | Description de la Contrainte | Action en Cas de Violation |
| :--- | :--- | :--- | :--- |
| **SR-00** | **Préemption d'Urgence (EVP)** | Véhicule d'urgence actif (SAMU/Pompiers/Police) en approche avec sirène enclenchée. | Intercepter l'action ; appliquer un dégagement jaune/rouge intégral sécurisé, puis injecter `ACTION_HOLD` sur le couloir vert cible. |
| **SR-01** | **Temps Vert Minimal** | La phase active doit rester verte pendant au moins $T_{min} = 7.0\text{ s}$ pour évacuer les véhicules en file. | Forcer `ACTION_KEEP_PHASE`. |
| **SR-02** | **Dégagement Jaune** | Toute transition de phase doit obligatoirement respecter un intervalle d'avertissement jaune de $3.0\text{ s}$. | Intercepter l'action ; injecter la phase Jaune. |
| **SR-03** | **Intervalle Tout-Rouge** | Les mouvements directionnels en conflit nécessitent un intervalle de dégagement tout-rouge de $2.0\text{ s}$. | Injecter l'état de dégagement Tout-Rouge. |
| **SR-04** | **Temps Rouge Minimal** | Les mouvements non desservis doivent respecter un intervalle rouge minimal avant d'être réactivés. | Inhiber la réactivation prématurée de la phase. |
| **SR-05** | **Plafond Vert Maximal (Anti-Famine)** | Une phase ne peut excéder la durée verte maximale si des approches concurrentes ont des files d'attente. | Forcer la terminaison de la phase et la transition vers la demande en attente. |
| **SR-06** | **Matrice de Conflit & Vert Fantôme** | Empêche l'affichage simultané d'indications vertes sur des voies conflictuelles ou sur des axes sans débit. | Veto strict ; repli vers l'état de repos sécurisé. |

---

## 3. Veto Neuronal Calibré de Remontée de File (*Spillback*) (`GuardianAgent` & `src/safety/`)

L'**Agent Guardian** ([`src/agents/guardian_agent.py`](../../src/agents/guardian_agent.py)) intègre un **Dueling Double DQN distributionnel par régression quantile (`D3QN_TCN`, `num_quantiles = 32`)** à une physique cinématique tenant compte de la capacité et à une fusion de risques non compensatoire :

- **Estimation Quantile du Risque de Queue ($\text{CVaR}_{\alpha}$) :** `GuardianNeuralPredictor` évalue les quantiles inférieurs du pire cas ($\alpha = 0.20$) plutôt que les seules valeurs Q moyennes.
- **Estimation Physique Cinématique & PAE ([`GuardianPhysicsEstimator`](../../src/safety/guardian_physics_estimator.py)) :** Extrait strictement les triplets de capteurs des tronçons entrants (`edge_feature_dim`), normalise les files par rapport aux capacités physiques de véhicules des voies (`edge_capacities`), projette la croissance de saturation sur l'horizon de dégagement inter-vert $H = \text{yellow} + \text{all\_red}$ et interroge les prévisions contrefactuelles du PAE (`decode_with_uncertainty` pour `ADVANCE` vs `KEEP`).
- **Calibration Invariante d'Échelle & Fusion Noisy-OR ([`GuardianRiskCalibrator`](../../src/safety/guardian_risk_calibrator.py)) :** Calibre les écarts quantiles par régression logistique régularisée et réglage du seuil par score $F_2$ lors de la promotion `CHILD`, combinant les risques physique, PAE et QR-D3QN via la fusion Noisy-OR non compensatoire ($1 - \prod_i (1 - c_i r_i)$) et un plancher strict de remontée de file physique/PAE.
- **Entraînement Ombre Sûr `CHILD`-Uniquement & Gel ([`GuardianShadowTrainer`](../../src/safety/guardian_shadow_trainer.py) & [`GuardianCheckpointService`](../../src/safety/guardian_checkpoint_service.py)) :** Entraîne QR-D3QN *off-policy* exclusivement pendant `Maturity.CHILD` tandis que les feux physiques suivent des plans à temps fixe ; lors de la promotion vers `TEEN`/`ADULT`, exécute `finalize_child_calibration()` et `freeze_for_deployment()` (libérant `target_net`, `optimizer` et les tampons PER) et persiste atomiquement `guardian_{tl_id}.pth`.

---

## 4. Watchdog de Processus Temps Réel (`src/watchdog/`)

Le microservice `Watchdog` ([`src/watchdog/watchdog_process.py`](../../src/watchdog/watchdog_process.py) et [`src/watchdog/watchdog_logic.py`](../../src/watchdog/watchdog_logic.py)) surveille la vivacité des 8 microservices de CARINA :

- **Intervalle de Pulsation (*Heartbeat*) :** 100 ms via la file IPC `wd`.
- **Délai d'Expiration de Pulsation :** 5,0 secondes (période de grâce initiale : 10 secondes).
- **Mécanisme Fail-Safe :** Si `AI_Process` ou `CentralController` plante, subit un interblocage (*deadlock*) ou manque des pulsations consécutives :
  1. Le Watchdog notifie la zone de notification de l'IHM bureautique.
  2. Il signale au [`FailsafeManager`](../../src/controller/failsafe_manager.py) -> `HardwareGatewayCoordinator.on_failsafe_triggered()`, invoquant `EmergencyReleaseControlAll()` sur la passerelle Go (relâchant les maintiens tout en gardant les pilotes SNMP et l'écouteur de trappes prêts pour `resume_control` lors de la reprise).
  3. Les contrôleurs de feux physiques basculent de manière autonome vers des plans locaux à temps fixe ou en clignotant jaune.
  4. Déclenche le **Superviseur de Processus F.E.N.I.X.** (`on_fenix_trigger` via la file `fenix` et [`fenix_supervision_loop.py`](../../src/launcher/fenix_supervision_loop.py)) pour engager la récupération autonome et la réconciliation d'état en boucle fermée.
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

### 5.3 Transfert d'Autorité sur Limite Sécurisée (`StateReconciler` & `FenixStageDispatcher`)
Situé dans [`src/fenix/state_reconciler.py`](../../src/fenix/state_reconciler.py) et [`src/controller/fenix_stage_dispatcher.py`](../../src/controller/fenix_stage_dispatcher.py) :
- **Risque de Collision en Mi-Étape :** Lorsque le processus IA ressuscite, injecter des commandes au milieu d'une étape d'un carrefour physique pourrait violer les intervalles de dégagement ou causer des changements brutaux de feux.
- **Poignée de Main Terrain en Boucle Fermée :** `FenixStageDispatcher` interroge des instantanés frais des contrôleurs auprès de la passerelle Go, décode les étapes terrain actives via [`HardwareTelemetryDecoder`](../../src/drivers/hardware_telemetry_decoder.py) et réconcilie `StateReconciler` (`reconcile_with_field` via `fenix_post_resurrection`).
- **Déverrouillage lors de la Transition de Phase :** Le contrôle neuronal est déverrouillé (`on_stage_transition_detected`) lorsque le contrôleur physique effectue la transition vers une limite d'étape sûre, émettant `fenix_handover_complete` -> `HANDOVER_COMPLETE` afin que `FenixSupervisor` confirme la résurrection et reprenne les pulsations (`resume_control`).

---

Pour les détails sur la communication avec les contrôleurs physiques, voir [Pilotes Matériels](hardware_drivers.md).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3 ou ultérieure (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
