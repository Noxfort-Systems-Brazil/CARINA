# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Agent checkpoint serialization, vault synchronization, and orchestrated load/migration."""

import logging
import os
from typing import TYPE_CHECKING, Any, Dict, Optional

import torch

from src.agents.checkpoint_migrator import CheckpointMigrator
from src.interfaces.repositories import ICloudVaultRepository

if TYPE_CHECKING:
    from src.agents.local_agent import LocalAgent


class AgentCheckpointManager:
    """Handles checkpoint I/O, optional vault synchronization, and calls `CheckpointMigrator`."""

    @staticmethod
    def _get_results_base_dir() -> str:
        try:
            from src.utils.paths import get_base_output_dir
        except ImportError:
            from utils.paths import get_base_output_dir
        return os.path.join(get_base_output_dir(), "results")

    @staticmethod
    def _resolve_vault_repo(
        agent: Any, vault_repo: Optional[ICloudVaultRepository] = None
    ) -> Optional[ICloudVaultRepository]:
        if vault_repo is not None:
            return vault_repo
        agent_db = getattr(agent, "db_manager", None)
        if agent_db is not None:
            return agent_db
        try:
            from src.database.database_manager import DatabaseManager
        except ImportError:
            from database.database_manager import DatabaseManager
        return DatabaseManager.get_instance(agent.locale_manager)

    @staticmethod
    def _migrate_legacy_architecture_keys(
        state_dict: Dict[str, Any], target_state_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        return CheckpointMigrator.migrate_legacy_architecture_keys(state_dict, target_state_dict)

    @staticmethod
    def _find_first_conv_key(state_dict: Dict[str, Any]) -> Optional[str]:
        return CheckpointMigrator.find_first_conv_key(state_dict)

    @staticmethod
    def _load_into_policy_net(policy_net: Any, state_dict: Dict[str, Any], target_dict: Dict[str, Any]) -> None:
        CheckpointMigrator.load_into_policy_net(policy_net, state_dict, target_dict)

    @staticmethod
    def save(
        agent: "LocalAgent",
        filepath: str,
        maturity_stage: str,
        vault_repo: Optional[ICloudVaultRepository] = None,
    ) -> None:
        raw_xai = getattr(agent, "xai_memory", None)
        if raw_xai is None:
            serialized_xai: Any = None
        elif (
            hasattr(raw_xai, "size")
            and hasattr(raw_xai, "capacity")
            and isinstance(getattr(raw_xai, "size", None), int)
            and isinstance(getattr(raw_xai, "capacity", None), int)
        ):
            n_valid = min(int(raw_xai.size), int(raw_xai.capacity), 200)
            if n_valid <= 0:
                serialized_xai = None
            elif (
                isinstance(getattr(raw_xai, "states", None), torch.Tensor)
                and type(raw_xai.states).__name__ != "DummyTensor"
            ):
                ptr = int(getattr(raw_xai, "ptr", n_valid))
                cap = int(raw_xai.capacity)
                if raw_xai.size <= cap and ptr == raw_xai.size and n_valid == raw_xai.size:
                    valid_states = raw_xai.states[:n_valid].detach().cpu().clone()
                else:
                    indices = [(ptr - n_valid + i) % cap for i in range(n_valid)]
                    valid_states = raw_xai.states[indices].detach().cpu().clone()
                serialized_xai = {
                    "_compact_xai_states": valid_states,
                    "state_shape": tuple(getattr(raw_xai, "state_shape", tuple(valid_states.shape[1:]))),
                    "capacity": min(cap, 200),
                }
            else:
                serialized_xai = raw_xai
        else:
            serialized_xai = raw_xai

        checkpoint = {
            "episodes_done": agent.episodes_done,
            "steps_done": agent.steps_done,
            "policy_net_state_dict": agent.policy_net.state_dict(),
            "optimizer_state_dict": agent.optimizer.state_dict(),
            "hyperparameters": agent.hyperparams,
            "xai_memory": serialized_xai,
            "n_observations": agent.n_observations,
            "n_actions": getattr(agent, "n_actions", 2),
            "maturity_stage": maturity_stage,
        }
        torch.save(checkpoint, filepath)
        try:
            repo = AgentCheckpointManager._resolve_vault_repo(agent, vault_repo)
            if repo is not None:
                repo.sync_file_to_vault(filepath, AgentCheckpointManager._get_results_base_dir())
        except Exception:
            pass

    @staticmethod
    def _try_restore_from_vault(
        agent: "LocalAgent", filepath: str, vault_repo: Optional[ICloudVaultRepository] = None
    ) -> None:
        if os.path.exists(filepath):
            return
        try:
            repo = AgentCheckpointManager._resolve_vault_repo(agent, vault_repo)
            if repo is None:
                return
            base_dir = AgentCheckpointManager._get_results_base_dir()
            rel_path = os.path.relpath(filepath, base_dir)
            repo.restore_file_from_vault(rel_path, filepath)
        except Exception as e:
            logging.warning(
                f"[AgentCheckpointManager] Vault restoration check error for {filepath}: {e}", exc_info=True
            )

    @staticmethod
    def _load_torch_checkpoint(filepath: str, device: Any) -> Dict[str, Any]:
        try:
            return torch.load(filepath, map_location=device, weights_only=True)
        except Exception:
            return torch.load(filepath, map_location=device, weights_only=False)  # nosec B614

    @staticmethod
    def _maybe_adapt_channels(
        agent: "LocalAgent",
        checkpoint: Dict[str, Any],
        raw_state_dict: Any,
        state_dict: Any,
    ) -> bool:
        conv_key = CheckpointMigrator.find_first_conv_key(state_dict) if isinstance(state_dict, dict) else None
        if not isinstance(state_dict, dict) or conv_key is None:
            return False

        try:
            in_channels = state_dict[conv_key].shape[1]
            cur_pae_latent = agent.pae_augmentor.latent_dim if getattr(agent, "pae_augmentor", None) else 0
            agent.pae_latent_dim = cur_pae_latent
            expected_channels = agent.n_observations + cur_pae_latent
            if in_channels == expected_channels:
                return False

            logging.info(
                f"[LocalAgentHelpers] Adapting checkpoint weights for agent {agent.id}: "
                f"checkpoint has {in_channels} channels, current model expects {expected_channels} "
                f"(n_obs={agent.n_observations}, pae_latent={cur_pae_latent})."
            )
            CheckpointMigrator.adapt_input_channel_weights(
                agent, raw_state_dict, in_channels, checkpoint.get("n_observations"), cur_pae_latent
            )
            return True
        except Exception as e:
            logging.warning(
                f"[LocalAgentHelpers] Failed to adapt weights for agent {agent.id}: {e}. "
                "Rebuilding model with expected channels.",
                exc_info=True,
            )
            agent._build_network()
            agent._create_optimizer()
            return True

    @staticmethod
    def load(
        agent: "LocalAgent",
        filepath: str,
        vault_repo: Optional[ICloudVaultRepository] = None,
    ) -> str:
        lm = agent.locale_manager
        saved_maturity = "CHILD"
        AgentCheckpointManager._try_restore_from_vault(agent, filepath, vault_repo)

        try:
            checkpoint = AgentCheckpointManager._load_torch_checkpoint(filepath, agent.device)

            if agent.n_observations != checkpoint.get("n_observations"):
                logging.warning(
                    lm.get_string(
                        "local_agent.load.obs_mismatch_warning",
                        agent_id=agent.id,
                        chk_obs=checkpoint.get("n_observations"),
                        cur_obs=agent.n_observations,
                    )
                )

            saved_maturity = checkpoint.get("maturity_stage", "CHILD")
            raw_state_dict = checkpoint.get("policy_net_state_dict")
            target_state_dict = agent.policy_net.state_dict() if hasattr(agent.policy_net, "state_dict") else {}
            state_dict = (
                CheckpointMigrator.migrate_legacy_architecture_keys(raw_state_dict, target_state_dict)
                if isinstance(raw_state_dict, dict)
                else raw_state_dict
            )
            action_adapted = (
                isinstance(raw_state_dict, dict)
                and isinstance(state_dict, dict)
                and raw_state_dict.keys() != state_dict.keys()
            ) or (
                checkpoint.get("n_actions") is not None
                and checkpoint.get("n_actions") != getattr(agent, "n_actions", 2)
            )

            dim_adapted = AgentCheckpointManager._maybe_adapt_channels(agent, checkpoint, raw_state_dict, state_dict)

            if "hyperparameters" in checkpoint:
                agent.update_hyperparameters(checkpoint["hyperparameters"])

            if not dim_adapted and state_dict is not None:
                try:
                    CheckpointMigrator.load_into_policy_net(
                        agent.policy_net, state_dict, target_state_dict if isinstance(target_state_dict, dict) else {}
                    )
                    if "optimizer_state_dict" in checkpoint and not action_adapted:
                        try:
                            agent.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
                        except Exception:
                            agent._create_optimizer()
                except Exception as e:
                    logging.warning(
                        f"[LocalAgentHelpers] Error loading state dict: {e}. Reinitializing policy net.",
                        exc_info=True,
                    )
                    agent._build_network()
                    agent._create_optimizer()

            agent.episodes_done = checkpoint.get("episodes_done", 0)
            agent.steps_done = checkpoint.get("steps_done", 0)
            CheckpointMigrator.restore_xai_memory(agent, checkpoint.get("xai_memory"))

            agent.policy_net.train(False)
            agent._last_raw_state = None
            agent._last_decision = None
            logging.info(
                lm.get_string("local_agent.load.success", agent_id=agent.id, path=filepath, count=len(agent.xai_memory))
            )
        except FileNotFoundError:
            logging.warning(lm.get_string("local_agent.load.not_found_warning", agent_id=agent.id, path=filepath))
        except Exception as e:
            logging.error(lm.get_string("local_agent.load.error", agent_id=agent.id, error=e), exc_info=True)

        return saved_maturity
