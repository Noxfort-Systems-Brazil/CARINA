# 🛡️ Sécurité Neuro-Symbolique, Watchdog et F.E.N.I.X.

Ce document détaille l'architecture de sécurité à deux niveaux de CARINA, son processus Watchdog haute disponibilité et le superviseur de résilience F.E.N.I.X.

⬅️ [Hub de Documentation](../README.md) | 🚦 [Pilotes Matériels](hardware_drivers.md) | 🧪 [Tests](testing.md)

---

## 1. Pare-Feu de Sécurité à Double Barrière

```text
Action Proposée ──> [1. Règles Symboliques] ──> [2. Veto Neural Anti-Engorgement] ──> Sortie Matérielle
                             │                                 │
                             ├── Veto (Vert Min / Jaune)       └── Veto (Risque > 0.80)
                             └── Forcer Maintien de Phase      └── Forcer Phase de Dégagement
```

---

## 2. Règles Symboliques Physiques Inviolables
- **SR-01 (Vert Minimal) :** Durée verte active garantie d'au moins 7,0 s.
- **SR-02 (Intervalle Jaune) :** Dégagement obligatoire de 3,0 s avant tout changement de phase.
- **SR-03 (Rouge Intégral) :** Sécurité de 2,0 s entre mouvements conflictuels.
- **SR-04 (Protection Piétonne) :** Respect des demandes de bouton-poussoir piéton.
- **SR-05 (Matrice de Conflits) :** Interdiction stricte de verts simultanés sur voies sécantes.

---

## 3. Supervision Watchdog et Auto-Guérison F.E.N.I.X.
- **Watchdog :** Écoute les signaux vitaux toutes les 100 ms. En cas d'absence de signal pendant 5,0 s, il déclenche le mode de repli local et active `FenixSupervisor`.
- **F.E.N.I.X. (`src/fenix/`) :** Relance le processus d'IA, gère un délai exponentiel (backoff), place la nouvelle instance en mode `FROZEN_SYNC` et n'autorise la reprise des commandes qu'au moment précis de la prochaine transition de phase du contrôleur physique (`StateReconciler`).
