---
tags: [slm, llm, qwen, llama-cpp, gguf, natural-language, xai]
aliases: [Small Language Models, Local LLM, Semantic Transducer, Offline AI]
---

# 🤖 Petits Modèles de Langage (SLM) & Intégration de LLM Local

Ce document spécifie le sous-système de Petits Modèles de Langage (SLM) de CARINA situé dans [`src/slm/`](../../src/slm). Il détaille la manière dont CARINA génère des justifications textuelles médico-légales prêtes pour publication à partir de tenseurs bruts d'attribution neuronale en utilisant des modèles de langage locaux et hors ligne (ex. **Qwen3 1.7B**, **Qwen2.5 1.5B/3B**, ou **Llama-3.2 3B**) sans appels d'API externes ni dépendances cloud.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🔍 Voir [IA Explicable & SAS](xai_and_sas.md) | 📄 Voir [Blocs de Rapports & Word](report_blocks_and_templates.md)

---

## 1. Philosophie Architecturale : Confidentialité Médico-Légale 100% Hors Ligne

Dans l'administration municipale publique, l'envoi de la télémétrie de trafic, des journaux d'incidents ou des données de contrôle des carrefours vers des API cloud commerciales (OpenAI, Anthropic, Google Cloud) enfreint la gouvernance des données publiques, les lois sur la vie privée (RGPD/LGPD) et la souveraineté municipale.

CARINA exécute toute la synthèse de rapports en langage naturel **100% localement sur site** :
- Fonctionne via des liaisons C++ optimisées (`llama-cpp-python`).
- Prend en charge la **quantification GGUF en 4 bits et 8 bits** (`Q4_K_M`, `Q8_0`).
- Ne consomme qu'environ **1,5 Go à 3,5 Go de VRAM** (ou RAM processeur avec accélération AVX-512).
- Sortie entièrement déterministe grâce à un échantillonnage à basse température ($\tau \le 0.2$).

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
- Transforme les tuples numériques `(queue_length=18, speed=12.4 km/h, veto=True)` en invites (*prompts*) spécialisées en ingénierie de la circulation.
- Intègre un moteur heuristique de repli : si le matériel manque de GPU/RAM ou si les poids LLM sont absents, il génère un texte d'ingénierie déterministe basé sur des règles sans planter.

### 2.2 Transducteur Llama Local (`local_llama_transducer.py`)
Situé dans [`src/slm/local_llama_transducer.py`](../../src/slm/local_llama_transducer.py) :
- Encapsule `llama_cpp.Llama` avec des verrous d'exécution thread-safe.
- Gère le déchargement des couches GPU (`n_gpu_layers = -1` pour un déchargement CUDA complet).
- Restreint la longueur de génération et la température pour prévenir les hallucinations.

### 2.3 Gestion des Périphériques & Ressources (`device_manager.py` & `resource_manager.py`)
- [`src/slm/device_manager.py`](../../src/slm/device_manager.py) : Profile le matériel disponible (NVIDIA CUDA, ROCm, Apple Metal ou threads CPU).
- [`src/slm/resource_manager.py`](../../src/slm/resource_manager.py) : Gère automatiquement les fenêtres de contexte ($2048$ à $4096$ jetons) et purge le cache KV entre les épisodes de génération de rapports.

### 2.4 Moteur de Révision Factuelle (`revision_engine.py` & `output_sanitizer.py`)
- [`src/slm/revision_engine.py`](../../src/slm/revision_engine.py) : Extrait les entités numériques de la prose générée et vérifie qu'elles correspondent strictement aux valeurs de la base de données SQL sous-jacente.
- [`src/slm/output_sanitizer.py`](../../src/slm/output_sanitizer.py) : Supprime les balises markdown, les espaces superflus et les artefacts de boucle répétitifs.

---

## 3. Configuration & Structure du Dossier Modèles (*Model Vault*)

Les poids pré-entraînés sont stockés dans le répertoire local `Model_Vault/` :

```text
Model_Vault/
└── qwen3-1.7b-instruct-q4_k_m.gguf
```

Configuration dans `config/settings.ini` :
```ini
[XAI]
enable_xai = true
model_name = Model_Vault/qwen3-1.7b-instruct-q4_k_m.gguf
vram_allocation_gb = 3.5
temperature = 0.15
context_window = 3072
```

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
