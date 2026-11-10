# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
from typing import Any, Dict, Optional

import torch

from src.utils.paths import get_base_output_dir


class AgentCheckpointRepository:
    """Handles disk persistence (saving and restoring) of AI agent weights and states."""

    @classmethod
    def get_checkpoint_dir(cls, map_path: str) -> str:
        """Derives checkpoint directory path from the map file path."""
        map_name = os.path.basename(map_path).replace(".net.xml", "")
        return os.path.join(get_base_output_dir(), "results", map_name, "checkpoints")

    @classmethod
    def save_system_state(
        cls,
        map_path: str,
        agents: Dict[str, Any],
        strategist: Optional[Any],
        shared_pae: Optional[Any] = None,
        guardians: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persists the state (weights) of all local and global agents to disk."""
        if not map_path:
            logging.warning("[AgentCheckpointRepository] Cannot save state: No map path provided.")
            return

        ckpt_dir = cls.get_checkpoint_dir(map_path)
        os.makedirs(ckpt_dir, exist_ok=True)

        count_saved = 0
        # Save Local Agents
        for tl_id, agent in agents.items():
            try:
                safe_id = tl_id.replace(":", "_").replace("/", "_")
                path = os.path.join(ckpt_dir, f"agent_{safe_id}.pth")
                if hasattr(agent, "save"):
                    agent.save(path)
                    count_saved += 1
            except Exception as e:
                logging.error(f"[AgentCheckpointRepository] Failed to save agent {tl_id}: {e}", exc_info=True)

        # Save Strategist
        if strategist:
            try:
                strat_path = os.path.join(ckpt_dir, "strategist_global.pth")
                strategist.save_checkpoint(strat_path)
                logging.info("[AgentCheckpointRepository] Strategist state saved.")
            except Exception as e:
                logging.error(f"[AgentCheckpointRepository] Failed to save Strategist: {e}", exc_info=True)

        logging.info(f"[AgentCheckpointRepository] System state saved to {ckpt_dir} ({count_saved} local agents).")

        # Save PAE Universal
        if shared_pae is not None:
            try:
                pae_path = os.path.join(ckpt_dir, "pae_universal.pth")
                torch.save(shared_pae.state_dict(), pae_path)
                logging.info("[AgentCheckpointRepository] PAE Universal state saved.")
            except Exception as e:
                logging.error(f"[AgentCheckpointRepository] Failed to save PAE Universal: {e}", exc_info=True)

        # Save Guardians
        if guardians:
            for tl_id, guardian in guardians.items():
                try:
                    safe_id = tl_id.replace(":", "_").replace("/", "_")
                    path = os.path.join(ckpt_dir, f"guardian_{safe_id}.pth")
                    torch.save(guardian.policy_net.state_dict(), path)
                except Exception as e:
                    logging.error(f"[AgentCheckpointRepository] Failed to save guardian {tl_id}: {e}", exc_info=True)

    @classmethod
    def restore_system_state(
        cls,
        map_path: str,
        agents: Dict[str, Any],
        strategist: Optional[Any],
        shared_pae: Optional[Any] = None,
        guardians: Optional[Dict[str, Any]] = None,
        device: Optional[Any] = None,
    ) -> None:
        """Loads the weights of agents from disk if available."""
        if not map_path:
            return

        ckpt_dir = cls.get_checkpoint_dir(map_path)
        if not os.path.exists(ckpt_dir):
            logging.info("[AgentCheckpointRepository] No checkpoints found. Starting with fresh agents.")
            return

        # Load Local Agents
        for tl_id, agent in agents.items():
            safe_id = tl_id.replace(":", "_").replace("/", "_")
            path = os.path.join(ckpt_dir, f"agent_{safe_id}.pth")
            if os.path.exists(path):
                try:
                    if hasattr(agent, "load"):
                        agent.load(path)
                except Exception as e:
                    logging.warning(f"[AgentCheckpointRepository] Failed to load checkpoint for {tl_id}: {e}", exc_info=True)

        # Load Strategist
        if strategist:
            strat_path = os.path.join(ckpt_dir, "strategist_global.pth")
            if os.path.exists(strat_path):
                try:
                    strategist.load_checkpoint(strat_path)
                    logging.info("[AgentCheckpointRepository] Strategist state restored.")
                except Exception as e:
                    logging.warning(f"[AgentCheckpointRepository] Failed to load Strategist checkpoint: {e}", exc_info=True)

        # Restore PAE Universal
        if shared_pae is not None:
            pae_path = os.path.join(ckpt_dir, "pae_universal.pth")
            if os.path.exists(pae_path):
                try:
                    try:
                        pae_data = torch.load(pae_path, map_location=device, weights_only=True)
                    except Exception:
                        pae_data = torch.load(pae_path, map_location=device, weights_only=False)
                    shared_pae.load_state_dict(pae_data)
                    logging.info("[AgentCheckpointRepository] PAE Universal state restored.")
                except Exception as e:
                    logging.warning(f"[AgentCheckpointRepository] Failed to load PAE Universal checkpoint: {e}", exc_info=True)

        # Restore Guardians
        if guardians:
            for tl_id, guardian in guardians.items():
                safe_id = tl_id.replace(":", "_").replace("/", "_")
                path = os.path.join(ckpt_dir, f"guardian_{safe_id}.pth")
                if os.path.exists(path):
                    try:
                        try:
                            g_data = torch.load(path, map_location=device, weights_only=True)
                        except Exception:
                            g_data = torch.load(path, map_location=device, weights_only=False)
                        guardian.policy_net.load_state_dict(g_data)
                        guardian.target_net.load_state_dict(guardian.policy_net.state_dict())
                    except Exception as e:
                        logging.warning(
                            f"[AgentCheckpointRepository] Failed to load guardian checkpoint for {tl_id}: {e}"
                        , exc_info=True)
