# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os


class HFTSessionManager:
    """
    Handles local file system I/O for saving map and schedule scenarios.
    Ensures correct directory structures are used outside of the networking code.
    """

    @staticmethod
    def save_map_and_schedule(
        map_file_content: bytes, map_file_name: str, peak_schedule_json: str, locale_manager=None
    ) -> tuple[bool, str, str | None, str | None]:
        """
        Saves the topology map and optional peak schedule.
        Returns (success, message, map_path, maps_dir)
        """

        def _get_string(key: str, default: str = None, **kwargs) -> str:
            if locale_manager and hasattr(locale_manager, "get_string"):
                return locale_manager.get_string(key, default=default, **kwargs)
            return default.format(**kwargs) if default and kwargs else (default or key)

        try:
            session_name = "hft_live_session"
            from src.utils.paths import get_base_output_dir

            session_dir = os.path.join(get_base_output_dir(), "results", session_name)
            maps_dir = os.path.join(session_dir, "maps")

            os.makedirs(maps_dir, exist_ok=True)

            if peak_schedule_json:
                peak_schedule_path = os.path.join(session_dir, "peak_schedule.json")
                with open(peak_schedule_path, "w", encoding="utf-8") as f:
                    f.write(peak_schedule_json)
                logging.info(
                    _get_string(
                        "hft_session.peak_schedule_saved",
                        default="[HFT Session] Peak schedule saved to {schedule_path}",
                        schedule_path=peak_schedule_path,
                    )
                )

            original_filename = map_file_name
            if not original_filename:
                original_filename = f"{session_name}.net.xml"
                logging.warning(f"[HFT] map_file_name not provided by Synapse. Falling back to {original_filename}")

            map_path = os.path.join(maps_dir, original_filename)

            with open(map_path, "wb") as f:
                f.write(map_file_content)

            logging.info(
                _get_string(
                    "hft_session.map_saved",
                    default="[HFT Session] Map {map_file} saved to {map_path}",
                    map_file=original_filename,
                    map_path=map_path,
                )
            )
            return (
                True,
                _get_string(
                    "hft_session.scenario_accepted",
                    default="Scenario accepted and saved successfully to {map_path}",
                    map_path=map_path,
                ),
                map_path,
                maps_dir,
            )

        except Exception as e:
            logging.error(f"[HFT] Error saving/processing map: {e}", exc_info=True)
            return False, str(e), None, None
