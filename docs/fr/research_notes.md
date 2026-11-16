---
tags: [research, ai, math, neural]
aliases: [Recherche Neuronale, Formulations Mathématiques, PPO-TCN, GOMES]
---

# 🧠 Recherche Neuronale & Formulations Mathématiques

Ce document détaille le cadre mathématique, les architectures de réseaux neuronaux et les formulations curriculaires sous-tendant le système expert multi-agents basé sur les graphes **GOMES** (*Graph-based Operational Multi-agent Expert System*) et le cursus de maturation **DA SILVA** de CARINA.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🏛️ Voir [Architecture Multiprocessus](architecture.md) | 🛡️ Voir [Sécurité & Watchdog](safety_and_watchdog.md) | 🔍 Voir [IA Explicable & SAS](xai_and_sas.md)

---

## 1. PPO-TCN : Réseaux Convolutifs Temporels Causaux Unifiés & Inférence Vectorisée

Les réseaux neuronaux récurrents standards (LSTM/GRU) souffrent de la disparition du gradient et de goulots d'étranglement liés à la rétropropagation séquentielle à travers le temps (BPTT). CARINA remplace les LSTM par un **tronc dorsal TCN causal unifié** ([`src/models/tcn_backbone.py`](../../src/models/tcn_backbone.py)) partagé entre les agents tactique, de sécurité et stratégique :

```text
Historique du Tenseur d'Entrée : X ∈ ℝ^(B × T × C) -> transposé en (B × C × T)
  B : Taille de lot (ou taille de flotte sous torch.vmap)
  C : Caractéristiques par pas de temps (occupation, vitesse, file d'attente, phase, ped_calls + latent PAE)
  T : Fenêtre de contexte temporel (par défaut sequence_length = 12 trames)
```

### 1.1 Convolutions Causales Dilatées, `GroupNorm` et Pooling par Attention

Pour garantir une absence totale de fuite temporelle (la prédiction à l'instant $t$ ne dépend strictement que des instants $\le t$) tout en restant pleinement compatible avec `torch.vmap` et `torch.compile`, `TemporalBlock` remplace `weight_norm` déprécié par `TemporalConv1d`, une normalisation causale par canal `GroupNorm(1, C)`, `SiLU`, une initialisation orthogonale et [`TemporalAttentionPool`](../../src/models/tcn_backbone.py) :

$$y(t) = (x \star_d f)(t) = \sum_{i=0}^{k-1} f(i) \cdot x(t - d \cdot i)$$

Où :
- $k$ : Taille du noyau (*kernel size*, $k = 3$)
- $d$ : Facteur de dilatation ($d = 2^l$ à l'indice de niveau $l \in \{0, 1, 2\}$ sur `num_levels = 3`)
- Taille du champ récepteur (*Receptive Field*) : $RF = 1 + \sum_{l=0}^{L-1} (k - 1) \cdot d_l$

`ActorCriticNet` ([`src/models/actor_critic_tcn.py`](../../src/models/actor_critic_tcn.py)) utilise des troncs Actor et Critic découplés au-dessus de `TemporalAttentionPool`, produisant des logits FP32 bruts (`n_actions = 2` : `0 = ADVANCE`, `1 = KEEP`) masqués directement via [`PhysicalActionMasker`](../../src/engine/physical_action_masker.py) (`apply_action_mask`) pour une distribution `Categorical(logits=...)` sûre sous AMP. Sur les carrefours homogènes, [`FleetBatchInferencer`](../../src/engine/fleet_batch_inferencer.py) exécute l'évaluation de politique en lots via `torch.func.stack_module_state` + `torch.vmap`.

### 1.2 Objectif Substitut Écrêté PPO & GAE NumPy Hôte

Le réseau de politique PPO est optimisé à l'aide de l'objectif substitut tronqué avec estimation d'avantage généralisée (GAE) calculée en NumPy sur l'hôte dans [`PPOOptimizer`](../../src/optimizer/ppo_optimizer.py) et en réutilisant `precomputed_latents` sur `k_epochs` mini-lots :

$$L^{CLIP}(\theta) = \hat{\mathbb{E}}_t \left[ \min \left( r_t(\theta)\hat{A}_t, \text{clip}(r_t(\theta), 1-\epsilon, 1+\epsilon)\hat{A}_t \right) \right]$$

Où :
- $r_t(\theta) = \frac{\pi_\theta(a_t | s_t)}{\pi_{\theta_{old}}(a_t | s_t)}$ est le ratio de probabilité.
- $\hat{A}_t = \sum_{l=0}^{\infty} (\gamma \lambda)^l \delta_{t+l}^V$ est l'estimateur d'avantage GAE.
- $\epsilon = 0.2$ est la limite de troncature de la politique.

---

## 2. Modèle du Monde Universel iTransformer Action-Conditionné (PAE)

L'**Auto-Encodeur Prédictif (PAE)** ([`src/models/pae.py`](../../src/models/pae.py)) est un **Modèle du Monde iTransformer Action-Conditionné** partagé qui projette la dynamique future des voies et l'incertitude épistémique à partir des séquences d'états historiques :

```text
X_hist [B, T, D_in] ──> RevIN par Variable + Plongement Stats [mean, std]
                                 │
                                 ▼ (Attention Inversée sur D_in Variables + key_padding_mask)
                         Encodeur iTransformer + Requêtes Latentes par Attention Croisée (Z ∈ ℝ^latent_dim)
                                 │
                                 ├──> Concaténé aux états de LocalAgent & GuardianAgent
                                 └──> + Plongement d'Action (0=ADVANCE, 1=KEEP) ──> (mean, log_var)
```

### 2.1 Mécanismes Architecturaux Clés
- **RevIN par Variable & Masque de Rembourrage (`pae_preprocessing.py`) :** Découple la dynamique temporelle des échelles statiques de saturation des tronçons via *Reversible Instance Normalization* et masque les dimensions rembourrées de zéros (`valid_dims`) durant le pooling par attention croisée afin que les carrefours comptant moins de voies entrantes ne corrompent jamais les jetons latents.
- **Conditionnement d'Action Contrefactuel & Incertitude Hétéroscédastique :** `decode_with_uncertainty(z, action)` prédit à la fois l'état suivant attendu $\hat{\mu}(z, a)$ et la log-variance $\log \hat{\sigma}^2(z, a)$ pour `0 = ADVANCE` vs `1 = KEEP`.
- **Encodage de Flotte en Passe Unique (`BatchedPAEEncoder`) :** Encode tous les carrefours actifs une fois par pas et compile optionnellement les sous-modules avec `torch.compile` (`torch_compile_helper.py`).

---

## 3. Agent Guardian Distributionnel QR-D3QN & Calibration Noisy-OR

L'**Agent Guardian** ([`src/agents/guardian_agent.py`](../../src/agents/guardian_agent.py), [`src/models/d3qn_tcn.py`](../../src/models/d3qn_tcn.py)) combine un **Dueling Double DQN distributionnel par régression quantile (`QR-D3QN`, `num_quantiles = 32`)** avec une projection cinématique tenant compte de la capacité et une fusion de capteurs calibrée non compensatoire (`src/safety/`) :

$$Z_\tau(s, a) = V_\tau(s) + \left( A_\tau(s, a) - \frac{1}{|\mathcal{A}|} \sum_{a' \in \mathcal{A}} A_\tau(s, a') \right), \quad \tau_k = \frac{k + 0.5}{N}, \; N=32$$

- **Risque de Queue ($\text{CVaR}_{\alpha}$) :** Évalue la valeur à risque conditionnelle sur la queue inférieure ($\alpha = 0.20$) sur `forward_quantiles` plutôt que la seule espérance.
- **Cinématique Normalisée par la Capacité (`GuardianPhysicsEstimator`) :** Extrait strictement les triplets des tronçons entrants (`edge_feature_dim`), normalise les files par la capacité physique de véhicules des voies (`edge_capacities`), projette sur l'horizon de dégagement $H = \text{yellow} + \text{all\_red}$ et calcule le risque UCB contrefactuel du PAE pondéré par la fiabilité dynamique du PAE ($\exp(-\text{MSE}/0.10)\exp(-\overline{\log \sigma^2}/2)$).
- **Calibration Invariante d'Échelle & Fusion Noisy-OR (`GuardianRiskCalibrator`) :** Ajuste une calibration logistique régularisée et des seuils de décision par score $F_2$ lors de la promotion `CHILD`, combinant les détecteurs cinématique ($r_{\text{kin}}$), PAE ($r_{\text{pae}}$) et neuronal ($r_{\text{d3qn}}$) via la fusion Noisy-OR non compensatoire :
  $$P_{\text{spillback}} = 1 - (1 - r_{\text{kin}})(1 - c_{\text{pae}} r_{\text{pae}})(1 - c_{\text{d3qn}} r_{\text{d3qn}})$$
- **Entraînement Ombre `CHILD`-Uniquement & Gel de Déploiement (`GuardianShadowTrainer`) :** Apprend *off-policy* en `Maturity.CHILD` pendant que des plans à temps fixe pilotent le matériel, puis exécute `freeze_for_deployment()` à la promotion (libérant `target_net`, `optimizer` et les tampons PER) et sauvegarde `guardian_{tl_id}.pth`.

---

## 4. Couche Stratégique : ST-GATv2 Lite avec Prédiction en Ligne & CTDE (`src/models/st_gatv2_lite.py`)

Pour coordonner des « Ondes Vertes » sur plusieurs carrefours le long d'artères majeures, CARINA modélise le réseau routier sous forme de graphe orienté $\mathcal{G} = (\mathcal{V}, \mathcal{E})$ à l'aide de `TemporalConvNetLite` + `TemporalAttentionPool` suivis de deux couches résiduelles `GATv2Conv`, d'une tête auxiliaire de prévision à un pas (`pred_head`) et d'une tête critique coopérative CTDE (`global_critic_head`). [`StrategicCoordinator`](../../src/engine/strategic_coordinator.py) échantillonne les séquences via des appels non-mutants [`StateExtractor.peek_state()`](../../src/engine/state_extractor.py).

### 4.1 Poids d'Attention GATv2

Pour les carrefours connectés $i, j \in \mathcal{V}$, GATv2 calcule des coefficients d'attention dynamiques $\alpha_{ij}$ :

$$\alpha_{ij} = \frac{\exp\left( \mathbf{a}^T \text{LeakyReLU}\left( \mathbf{W} [h_i \,\|\, h_j] \right) \right)}{\sum_{k \in \mathcal{N}_i} \exp\left( \mathbf{a}^T \text{LeakyReLU}\left( \mathbf{W} [h_i \,\|\, h_k] \right) \right)}$$

Où :
- $h_i, h_j$ : Représentations de caractéristiques du nœud $i$ et du nœud voisin $j$.
- $\mathbf{W}$ : Matrice de poids partagée.
- $\mathbf{a}$ : Vecteur d'attention apprenable.

---

## 5. Formulation du Cursus de Maturation DA SILVA

Le pipeline **DA SILVA** (*Dynamic Agent Safety Integrated Learning for Validated Autonomy*) évalue la maturité des politiques à l'aide de l'**Entropie de Shannon de la Politique** :

$$\mathcal{H}(\pi_\theta(\cdot | s_t)) = -\sum_{a \in \mathcal{A}} \pi_\theta(a | s_t) \log \pi_\theta(a | s_t)$$

### 5.1 Critères de Progression et Courbe Dynamique de Décroissance de l'Entropie

Afin de garantir que les politiques aléatoires ne soient jamais promues prématurément, la maturité de la politique utilise un plafond d'entropie borné par le nombre d'actions $E_{max} = \ln(|\mathcal{A}|)$ (valant par défaut $E_{max} = \ln(2) \approx 0.6931$ pour l'espace d'actions binaire `ADVANCE`/`KEEP` de CARINA dans `DynamicEntropyCalculator`) ou une entropie normalisée $\mathcal{H}_{norm} = \mathcal{H} / \ln(|\mathcal{A}|) \in [0, 1]$. Le seuil d'admission décroît dynamiquement selon la durée configurée par l'utilisateur ($t$ épisodes) via `DynamicEntropyCalculator` :

$$E(t) = E_{ideal} + (E_{max} - E_{ideal}) \cdot e^{-k \cdot t}$$

Où $E_{ideal} = 0.10$, $k = 0.05$ pour la transition Enfant $\to$ Ado, et $k = 0.15$ pour la transition Ado $\to$ Adulte. Les objectifs de progression asymptotiques nominaux sont :

1. **Stade ENFANT / CHILD (Mode Ombre) :** $\mathcal{H} > E_{child}(t)$ (objectif asymptotique nominal $\mathcal{H} > 0.40$). Les actions sont exécutées strictement en mode ombre (télémétrie passive seule) ; le contrôleur historique pilote les plans de feux matériels tandis que `GuardianShadowTrainer` entraîne QR-D3QN en toute sécurité *off-policy*. Comme $E(t) < \ln(2)$ pour tout $t \ge 1$, une politique aléatoire uniforme ($\mathcal{H} = \ln 2$) est strictement empêchée de graduer. Plancher minimal inviolable : 1 semaine complète ($E_{\text{semaine}}$ épisodes calculés via [`EpisodeStepCalculator`](../../src/utils/episode_step_calculator.py)) pour observer les 168 créneaux horaires réels.
2. **Stade ADOLESCENT / TEEN (Autonomie Restreinte) :** $E_{adult}(t) < \mathcal{H} \le E_{child}(t)$ (plage nominale $0.15 < \mathcal{H} \le 0.40$). L'agent pilote le matériel physique exclusivement hors des heures de pointe (définies par Synapse ou la norme urbaine classique) ; durant les heures de pointe, il bascule en mode ombre pour la sécurité routière. Plancher minimal inviolable : 1 semaine complète ($E_{\text{semaine}}$ épisodes).
3. **Stade ADULTE / ADULT (Autonomie Complète) :** $\mathcal{H} \le E_{adult}(t)$ (objectif asymptotique nominal $\mathcal{H} \le 0.15$, atteint à $t \ge 20$ épisodes avec $k=0.15$) et Récompense Moyenne $\mu_{reward} > \mu_{baseline} + \delta^*$. Autorité d'actionnement autonome 24h/24 et 7j/7 accordée sous toutes les conditions de trafic.

### 5.1.1 Dimensionnement Topologique des Pas et Rythme Hebdomadaire
Pour éliminer les nombres magiques et calibrer l'horizon de chaque épisode sur l'échelle physique du réseau urbain, CARINA emploie [`EpisodeStepCalculator`](../../src/utils/episode_step_calculator.py) :
- **Complexité Topologique ($C_{\text{topo}}$) :** Ratio entre les connexions physiques réelles $E_{\text{real}}$ (unifiant les sens bidirectionnels et ignorant les connecteurs internes avec `:`) et les carrefours à feux $N$, pondéré par la moyenne des voies $\bar{F}$ :
  $$C_{\text{topo}} = \text{clamp}\left( \frac{E_{\text{real}}}{N} \times \left(1.0 + 0.1 \times (\bar{F} - 1.0)\right), \quad 0.8, \quad 1.6 \right)$$
- **Relaxation Sous-Linéaire :** Prévient l'explosion de durée dans les grandes métropoles en indexant sur la profondeur du corridor critique ($\sqrt{N}$) et le diamètre géographique ($D_{\text{km}}$) :
  $$T_{\text{physique}} = 180 + \left( 60 \cdot \sqrt{N} + 30 \cdot D_{\text{km}} \right) \times C_{\text{topo}}$$
- **Pas par Épisode ($S$) :** Conversion pessimiste à $\Delta t = 250\text{ ms}$ ($4\text{ pas/seconde}$), arrondie au multiple supérieur de 100 et bornée entre 2,5 minutes ($600\text{ pas}$) et 1 heure ($14\,400\text{ pas}$) :
  $$S = \text{clamp}\left( \left\lceil \frac{T_{\text{physique}} / 0.25}{100} \right\rceil \times 100, \quad 600, \quad 14400 \right)$$
- **Plancher Inviolable d'Une Semaine ($E_{\text{semaine}}$) :** Nombre minimal d'épisodes requis pour observer exactement 7 jours complets ($604\,800\text{ secondes}$) :
  $$E_{\text{semaine}} = \left\lceil \frac{604800}{S \times 0.25} \right\rceil$$

### 5.1.2 Suivi de Couverture Hebdomadaire et Résilience aux Redémarrages
Pour vérifier que l'évaluation de la politique couvre l'ensemble des conditions réelles de trafic (jours ouvrés, nuits, heures de pointe et week-ends) avant la promotion, [`WeeklyCoverageTracker`](../../src/core/weekly_coverage_tracker.py) collabore avec [`ActionAuthorizer`](../../src/core/action_authorizer.py) :
- **Matrice de 168 Créneaux Calendaires :** Mappe les 168 heures hebdomadaires ($7\text{ jours} \times 24\text{ heures}$). Chaque trame munie d'un horodatage réel (`datetime.fromtimestamp(raw_timestamp)`) enregistre sa présence dans la cellule `(jour_semaine, heure)`.
- **Persistance Atomique :** L'état de couverture est sauvegardé de manière atomique sur disque (`weekly_coverage_CHILD.json` et `weekly_coverage_TEEN.json`), tolérant les pauses et redémarrages sans perte de progression.
- **Régulation des Pointes Classique et Synapse :** La phase `TEEN` n'agit physiquement qu'en dehors des heures de pointe. Si Synapse ne transmet pas de fichier dynamique `peak_schedule.json`, CARINA applique l'ingénierie de trafic classique :
  - *Lundi à Vendredi :* Heures de pointe matinale (**06h30 à 09h00**) et vespérale (**17h00 à 19h30**) en mode ombre.
  - *Week-ends :* Hors-pointe (mode actif autorisé).
- **Évaluation Macroscopique Holistique :** La promotion évalue la performance cumulée sur l'ensemble de la semaine ($\mu_{\text{semaine}} \ge \mu_{\text{baseline}} + \delta^*$), empêchant qu'une anomalie ponctuelle sur un seul jour ne disqualifie une politique par ailleurs sûre.

### 5.1.3 Invariants Inviolables de Sécurité
Pour protéger les infrastructures urbaines critiques contre des configurations imprudentes, des invariants mathématiques stricts sont appliqués :
- **Plancher Temporel Inviolable :** Les opérateurs peuvent configurer une durée d'observation plus longue, mais jamais la réduire en dessous du plancher hebdomadaire :
  $$t_{\min} = \max(E_{\text{semaine}}, \text{configuration\_opérateur})$$
- **Plafond de Certitude (Plancher d'Entropie) :** Les opérateurs peuvent exiger une plus grande certitude (entropie plus faible), mais jamais relâcher le critère pour accepter des politiques chaotiques :
  $$\text{seuil} = \min(E_{\text{calculé}}(t), E_{\text{manuel\_opérateur}})$$

### 5.2 Entraînement Basé sur la Population Intra-Phase (PBT)
Pour assurer l'intégrité biologique et développementale entre les cohortes d'agents, l'exploitation et l'exploration évolutives dans [`PopulationManager`](../../src/core/population_manager.py) opèrent sous une stricte isolation intra-phase :
- **Regroupement en Cohortes :** Les agents s'affrontent, clonent leurs poids et font muter leurs hyperparamètres strictement au sein de leur stade de vie ($\text{TEEN} \leftrightarrow \text{TEEN}$, $\text{ADULT} \leftrightarrow \text{ADULT}$).
- **Protection de l'Enfance :** Les agents au stade `CHILD` sont exemptés de mutations évolutives. Leurs poids neuronaux restent préservés pendant l'observation de la dynamique du réseau physique.
- **Sécurité d'Hétérogénéité Topologique :** Le transfert de poids entre des topologies de carrefours dissemblables est protégé contre les incompatibilités de dimension de tenseur via une validation dimensionnelle à l'exécution.

### 5.3 Marge Dynamique de Performance pour la Graduation ($\delta^*$)
Plutôt que des seuils statiques arbitraires, la marge de graduation requise pour qu'un agent passe de `TEEN` à `ADULT` est calculée en continu à partir de la dynamique des fluides de trafic routier empirique :

$$\delta^* = K \times \left(1 - \frac{\bar{v}_{\text{child}}}{v_{\text{limit}}}\right) \times (1 - \text{occupancy}_{\text{child}}) \times 100\%$$

Où :
- $\left(1 - \frac{\bar{v}_{\text{child}}}{v_{\text{limit}}}\right)$ quantifie l'inefficacité opérationnelle des plans de feux historiques observée pendant l'enfance.
- $(1 - \text{occupancy}_{\text{child}})$ représente la marge de capacité disponible sur la chaussée.
- $K = 0.25$ aligne les objectifs sur les références empiriques des systèmes adaptatifs réels (SCATS / SCOOT : $10\%\text{--}15\%$).
- $\delta^*$ est borné de façon sécurisée à $[3.0\%, 25.0\%]$ afin d'éviter des objectifs inatteignables sur réseaux saturés ou des promotions prématurées sur des couloirs dégagés.

### 5.4 Équilibrage Physique de la Fonction de Récompense (Physique HCM)
CARINA équilibre la fonction de récompense multi-objectifs pour éviter toute disparité dimensionnelle entre les pénalités de retard et les bonus de débit :

$$R(t) = w_{\text{wait}} \times T_{\text{wait}}(t) + w_{\text{flow}} \times F_{\text{discharged}}(t)$$

D'après les formulations du Highway Capacity Manual (HCM), évacuer un véhicule fait gagner le temps de trajet caractéristique du tronçon :

$$\tau = \frac{\bar{L}_{\text{links}}}{\bar{v}_{\text{limit}}}$$

L'algorithme d'équilibrage physique dans [`RewardWeightsCalculator`](../../src/engine/reward_weights_calculator.py) établit :
- $w_{\text{wait}} = -1.0$ (pénalité normalisée de retard par seconde de file d'attente).
- $w_{\text{flow}} = \text{clamp}(2.0, 25.0, \text{round}(\tau \times \alpha, 2))$, garantissant que l'incitation à l'évacuation de véhicules corresponde à l'échelle du retard accumulé en file.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3 ou ultérieure (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
