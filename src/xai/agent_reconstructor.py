# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
import warnings

import torch

warnings.filterwarnings("ignore", category=FutureWarning, message=".*weight_norm.*")
warnings.filterwarnings("ignore", category=FutureWarning, module="torch.nn.utils.weight_norm")

from agents.local_agent import LocalAgent
from models.pae import PredictiveAutoencoder
from utils.locale_manager_backend import LocaleManagerBackend


class AgentReconstructor:
    """
    Responsibility: Load physical PyTorch Checkpoints (.pth) from the disk,
    validate their structure, and instantiate 'Blind' LocalAgents (disconnected
    from the live SUMO/Synapse network) strictly for Mathematical Analysis.
    """

    def __init__(self, checkpoints_dir: str):
        self.checkpoints_dir = checkpoints_dir
        self.locale_manager = LocaleManagerBackend()

        # --- Load PAE Universal from checkpoint ---
        self.shared_pae = self._load_pae()

    def _load_pae(self):
        """
        Loads the Universal PAE from the pae_universal.pth checkpoint.
        Infers iTransformer dimensions (var_embedding, value_embedding, latent_proj)
        with backward-compatible fallback, returning the model in eval() mode.
        """
        pae_path = os.path.join(self.checkpoints_dir, "pae_universal.pth")
        if not os.path.exists(pae_path):
            logging.info("[AgentReconstructor] PAE checkpoint not found. Agents will be reconstructed without PAE.")
            return None

        try:
            try:
                raw_ckpt = torch.load(pae_path, map_location=torch.device("cpu"), weights_only=True)
            except Exception:
                raw_ckpt = torch.load(pae_path, map_location=torch.device("cpu"), weights_only=False)  # nosec B614

            state_dict = (
                raw_ckpt["model_state_dict"]
                if isinstance(raw_ckpt, dict) and "model_state_dict" in raw_ckpt
                else raw_ckpt
            )

            if "var_embedding" in state_dict:
                input_dim = int(state_dict["var_embedding"].shape[1])
                d_model = int(state_dict["var_embedding"].shape[2])
                history_len = (
                    int(state_dict["value_embedding.weight"].shape[1]) if "value_embedding.weight" in state_dict else 8
                )
                if "latent_proj.3.weight" in state_dict:
                    latent_dim = int(state_dict["latent_proj.3.weight"].shape[0])
                elif "action_embedding.weight" in state_dict:
                    latent_dim = int(state_dict["action_embedding.weight"].shape[1])
                elif "decoder.0.weight" in state_dict:
                    latent_dim = int(state_dict["decoder.0.weight"].shape[1])
                elif "latent_proj.weight" in state_dict:
                    latent_dim = int(state_dict["latent_proj.weight"].shape[0])
                else:
                    latent_dim = 16

                num_latent_queries = int(state_dict["latent_queries"].shape[1]) if "latent_queries" in state_dict else 4
                layer_ids = {
                    int(k.split(".")[2])
                    for k in state_dict.keys()
                    if k.startswith("transformer_encoder.layers.")
                    and len(k.split(".")) > 2
                    and k.split(".")[2].isdigit()
                }
                num_layers = (max(layer_ids) + 1) if layer_ids else 2
                pae = PredictiveAutoencoder(
                    input_dim=input_dim,
                    latent_dim=latent_dim,
                    history_len=history_len,
                    d_model=d_model,
                    num_layers=num_layers,
                    num_latent_queries=num_latent_queries,
                )
            elif "encoder.0.weight" in state_dict and "encoder.3.weight" in state_dict:
                input_dim = int(state_dict["encoder.0.weight"].shape[1])
                latent_dim = int(state_dict["encoder.3.weight"].shape[0])
                pae = PredictiveAutoencoder(input_dim=input_dim, latent_dim=latent_dim)
            elif isinstance(state_dict, dict) and len(state_dict) == 0:
                input_dim, latent_dim = 40, 16
                pae = PredictiveAutoencoder(input_dim=input_dim, latent_dim=latent_dim)
            else:
                raise KeyError("Unrecognized PAE state_dict architecture keys.")

            target_sd = pae.state_dict()
            compatible_sd = {
                k: v
                for k, v in state_dict.items()
                if k in target_sd and getattr(v, "shape", None) == getattr(target_sd[k], "shape", None)
            }
            pae.load_state_dict(compatible_sd, strict=False)
            pae.eval()

            logging.info(f"[AgentReconstructor] Universal PAE loaded (input={input_dim}, latent={latent_dim})")
            return pae
        except Exception as e:
            logging.warning(f"[AgentReconstructor] Failed to load PAE: {e}. Continuing without PAE.", exc_info=True)
            return None

    def reconstruct_agent(self, agent_id: str) -> LocalAgent:
        """Loads weights from disk and reconstructs the Agent memory (with PAE integration)."""
        checkpoint_path = os.path.join(self.checkpoints_dir, f"agent_{agent_id}.pth")

        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

        try:
            try:
                checkpoint = torch.load(checkpoint_path, map_location=torch.device("cpu"), weights_only=True)
            except Exception:
                checkpoint = torch.load(
                    checkpoint_path, map_location=torch.device("cpu"), weights_only=False
                )  # nosec B614
        except Exception as e:
            raise RuntimeError(f"Corrupted checkpoint for {agent_id}: {e}")

        n_observations = checkpoint.get("n_observations")

        if n_observations is None:
            raise ValueError(f"Invalid checkpoint structure for {agent_id}. Missing 'n_observations'.")

        # Reconstruct Agent in binary tactical action space (0=ADVANCE, 1=KEEP);
        # AgentCheckpointManager.load automatically migrates legacy 3-action weights if encountered.
        agent = LocalAgent(
            tlight_id=agent_id,
            n_observations=n_observations,
            n_actions=2,
            initial_hyperparams={},
            log_dir="",
            locale_manager=self.locale_manager,
            shared_pae=self.shared_pae,
            device=torch.device("cpu"),
        )

        agent.load_checkpoint(checkpoint_path)
        if hasattr(agent.policy_net, "eval"):
            agent.policy_net.eval()
        pae_status = "with PAE" if self.shared_pae else "without PAE"
        logging.info(f"[AgentReconstructor] Agent {agent_id} reconstructed ({pae_status}).")
        return agent
