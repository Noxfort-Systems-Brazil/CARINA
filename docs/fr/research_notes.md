---
tags: [research, ai, math, neural]
aliases: [Recherche Neuronale, Formulations Mathématiques, PPO-TCN, GOMES]
---

# 🧠 Recherche Neuronale & Formulations Mathématiques

Ce document détaille le cadre mathématique, les architectures de réseaux neuronaux et les formulations curriculaires sous-tendant le système expert multi-agents basé sur les graphes **GOMES** (*Graph-based Operational Multi-agent Expert System*) et le cursus de maturation **DA SILVA** de CARINA.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🏛️ Voir [Architecture Multiprocessus](architecture.md) | 🛡️ Voir [Sécurité & Watchdog](safety_and_watchdog.md) | 🔍 Voir [IA Explicable & SAS](xai_and_sas.md)

---

## 1. PPO-TCN : Réseaux Convolutifs Temporels vs LSTMs

Les réseaux neuronaux récurrents standards (LSTM/GRU) souffrent de la disparition du gradient et de la perte du contexte temporel lors de la rétropropagation à travers le temps sur de longs épisodes (BPTT). CARINA remplace les LSTM par un réseau convolutif temporel (**TCN** - *Temporal Convolutional Network*) comme tronc dorsal dans l'Agent Tactique PPO.

```text
Historique du Tenseur d'Entrée : X ∈ ℝ^(B × C × T)
  B : Taille de lot (Batch size)
  C : Caractéristiques par pas de temps (occupation, vitesse, file d'attente, phase)
  T : Fenêtre de contexte temporel (ex. T = 8 secondes à 10Hz = 80 trames)
```

### 1.1 Convolutions Causales Dilatées

Pour garantir une absence totale de fuite temporelle (la prédiction à l'instant $t$ ne dépend que des instants $\le t$), le TCN utilise des convolutions causales dilatées 1D :

$$y(t) = (x \star_d f)(t) = \sum_{i=0}^{k-1} f(i) \cdot x(t - d \cdot i)$$

Où :
- $k$ : Taille du noyau (*kernel size*, $k = 3$)
- $d$ : Facteur de dilatation ($d = 2^l$ à l'indice de couche $l \in \{0, 1, 2, 3\}$)
- Taille du champ récepteur (*Receptive Field*) : $RF = 1 + \sum_{l=0}^{L-1} (k - 1) \cdot d_l$

Le TCN produit un tenseur de représentation temporelle dense $H_{tcn}$, qui alimente les têtes d'Acteur et de Critique du PPO.

### 1.2 Objectif Substitut Éêté PPO (*Clipped Surrogate Objective*)

Le réseau de politique PPO est optimisé à l'aide de l'objectif substitut tronqué avec estimation d'avantage généralisée (GAE) :

$$L^{CLIP}(\theta) = \hat{\mathbb{E}}_t \left[ \min \left( r_t(\theta)\hat{A}_t, \text{clip}(r_t(\theta), 1-\epsilon, 1+\epsilon)\hat{A}_t \right) \right]$$

Où :
- $r_t(\theta) = \frac{\pi_\theta(a_t | s_t)}{\pi_{\theta_{old}}(a_t | s_t)}$ est le ratio de probabilité.
- $\hat{A}_t = \sum_{l=0}^{\infty} (\gamma \lambda)^l \delta_{t+l}^V$ est l'estimateur d'avantage GAE.
- $\epsilon = 0.2$ est la limite de troncature de la politique.

---

## 2. Auto-Encodeur Prédictif (PAE) & Espace Latent $Z$

L'**Auto-Encodeur Prédictif (PAE)** anticipe les remontées de files d'attente de trafic futures à partir des tendances spatio-temporelles passées.

```text
        ┌──────────────┐          ┌───────────────────────┐          ┌──────────────┐
X_hist  │ Encodeur PAE │ ───────> │  Goulot Latent Z      │ ───────> │ Décodeur PAE │ ───> X_pred
(t-8s..t)└──────────────┘          │  Z ∈ ℝ^16             │          └──────────────┘      (t+1s..t+30s)
                                   └───────────────────────┘
```

### 2.1 Fonction de Perte du PAE

Le PAE est entraîné hors ligne et en ligne à l'aide d'une régularisation conjointe par erreur quadratique moyenne (MSE) et divergence de Kullback-Leibler (KL) :

$$\mathcal{L}_{PAE} = \underbrace{\| X_{pred} - X_{future} \|_2^2}_{\text{Perte de Reconstruction & Prédiction}} + \beta \cdot D_{KL}\Big( q_\phi(Z|X) \,\parallel\, \mathcal{N}(0, I) \Big)$$

Le vecteur latent à 16 dimensions $Z \in \mathbb{R}^{16}$ capture l'inertie physique des files d'attente de trafic et est concaténé dans le vecteur d'entrée du PPO.

---

## 3. Agent Guardian Dueling DQN-TCN

L'**Agent Guardian** estime en continu le **Risque de Remontée de File** (*Spillback Risk*) pour chaque voie de carrefour en utilisant un réseau Dueling Deep Q-Network sur les représentations temporelles TCN :

$$Q(s, a; \theta, \alpha, \beta) = V(s; \theta, \beta) + \left( A(s, a; \theta, \alpha) - \frac{1}{|\mathcal{A}|} \sum_{a' \in \mathcal{A}} A(s, a'; \theta, \alpha) \right)$$

Où :
- $V(s)$ : Valeur scalaire de référence de l'état $s$.
- $A(s, a)$ : Avantage procuré par l'action de phase $a$.

Si $\max_a Q(s, a_{spillback}) > \tau_{risk}$ (avec $\tau_{risk} = 0.8$), le Guardian passe outre la phase proposée par l'Agent Tactique et impose une phase d'évacuation d'urgence.

---

## 4. Couche Stratégique : Réseaux d'Attention sur Graphes (GATv2 Lite)

Pour coordonner des « Ondes Vertes » sur plusieurs carrefours le long d'artères majeures, CARINA modélise le réseau routier sous forme de graphe orienté $\mathcal{G} = (\mathcal{V}, \mathcal{E})$.

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

Afin de garantir que les politiques aléatoires ne soient jamais promues prématurément, la maturité de la politique utilise un plafond d'entropie borné par le nombre d'actions $E_{max} = \ln(|\mathcal{A}|)$ (où $E_{max} = \ln(3) \approx 1.0986$ pour 3 actions) ou une entropie normalisée $\mathcal{H}_{norm} = \mathcal{H} / \ln(|\mathcal{A}|) \in [0, 1]$. Le seuil d'admission décroît dynamiquement selon la durée configurée par l'utilisateur ($t$ épisodes) via `DynamicEntropyCalculator` :

$$E(t) = E_{ideal} + (E_{max} - E_{ideal}) \cdot e^{-k \cdot t}$$

Où $E_{ideal} = 0.10$, $k = 0.05$ pour la transition Enfant $\to$ Ado, et $k = 0.15$ pour la transition Ado $\to$ Adulte. Les objectifs de progression asymptotiques nominaux sont :

1. **Stade ENFANT / CHILD (Mode Ombre) :** $\mathcal{H} > E_{child}(t)$ (objectif asymptotique nominal $\mathcal{H} > 0.40$). Les actions sont exécutées en ombre (télémétrie seule) ; le contrôleur historique pilote le matériel. Comme $E(t) < \ln(3)$ pour tout $t \ge 1$, une politique purement aléatoire ($\mathcal{H} = \ln 3$) est strictement empêchée de graduer.
2. **Stade ADOLESCENT / TEEN (Autonomie Restreinte) :** $E_{adult}(t) < \mathcal{H} \le E_{child}(t)$ (plage nominale $0.15 < \mathcal{H} \le 0.40$). L'agent pilote le matériel pendant les heures à faible risque (01h00 - 04h00).
3. **Stade ADULTE / ADULT (Autonomie Complète) :** $\mathcal{H} \le E_{adult}(t)$ (objectif asymptotique nominal $\mathcal{H} \le 0.15$, atteint à $t \ge 20$ épisodes avec $k=0.15$) et Récompense Moyenne $\mu_{reward} > \mu_{baseline} + \delta^*$. Autorité d'actionnement autonome 24h/24 et 7j/7 accordée.

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
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
