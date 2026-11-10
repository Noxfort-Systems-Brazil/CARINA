# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Dict, Optional

import torch

from optimizer.pae_optimizer import PAEOptimizer


class OnlinePAETrainer:
    """
    Coordinates online self-supervised training for the shared Universal PAE
    (Predictive Autoencoder) during simulation steps.

    Encapsulates state transition sampling across active agents, experience
    replay memory buffering, and optimization execution.
    """

    def __init__(
        self,
        settings: Any,
        agent_manager: Any,
        pae_optimizer: Optional[PAEOptimizer] = None,
    ) -> None:
        self.settings = settings
        self.agent_manager = agent_manager

        # --- Configuration ---
        try:
            self.pae_update_frequency = int(
                self.settings.getint("PAE", "update_frequency_seconds", fallback=5)
            )
        except (TypeError, ValueError, AttributeError):
            self.pae_update_frequency = 5

        self._last_pae_update_time = -self.pae_update_frequency

        if pae_optimizer is not None:
            self.pae_optimizer = pae_optimizer
        else:
            try:
                pae_lr = float(self.settings.getfloat("PAE", "learning_rate", fallback=5e-4))
            except (TypeError, ValueError, AttributeError):
                pae_lr = 5e-4
            self.pae_optimizer = PAEOptimizer(learning_rate=pae_lr)

        self.pae_memory = None

    def reset(self) -> None:
        """Resets the internal timers and state for a new session or map."""
        self._last_pae_update_time = -self.pae_update_frequency

    def train_step(self, sim_time: float, agents: Dict[str, Any]) -> None:
        """
        Conditionally triggers an online self-supervised training step
        if the configured time interval has elapsed.
        """
        if (sim_time - self._last_pae_update_time) >= self.pae_update_frequency:
            self._last_pae_update_time = sim_time
            self._execute_online_training(agents)

    def _execute_online_training(self, agents: Dict[str, Any]) -> None:
        """
        Executes a vectorized online self-supervised training step on the shared Universal PAE.
        Collects the most recent state transitions (S_{t-1}, a_{t-1} -> s_t) across all active agents
        and updates the action-conditioned iTransformer weights via PAEOptimizer.
        """
        from models.pae import PredictiveAutoencoder

        shared_pae = getattr(self.agent_manager, "shared_pae", None)
        if shared_pae is None:
            return

        is_real_pae = isinstance(shared_pae, PredictiveAutoencoder)
        raw_hist = getattr(shared_pae, "history_len", 8)
        history_len = int(raw_hist) if isinstance(raw_hist, int) and raw_hist > 0 else 8
        raw_in = getattr(shared_pae, "input_dim", 40)
        input_dim = int(raw_in) if isinstance(raw_in, int) and raw_in > 0 else 40

        raw_dev = getattr(self.pae_optimizer, "device", None)
        if isinstance(getattr(torch, "device", None), type):
            opt_device = raw_dev if isinstance(raw_dev, (torch.device, str)) else torch.device("cpu")
        else:
            opt_device = raw_dev or torch.device("cpu")

        curr_seqs = []
        next_vecs = []
        curr_acts = []
        curr_valid_dims = []

        for tl_id, agent in agents.items():
            if hasattr(agent, "memory") and len(agent.memory) >= 2:
                try:
                    if getattr(self, "pae_memory", None) is None:
                        from memory.state_buffer import StateReplayMemory

                        self.pae_memory = StateReplayMemory(
                            capacity=10000,
                            state_shape=(history_len, input_dim),
                            next_state_shape=(input_dim,),
                            device=opt_device,
                        )

                    st_prev = agent.memory.states[-2]
                    st_curr = agent.memory.states[-1]
                    if isinstance(st_curr, (list, tuple)) and len(st_curr) > 0:
                        target_frame = st_curr[-1]
                    else:
                        target_frame = st_curr

                    seq_t = torch.as_tensor(st_prev, dtype=torch.float32, device=opt_device)
                    orig_dim = (
                        int(seq_t.shape[-1])
                        if hasattr(seq_t, "shape") and len(seq_t.shape) >= 1 and isinstance(seq_t.shape[-1], int)
                        else input_dim
                    )
                    if is_real_pae and hasattr(shared_pae, "standardize_sequence"):
                        if hasattr(seq_t, "dim") and seq_t.dim() == 2:
                            seq_t = shared_pae.standardize_sequence(seq_t.unsqueeze(0)).squeeze(0)
                        elif hasattr(seq_t, "dim") and seq_t.dim() == 3:
                            seq_t = shared_pae.standardize_sequence(seq_t).squeeze(0)
                    seq_t = shared_pae.pad_to_input_dim(seq_t)

                    tgt_t = torch.as_tensor(target_frame, dtype=torch.float32, device=opt_device)
                    if hasattr(tgt_t, "dim") and tgt_t.dim() > 1:
                        tgt_t = tgt_t[-1]
                    tgt_t = shared_pae.pad_to_input_dim(tgt_t)

                    act_val = 0
                    mem_actions = getattr(agent.memory, "actions", None)
                    if isinstance(mem_actions, (list, tuple, torch.Tensor)) and len(mem_actions) >= 2:
                        raw_act = mem_actions[-2]
                        raw_int = int(raw_act.item()) if hasattr(raw_act, "item") else int(raw_act)
                        act_val = 1 if raw_int >= 1 else 0

                    if self.pae_memory is not None:
                        self.pae_memory.push(seq_t, tgt_t, action=act_val, valid_dim=orig_dim)

                    curr_seqs.append(seq_t)
                    next_vecs.append(tgt_t)
                    curr_acts.append(act_val)
                    curr_valid_dims.append(orig_dim)
                except Exception as e_sample:
                    logging.debug(f"[OnlinePAETrainer] PAE transition sampling skipped for {tl_id}: {e_sample}")

        if self.pae_memory is not None and len(self.pae_memory) >= 32:
            try:
                batch_size = min(len(self.pae_memory), 64)
                pae_loss = self.pae_optimizer.step_from_memory(shared_pae, self.pae_memory, batch_size=batch_size)
                logging.debug(
                    f"[PAE_ONLINE] Memory-buffered training step completed. Loss: {pae_loss:.6f} (buffer: {len(self.pae_memory)})"
                )
            except Exception as e_train:
                logging.debug(f"[PAE_ONLINE] Memory-buffered training step skipped: {e_train}")
        elif curr_seqs and next_vecs:
            try:
                batch_curr = torch.stack(curr_seqs)
                batch_next = torch.stack(next_vecs)
                if type(self.pae_optimizer) is PAEOptimizer:
                    batch_acts = torch.tensor(curr_acts, dtype=torch.long, device=opt_device)
                    batch_vdims = torch.tensor(curr_valid_dims, dtype=torch.long, device=opt_device)
                    pae_loss = self.pae_optimizer.step(
                        shared_pae, batch_curr, batch_next, actions=batch_acts, valid_dims=batch_vdims
                    )
                else:
                    pae_loss = self.pae_optimizer.step(shared_pae, batch_curr, batch_next)
                logging.debug(
                    f"[PAE_ONLINE] Self-supervised training step completed. Loss: {pae_loss:.6f} ({len(curr_seqs)} agents)"
                )
            except Exception as e_train:
                logging.debug(f"[PAE_ONLINE] Online training step skipped: {e_train}")
