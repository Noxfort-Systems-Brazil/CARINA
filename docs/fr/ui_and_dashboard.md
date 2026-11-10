---
tags: [ui, flet, dashboard, frontend, sds, planning, widgets]
aliases: [Architecture UI, Service Dashboard, Frontend Flet, Vue de Planification]
---

# 🖥️ Architecture UI, Vue de Planification & Service de Tableau de Bord Intelligent (SDS)

Ce document spécifie l'interface utilisateur bureautique native de CARINA située dans [`ui/`](../../ui), le **Smart Dashboard Service (SDS)** dans [`src/sds/`](../../src/sds), le **Gestionnaire de Zone de Notification (System Tray)** et le système de verrouillage d'instance unique.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🗺️ Voir [Rendu & Cartes Thermiques](rendering_and_heatmaps.md) | 🔍 Voir [IA Explicable & SAS](xai_and_sas.md) | 🚑 Voir [Préemption EVP](evp_and_preemption.md)

---

## 1. Architecture Bureautique Découplée (`ui/` & `src/sds/`)

Pour empêcher que le rendu graphique de l'IHM ou la latence des sockets de navigateur client ne fassent perdre des trames de contrôle du trafic en temps réel, CARINA découple complètement son frontend au sein du processus **`DashboardService` (SDS)** ([`run_sds_worker`](../../src/sds/dashboard_worker.py)).

```text
CentralController (gRPC) ──> [File sds] ──> DashboardService (SDS) ──> [File ui] ──> Flet UI (Thread Principal)
                                                   │
                                                   └──> Serveur WebSocket de Télémétrie (port 8080)
```

---

## 2. Architecture Réelle de l'IHM Flet & Hiérarchie des Vues

Le frontend est développé avec **[Flet](https://flet.dev/)** (moteur Python + Flutter) situé dans [`ui/`](../../ui).

```text
ui/
├── main_ui.py                      # Amorçage principal de l'application Flet & configuration de la fenêtre
│
├── views/                          # Vues d'Écran de l'Application
│   ├── dashboard_view.py           # Surveillance du trafic en temps réel & canvas cartographique interactif
│   ├── planning_view.py            # Planification de la topologie, minutage des phases & regroupement de voies
│   ├── diagnostics_view.py         # Métriques de latence IPC, utilisation mémoire & moniteurs de processus
│   ├── system_status_view.py       # État actif des microservices & statuts des contrôleurs physiques
│   ├── settings_view.py            # Configuration système & éditeur de points de terminaison IP contrôleurs
│   └── error_view.py               # Capture globale d'erreurs & vue des exceptions de diagnostic
│
├── cards/                          # Cartes Modulaires de Paramètres & d'Inspection (Patron OCP)
│   ├── evp_fleet_connection_card.py    # Enregistrement de la flotte d'urgence & config RFID/transpondeurs
│   ├── evp_safety_parameters_card.py  # Portes de distance de préemption, watchdog de maintien max & dégagement
│   ├── remote_gateway_card.py          # Bascules de la passerelle Web Go, port 2201 & statut mesh Tailscale
│   ├── account_settings_card.py        # Profil utilisateur opérateur, rôles (RBAC) & identifiants
│   ├── database_settings_card.py       # Sélection moteur base de données (SQLite/PostgreSQL) & migrations
│   ├── hardware_connection_card.py     # Pool de connexion contrôleurs de terrain NTCIP 1202 & UTMC
│   ├── piloting_school_card.py         # Rythme PBT autonome & seuils de graduation RL
│   ├── reward_weights_card.py          # Équilibrage des récompenses : retard, pression, file & vitesse
│   ├── traffic_rules_card.py           # Contraintes de vert minimal, dégagement jaune & tout-rouge
│   ├── yellow_schedule_card.py         # Programmation automatisée de jaune clignotant nocturne
│   ├── monitor_settings_card.py        # Télémétrie externe courtier MQTT / webhook HTTP
│   ├── advanced_system_card.py         # Délais d'expiration watchdog, tailles de tampons IPC & pulsations
│   ├── advanced_dqn_card.py            # Taille mémoire replay DQN, synchro réseau cible & epsilon
│   └── advanced_ppo_card.py            # Ratio clip PPO, coefficient d'entropie & coef perte de valeur
│
├── widgets/                        # Widgets d'IHM Modulaires Spécialisés
│   ├── live_canvas_map_widget.py   # Dessin canvas personnalisé haute performance pour routes et feux
│   ├── evp_vehicle_marker.py       # Rendu canvas personnalisé pour véhicules d'urgence (formes & gyrophares)
│   ├── evp_vehicle_card.py         # Carte flottante affichant GPS temps réel, vitesse & ETA
│   ├── planning_control_panel_widget.py # Barres d'outils de planification, sélecteurs d'étape & inspecteur
│   ├── mfd_viewer_widget.py        # Traceur de courbe du Diagramme Fondamental Macroscopique en direct
│   ├── xai_viewer_widget.py        # Graphiques de répartition d'attribution de caractéristiques Captum
│   ├── street_info_widget.py       # Relevés par voie : vitesse, occupation & longueur de file
│   ├── traffic_light_widget.py     # Animations en direct des têtes de feux (Rouge, Jaune, Vert)
│   ├── audit_log_widget.py         # Tableau d'inspection médico-légale des vetos de sécurité Guardian
│   └── global_controls_widget.py   # Boutons Démarrer, Pause, Pas à Pas & Dérogation d'Urgence
│
├── renderers/                      # Dessin Canvas & Synchronisation Visuelle
│   ├── map_drawer.py               # Rastériseur de géométrie vectorielle pour voies et carrefours
│   ├── planning_map_renderer.py    # Moteur de disposition visuelle pour nœuds topologiques
│   └── map_visual_syncer.py        # Synchroniseur d'animations fluides à 60 FPS
│
└── locales/                        # Dictionnaires d'Internationalisation (i18n)
    ├── pt_br.json                  # Portugais (Brésil) - Par défaut
    ├── en_us.json                  # Anglais (États-Unis)
    ├── es_es.json                  # Espagnol
    ├── fr_fr.json                  # Français
    ├── ru_ru.json                  # Russe
    └── zh_cn.json                  # Chinois Simplifié
```

---

## 3. Vue de Planification & Éditeur de Topologie de Réseau

La **Vue de Planification** ([`ui/views/planning_view.py`](../../ui/views/planning_view.py)) permet aux ingénieurs municipaux de la circulation d'inspecter et de configurer de manière interactive les réseaux routiers physiques :
- **Regroupement Topologique :** Regrouper des grappes de carrefours en couloirs artériels coordonnés (Ondes Vertes).
- **Inspecteur de Phases & d'Étapes :** Inspecter les contraintes de vert minimal, le dégagement jaune et les tampons d'intergreen tout-rouge.
- **Gestionnaire d'Export :** Exporter les plans de feux modifiés directement vers les dépôts de connexion des contrôleurs ou vers des modèles CSV.

Pour les détails du rendu de carte vectorielle, voir [Rendu Cartographique & Cartes Thermiques](rendering_and_heatmaps.md).

---

## 4. Zone de Notification & Verrouillage d'Instance Unique (`SingleInstanceLock`)

CARINA s'exécute de façon transparente en arrière-plan comme un démon système doté d'une icône native dans la zone de notification (*system tray*) :

### 4.1 Gestion de la Zone de Notification ([`UITrayManager`](../../src/launcher/ui_tray_manager.py))
- **Actions de la Zone :** Réduire dans la barre d'état, Ouvrir le Tableau de Bord, Consulter les Journaux en Direct, Redémarrer les Services, Arrêt Propre.
- **Notifications Fenêtrées :** Émet des notifications natives du système d'exploitation lorsque le Watchdog détecte des plantages de microservices ou lorsque l'Agent Guardian déclenche un veto de sécurité d'urgence.

### 4.2 Verrouillage d'Instance Unique ([`SingleInstanceLock`](../../src/launcher/single_instance.py))
- **Port :** `42123`
- Si un utilisateur double-clique sur `carina.py` ou l'exécutable alors que CARINA est déjà en cours d'exécution :
  1. Le processus dupliqué tente de se lier au port TCP `42123`.
  2. En cas d'échec, il transmet un signal de commande `RESTORE` sur le socket TCP local à l'instance principale.
  3. L'instance principale place la fenêtre Flet au premier plan, et le processus dupliqué s'arrête proprement.

---

## 5. Architecture des Cartes Modulaires de Paramètres (`ui/cards/`)

La vue de configuration de CARINA ([`ui/views/settings_view.py`](../../ui/views/settings_view.py)) respecte une architecture de composants ouverts/fermés (OCP) assemblée via [`SettingsConfigurator`](../../ui/builders/settings_configurator.py) :

| Composant de Carte | Description | Modes Auto / Manuel |
| :--- | :--- | :--- |
| **`EVPFleetConnectionCard`** | Enregistrement de la flotte d'urgence & transpondeurs RFID | • Marquage par Corporation (Police, SAMU, Pompiers)<br>• Autorisation de Plaques & Liste Noire d'Accès |
| **`EVPSafetyParametersCard`** | Cinématique de préemption, portes & dégagements de sécurité | • Porte de Détection d'Entrée ($60\text{--}160\text{ m}$)<br>• Seuil de Sortie ($\le 15\text{ m}$)<br>• Watchdog de Maintien ($45\text{ s}$)<br>• Dégagement Obligatoire Jaune/Tout-Rouge |
| **`RemoteGatewayCard`** | Gestion de la passerelle Web Go & du mesh Tailscale | • Bascule du Démon Passerelle Web Port 2201<br>• Statut Funnel Tailscale & Inspecteur d'URL Publiques |
| **`AccountSettingsCard`** | Authentification opérateur & profils utilisateurs RBAC | • Attribution de Rôles (Admin, Opérateur, Auditeur)<br>• Sécurité des Sessions & Identifiants JWT |
| **`DatabaseSettingsCard`** | Configuration du stockage persistant SQLite & PostgreSQL | • Sélecteur de Moteur BD & Configuration du Pool<br>• Vérification des Connexions & Migrations de Schéma |
| **`PilotingSchoolCard`** | Rythme des durées de cycle de vie et règles de promotion | • Rythme Automatique de Durée (Taille du Réseau)<br>• Marge de Graduation Dynamique des Fluides ($\delta^*$) |
| **`RewardWeightsCard`** | Poids d'optimisation RL (Temps d'Attente vs Débit Véhiculaire) | • Équilibrage Physique Auto (Temps de Trajet HCM $\tau$)<br>• Dérogations Manuelles des Poids |
| **`YellowScheduleCard`** | Programmation autonome du jaune clignotant nocturne | • Planificateur de Fenêtre Horaire (HH:MM)<br>• Ciblage Sélectif par Carrefour ou Réseau |
| **`AdvancedSystemCard`** | Paramètres système du PBT et du Watchdog | • Centile d'Exploitation PBT<br>• Période de Grâce Watchdog & Intervalles d'Analyse |
| **`AdvancedDQNCard`** | Configuration des hyperparamètres Deep Q-Network | • Capacité Mémoire Replay, Fréquence Synchro Réseau Cible, Décroissance $\epsilon$ |
| **`AdvancedPPOCard`** | Configuration des hyperparamètres Proximal Policy Optimization | • Ratio de Troncature ($\epsilon=0.2$), Coef Entropie, Coef Perte Valeur |
| **`TrafficRulesCard`** | Sécurité réglementaire et minutages minimaux des feux | • Vert Minimal, Dégagement Jaune, Tampons Tout-Rouge |
| **`HardwareConnectionCard`** | Contrôleurs de terrain physiques (NTCIP / UTMC) | • Points de Terminaison IP, Identifiants SNMP & Test Fail-Safe |
| **`MonitorSettingsCard`** | Télémétrie externe et flux d'incidents | • Points d'Accès Courtier MQTT / Webhook HTTP |

---

## 6. Marqueurs Visuels Canvas EVP & Inspecteur de Télémétrie en Direct (`ui/widgets/`)

Pour la surveillance sur poste de travail, CARINA restitue les véhicules d'urgence actifs en temps réel directement sur le canvas interactif Flet :

- **`EVPVehicleMarker` ([`ui/widgets/evp_vehicle_marker.py`](../../ui/widgets/evp_vehicle_marker.py)) :**
  - **Glyphes par Corporation :** Restitue des silhouettes vectorielles distinctes selon la corporation du véhicule :
    - *Police / Militaire :* Triangle Équilatéral (`POLICE`).
    - *Ambulance / SAMU :* Croix Rouge/Blanche Symétrique (`SAMU`).
    - *Pompiers :* Bouclier Protecteur Courbé (`FIRE`).
  - **Animation de Gyrophare :** Lorsque `siren_active=True`, le marqueur fait pulser des anneaux stroboscopiques concentriques à $2.5\text{ Hz}$ sur le canvas, alertant les opérateurs d'une intervention d'urgence en cours.
  - **Cap Dynamique :** Oriente automatiquement la rotation du véhicule pour correspondre au cap GPS en temps réel.

- **`EVPVehicleCard` ([`ui/widgets/evp_vehicle_card.py`](../../ui/widgets/evp_vehicle_card.py)) :**
  - Carte flottante HUD affichant l'indicatif radio, la vitesse ($\text{km/h}$), l'état du gyrophare/sirène, la distance jusqu'à la ligne d'arrêt du feu aval ($\text{m}$) et le statut de préemption (`APPROACHING`, `HOLD_ACTIVE`, `CLEARED`).

---

## 7. Architecture Web & Mobile du Central Control Operator (CCO) (`src_tsx/src_cco`)

En plus de l'IHM bureautique native Flet, CARINA comprend une plateforme moderne pour **Central Control Operator (CCO)** basée sur le web, construite en **React 18**, **TypeScript**, **TailwindCSS** et **Vite** située dans [`src_tsx/src_cco/`](../../src_tsx/src_cco). Elle est conçue selon les principes de la **Clean Architecture**, assurant un découplage total entre les règles métier de circulation, l'infrastructure de streaming et les composants de présentation :

```text
src_tsx/src_cco/
├── domain/                         # Entités Pures du Domaine, Modèles & Services Métier
│   ├── models/                     # Entités Métier Centrales
│   │   ├── Topology.ts             # Interfaces MapTopology, Node, Edge, Bounds
│   │   ├── CongestionLevel.ts      # VO du Domaine résolvant couleurs de rétention & seuils
│   │   ├── EmergencyVehicle.ts     # Modèle d'état télémétrie & préemption (SAMU, Pompiers, Police)
│   │   └── TrafficLight.ts         # Têtes de feux, état d'affichage & modèles de minutage
│   ├── services/                   # Services Géométriques & Cartographiques Purs du Domaine
│   │   ├── MapProjectionService.ts # Calculs de limites 2D orthographiques & ratio d'aspect SVG
│   │   ├── GeoProjectionService.ts # Conversion canonique GPS WGS84 vers cartésien SUMO
│   │   └── StreetTopologyGrouperService.ts # Agrégation de tronçons & tracés de cartes thermiques
│   └── contracts/                  # Interfaces de Frontière (DIP)
│       ├── ITopologyRepository.ts  # Contrat de récupération de topologie réseau
│       └── ICcoStreamService.ts    # Interface de flux temps réel & statut de connexion
│
├── application/                    # Cas d'Utilisation Applicatifs & Orchestrateurs
│   └── usecases/
│       ├── LoadTopologyUseCase.ts          # Récupère & met en cache la géométrie réseau
│       ├── ManageEmergencyFleetUseCase.ts   # Catégorise véhicules par corporation & alertes actives
│       └── ProcessTelemetryUseCase.ts      # Dépaquète les charges SSE vers l'état du domaine
│
├── infrastructure/                 # Adaptateurs Externes, API & Passerelles
│   ├── api/
│   │   └── HttpTopologyRepository.ts       # Implémentation Axios/Fetch de ITopologyRepository
│   ├── stream/
│   │   └── SseCcoStreamService.ts          # Client Server-Sent Events (/stream/cco) avec reconnexion
│   └── adapters/
│       └── EChartsOptionAdapter.ts         # Adaptateur transformant modèles métier en specs ECharts
│
└── presentation/                   # IHM Réactive, Hooks, Composants & Thèmes
    ├── context/
    │   └── ThemeContext.tsx                # Sélecteur de thème de quart opérateur (☀️ Jour / 🌙 Nuit)
    ├── utils/
    │   └── haptics.ts                      # Retour tactile vibratoire pour périphériques tactiles
    ├── hooks/
    │   ├── useCcoViewModel.ts              # Vue-modèle racine coordonnant cas d'usage, flux SSE & état
    │   ├── useCcoMapLayers.ts              # Calcul mémorisé des calques (rues, nœuds, feux)
    │   └── useMapViewport.ts               # Gestes de panoramique, zoom & animations flyTo fluides
    ├── components/
    │   ├── CcoHeader.tsx                   # Barre réactive monoligne avec badges, recherche & plein écran
    │   ├── CcoMap.tsx                      # Carte vectorielle SVG haute performance avec pan/zoom
    │   ├── EvpAlertToast.tsx               # Toast d'alerte d'urgence rétractable (micro-pilule mobile)
    │   └── map/
    │       ├── InspectionBottomSheet.tsx   # Volet bas ergonomique mobile & inspecteur sur desktop
    │       ├── QuickSearchModal.tsx        # Palette de recherche instantanée & auto-focus (flyTo)
    │       ├── MapScaleBar.tsx             # Échelle métrique dynamique réelle (m/km) étalonnée sur SUMO
    │       ├── MapRoadsLayer.tsx           # Rastériseur de routes multi-traits & carte de congestion
    │       ├── MapIntersectionsLayer.tsx   # Nœuds de carrefours interactifs avec zones tactiles
    │       ├── MapTrafficLightsLayer.tsx   # Têtes de feux tricolores avec halo actif et diagnostics
    │       ├── MapEmergencyVehiclesLayer.tsx # Marqueurs de véhicules, rotation de cap & auras de sirène
    │       ├── MapGlowFilters.tsx          # Définitions de filtres SVG néon pour feux & alertes
    │       ├── MapLegend.tsx               # Légende opérationnelle rétractable de carte thermique
    │       └── MapZoomControls.tsx         # Commandes de zoom avant, arrière et recentrage caméra
    ├── styles/
    │   ├── flet_color_palette.json         # Synchronisation exacte des couleurs avec la palette Flet
    │   └── index.css                       # Directives Tailwind et verrouillages d'overscroll
    ├── App.tsx                             # Composant racine avec ThemeProvider et modales
    └── main.tsx                            # Point d'entrée React DOM
```

---

## 8. Capacités d'Ergonomie & d'Expérience Opérateur Modernes du CCO

Le frontend CCO est conçu pour offrir une expérience opérationnelle optimale qu'il soit affiché sur un mur d'écrans 4K d'une salle de commande ou sur un smartphone sur le terrain :

1. **Volet Inférieur Ergonomique Mobile (`InspectionBottomSheet.tsx`) :**
   - Sur les appareils mobiles (`< 768px`), les cartes d'inspection s'ancrent en bas de l'écran avec une poignée de saisie et des gestes de glissement natifs vers le bas pour fermer.
   - Sur les stations de travail bureautiques (`>= 768px`), les détails flottent élégamment dans un coin de l'écran (HUD compact).
   - Fournit des diagnostics complets en temps réel pour :
     - **Véhicules d'Urgence :** Indicatif radio, vitesse ($\text{km/h}$), cap GPS ($^\circ$), état du gyrophare/sirène et carrefour cible.
     - **Feux de Signalisation :** ID du feu, phase active, indicateur d'état en direct (Vert, Jaune, Rouge), coordonnées et état de supervision Watchdog Fénix.
     - **Carrefours & Rues :** Nœuds de carrefours physiques, nom de rue, pourcentage de congestion ($0\text{--}100\%$) et évaluation du débit de circulation.

2. **Thèmes de Quart Opérationnel Doubles (☀️ Jour / 🌙 Nuit) :**
   - **Mode Jour Cartographique (`#F7F7F7`) :** Fond clair à contraste élevé optimisé pour les opérations de terrain et la lisibilité en plein soleil.
   - **Mode Nuit pour Mur d'Écrans (`#020617`) :** Palette sombre profonde conçue pour réduire la fatigue oculaire des opérateurs lors des quarts de nuit en centres de contrôle assombris.
   - Basculable instantanément via le sélecteur d'en-tête et automatiquement persisté dans le `localStorage` du navigateur.

3. **Palette de Commande avec Recherche Rapide & Auto-Focus Cinématique (`QuickSearchModal.tsx` & `flyTo`) :**
   - Accessible via le bouton de recherche d'en-tête ou les raccourcis clavier globaux (`Ctrl+K` ou `/`).
   - Indexe instantanément les véhicules, feux tricolores, carrefours et noms de rues.
   - Sélectionner un résultat déclenche un vol de caméra animé (`flyTo`) avec interpolation cubique ease-out, centrant la cible et ouvrant son volet d'inspection.

4. **Barre d'Échelle Métrique Dynamique (`MapScaleBar.tsx`) :**
   - Barre d'échelle métrique réelle (ex. `|—— 100 m ——|`) qui se recalibre automatiquement en temps réel selon le niveau de zoom actif et les coordonnées métriques 1:1 de SUMO.

5. **Filtrage Interactif de la Flotte & Puces Tactiles :**
   - Les badges d'en-tête pour le **SAMU**, les **Pompiers** et la **Police** fonctionnent comme des filtres interactifs. Toucher une corporation met en surbrillance ses unités sur la carte tout en estompant discrètement les autres véhicules.

6. **Plein Écran Immersif & Retours Tactiles Haptiques :**
   - Bouton plein écran à touche unique maximisant l'espace visuel en masquant les barres du navigateur.
   - Des micro-vibrations haptiques (`navigator.vibrate`) fournissent une confirmation physique lors des interactions avec les feux, les véhicules et les contrôles de zoom sur les écrans tactiles compatibles.

---

## 9. Diffusion par la Passerelle Web Go & Connectivité Distante

Le CCO web est servi par la **Passerelle Web Go** à très haut débit ([`src_go/web_gateway/`](../../src_go/web_gateway)) s'exécutant sur le port `2201` :

- **Diffusion des Ressources Statiques :** Sert le paquet React compilé pour la production sous `/cco/` avec compression gzip et en-têtes de cache.
- **Flux Télémétrique SSE Inférieur à 50ms :** Expose `/stream/cco`, diffusant en temps réel les transitions de phases des feux, les mises à jour de congestion et la cinématique des véhicules d'urgence sans surcoût d'interrogation répétée (*polling*).
- **Réseau Maillé Tailscale & Ingestion Distante :** S'intègre avec Tailscale Funnel pour un accès distant sécurisé par les unités de terrain et l'ingestion par webhook depuis les systèmes de régulation et répartiteurs d'appels d'urgence (CAD).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
