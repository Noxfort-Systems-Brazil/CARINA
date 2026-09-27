# 🗄️ Architecture Base de Données et Schémas

Ce document détaille la persistance asynchrone non-bloquante de CARINA et ses schémas relationnels sous PostgreSQL.

⬅️ [Hub de Documentation](../README.md) | 🏛️ [Architecture](architecture.md)

---

## 1. Stockage Asynchrone à Compression Delta
Pour garantir un temps de boucle inférieur à 1 ms pour le modèle d'IA, les écritures SQL sont externalisées vers des workers en arrière-plan avec écriture par lots de 50 enregistrements. L'encodage par plages de répétition réduit le volume sur disque de **97.9%**.

---

## 2. Tables Principales
- `step_decisions` : Historique des propositions d'actions, vetos Guardian et temps d'exécution.
- `synapse_fluid_dynamics` : Données de trafic haute fréquence par tronçon routier.
- `hardware_controller_connections` : Enregistrement des connexions aux contrôleurs de feux.
- `users` : Gestion des utilisateurs avec hachage sécurisé bcrypt.
