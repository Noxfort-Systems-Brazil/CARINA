# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import os
from typing import Any, Dict, List

from utils.settings_manager import SettingsManager  # Using SettingsManager for Consistency


class LocaleManagerBackend:
    """
    Manages loading and mapping of translated strings in the Backend (Headless).
    Updated to support 'default' parameters and robust fallback.
    """

    def __init__(self, locales_dir_name="locale_backend", file_suffix="_backend"):
        # Determines the path based on the location of this file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level (src/utils -> src) and enter the specified dir
        self.locales_dir = os.path.join(base_dir, "..", locales_dir_name)
        self.file_suffix = file_suffix

        self.fallback_lang_code = "en_us"
        self.current_lang_data: Dict[str, Any] = {}
        self.fallback_lang_data: Dict[str, Any] = {}

        # Try loading configuration
        try:
            settings_manager = SettingsManager()
            settings = settings_manager.load_settings()
            initial_lang_code = settings.get("language") or "pt_br"
            logging.info(f"Lendo idioma de settings.ini: '{initial_lang_code}'")
        except Exception as e:
            logging.warning(f"Erro ao ler idioma de settings.ini: {e}", exc_info=True)
            initial_lang_code = "pt_br"

        self.load_language(initial_lang_code)

    def _load_file(self, lang_code: str) -> Dict[str, Any]:
        """Reads a JSON translation file or directory of files."""
        dir_path = os.path.join(self.locales_dir, lang_code)

        if os.path.isdir(dir_path):
            merged_data = {}
            for filename in os.listdir(dir_path):
                if filename.endswith(".json"):
                    file_path = os.path.join(dir_path, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            merged_data.update(json.load(f))
                    except Exception as e:
                        logging.error(f"[LocaleManagerBackend] Erro ao ler '{file_path}': {e}", exc_info=True)
            return merged_data

        # File name follows the pattern 'pt_br_backend.json' or 'pt_br.json' depending on suffix
        file_name = f"{lang_code}{self.file_suffix}.json"
        file_path = os.path.join(self.locales_dir, file_name)

        if not os.path.exists(file_path):
            # Try without the _backend suffix as a fallback (if files are shared)
            file_path_alt = os.path.join(self.locales_dir, f"{lang_code}.json")
            if os.path.exists(file_path_alt):
                file_path = file_path_alt
            else:
                logging.error(f"[LocaleManagerBackend] Arquivo/Diretório não encontrado: {dir_path} ou {file_path}")
                return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"[LocaleManagerBackend] Erro ao ler '{file_path}': {e}", exc_info=True)
            return {}

    def load_language(self, lang_code: str):
        """Loads primary language and fallback."""
        self.fallback_lang_data = self._load_file(self.fallback_lang_code)

        if lang_code == self.fallback_lang_code:
            self.current_lang_data = self.fallback_lang_data
        else:
            self.current_lang_data = self._load_file(lang_code)

        self.current_lang_code = lang_code

        if self.current_lang_data:
            logging.info(f"Language file '{lang_code}' successfully loaded for backend.")

    def get_language(self) -> str:
        """Returns current language code."""
        return getattr(self, "current_lang_code", self.fallback_lang_code)

    def _get_nested_value(self, data: Dict, keys: List[str]) -> str | None:
        temp_dict = data
        for key in keys:
            if isinstance(temp_dict, dict) and key in temp_dict:
                temp_dict = temp_dict[key]
            else:
                return None
        return str(temp_dict) if isinstance(temp_dict, (str, int, float, bool)) else None

    def get_string(self, key: str, default: str = None, **kwargs) -> str:
        """
        Retrieves translated string.
        Args:
            key: 'section.subsection' key
            default: Fallback text if key does not exist (prevents crash)
            **kwargs: Variables to format string (e.g. agent_id=1)
        """
        keys = key.split(".")

        # 1. Try current language
        val = self._get_nested_value(self.current_lang_data, keys)

        # 2. Try fallback (English)
        if val is None:
            val = self._get_nested_value(self.fallback_lang_data, keys)

        # 3. Use default if provided
        if val is None:
            if default is not None:
                val = default
            else:
                return key  # Returns own key if all else fails

        # 4. Formatting (e.g. "Hello {name}")
        if kwargs:
            try:
                return val.format(**kwargs)
            except Exception as e:
                logging.warning(f"[LocaleBackend] Erro de formatação na chave '{key}': {e}", exc_info=True)
                return val

        return val
