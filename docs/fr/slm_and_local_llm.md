---
tags: [slm, llm, qwen, llama-cpp, gguf, natural-language, xai]
aliases: [Petits Modèles de Langage, LLM Local, Transducteur Sémantique, IA Hors Ligne]
---

# 🤖 Petits Modèles de Langage (SLM) & Intégration de LLM Local

Ce document spécifie le sous-système de Petits Modèles de Langage (SLM) de CARINA situé dans [`src/slm/`](../../src/slm). Il détaille la manière dont CARINA génère des justifications textuelles médico-légales prêtes pour publication à partir de tenseurs bruts d'attribution neuronale en utilisant des modèles de langage locaux et hors ligne (principalement **Qwen3.5 2B** via `Qwen3.5-2B-UD-Q6_K_XL.gguf`, avec support de secours pour **Qwen2.5 1.5B/3B** ou **Llama-3.2 3B**) sans appels d'API externes ni dépendances cloud.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🔍 Voir [IA Explicable & SAS](xai_and_sas.md) | 📄 Voir [Blocs de Rapports & Word](report_blocks_and_templates.md)

---

## 1. Philosophie Architecturale : Confidentialité Médico-Légale 100% Hors Ligne

Dans l'administration municipale publique, l'envoi de la télémétrie de trafic, des journaux d'incidents ou des données de contrôle des carrefours vers des API cloud commerciales (OpenAI, Anthropic, Google Cloud) enfreint la gouvernance des données publiques, les lois sur la vie privée (RGPD/LGPD) et la souveraineté municipale.

CARINA exécute toute la synthèse de rapports en langage naturel **100% localement sur site** :
- Fonctionne via des liaisons C++ optimisées (`llama-cpp-python`).
- Prend en charge les **modèles quantifiés GGUF** (ex. `Q6_K_XL`, `Q4_K_M`, `Q8_0`).
- Ne consomme qu'environ **~1,5 Go à 3,5 Go de VRAM** (ou RAM processeur avec accélération AVX-512).
- Sortie entièrement déterministe grâce au décodage glouton (greedy) à température zéro ($\tau = 0.0$, `repeat_penalty = 1.05`).

```text
 Gradients Intégrés Captum & Télémétrie
                  │
                  ▼
       ┌───────────────────────┐
       │  semantic_transducer  │
       └───────────┬───────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
 ┌──────────────┐      ┌──────────────┐
 │prompt_builder│      │device_manager│ (Calcule la VRAM / Couches déchargées)
 └──────┬───────┘      └──────┬───────┘
        │                     │
        └──────────┬──────────┘
                   ▼
       ┌───────────────────────┐
       │local_llama_transducer │ (Exécute le modèle Qwen GGUF via llama.cpp)
       └───────────┬───────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
 ┌───────────────┐     ┌───────────────┐
 │output_sanitizer│    │revision_engine│ (Contre-vérifie le texte par rapport à la télémétrie)
 └───────────────┘     └───────────────┘
```

---

## 2. Modules Principaux dans `src/slm/`

### 2.1 Transducteur Sémantique (`semantic_transducer.py`)
Situé dans [`src/slm/semantic_transducer.py`](../../src/slm/semantic_transducer.py) :
- Sert d'interface publique principale pour la génération d'explications textuelles.
- Utilise par défaut `Model_Vault/Qwen3.5-2B-UD-Q6_K_XL.gguf` avec une fenêtre de contexte `n_ctx = 8192`.
- Transforme les tuples numériques `(queue_length=18, speed=12.4 km/h, veto=True)` en invites (*prompts*) spécialisées en ingénierie de la circulation.
- Intègre un moteur heuristique de repli : si le matériel manque de GPU/RAM ou si les poids LLM sont absents, il génère un texte d'ingénierie déterministe basé sur des règles sans planter.

### 2.2 Transducteur Local Llama (`local_llama_transducer.py`)
Situé dans [`src/slm/local_llama_transducer.py`](../../src/slm/local_llama_transducer.py) :
- Encapsule `llama_cpp.Llama` avec des verrous d'exécution thread-safe.
- Gère le déchargement des couches sur GPU (`n_gpu_layers = -1` pour un déchargement complet sur CUDA).
- Exécute un décodage glouton (`temperature = 0.0`, `repeat_penalty = 1.05`) avec des limites dynamiques de tokens pour éviter les hallucinations et les boucles de répétition.

### 2.3 Gestion des Périphériques et Ressources (`device_manager.py` & `resource_manager.py`)
- [`src/slm/device_manager.py`](../../src/slm/device_manager.py) : Détecte et profile le matériel disponible (NVIDIA CUDA, ROCm, Apple Metal ou threads CPU).
- [`src/slm/resource_manager.py`](../../src/slm/resource_manager.py) : Gère automatiquement l'allocation de contexte et purge le cache KV entre les sessions de génération.

### 2.4 Moteur de Révision Factuelle (`revision_engine.py` & `output_sanitizer.py`)
- [`src/slm/revision_engine.py`](../../src/slm/revision_engine.py) : Extrait les entités numériques de la prose générée et vérifie leur stricte conformité avec les valeurs de la base de données SQL.
- [`src/slm/output_sanitizer.py`](../../src/slm/output_sanitizer.py) : Supprime les balises markdown superflues, les espaces parasites et les artefacts de répétition.

---

## 3. Configuration et Dépôt de Modèles (`Model_Vault/`)

Les poids pré-entraînés sont stockés dans le répertoire local `Model_Vault/` :

```text
Model_Vault/
└── Qwen3.5-2B-UD-Q6_K_XL.gguf
```

Configuration dans `config/settings.ini` :
```ini
[REPORT_FORMATTING]
report_slm_device = auto
report_slm_gpu_layers = -1
xai_slm_device = auto
xai_slm_gpu_layers = -1
```

Paramètres d'inférence configurés dans [`semantic_transducer.py`](../../src/slm/semantic_transducer.py) :
- **Chemin du Modèle :** `Model_Vault/Qwen3.5-2B-UD-Q6_K_XL.gguf`
- **Fenêtre de Contexte (`n_ctx`) :** `8192`
- **Température :** `0.0` (déterministe / glouton)
- **Pénalité de Répétition :** `1.05`
- **Limite Maximale de Tokens :** Calculée dynamiquement (`512` à `4096`)

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3 ou ultérieure (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
