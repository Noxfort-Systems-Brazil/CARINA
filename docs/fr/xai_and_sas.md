# 🔍 IA Explicable (XAI) et Rapports Légaux

Ce document détaille le pipeline d'explicabilité de CARINA fondé sur Google Captum et la génération de rapports d'expertise technique.

⬅️ [Hub de Documentation](../README.md) | 🏛️ [Architecture](architecture.md)

---

## 1. Explicabilité Mathématique et Transparence
Dans les infrastructures publiques de transport, les modèles opaques ("boîtes noires") sont proscrits par les organes de contrôle. CARINA produit une attribution causale précise via les gradients intégrés de Captum pour chaque signal mesuré.

---

## 2. Les 5 Équations Formelles du Rapport
1. **Convolutions causales dilatées (TCN)** pour le traitement temporel sans fuite future.
2. **Attention spatio-temporelle sur graphe (ST-GATv2 Lite)** pour les ondes vertes.
3. **Fusion par attention croisée** entre les visions tactique et stratégique.
4. **Valeur Q Dueling de sécurité** pour la détection du risque d'engorgement.
5. **Gradients intégrés de Captum** respectant l'axiome de complétude.
