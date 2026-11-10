# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import TYPE_CHECKING, Optional

import torch

from memory.state_buffer import StateReplayMemory
from optimizer.pae_optimizer import PAEOptimizer
from optimizer.ppo_optimizer import PPOOptimizer

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend


class LearningCoordinator:
    """
    Encapsulates the formulation of the Reinforcement Learning Cycle correctly.
    (HFT Refactored for SOLID Compliance).
    """

    def __init__(
        self,
        agents: dict,
        state_history: dict,
        locale_manager: "LocaleManagerBackend",
        hyperparams: dict = None,
        shared_pae=None,
    ):
        """
        Initializes the Learning Coordinator.
        """
        self.agents = agents
        self.state_history = state_history
        self.locale_manager = locale_manager
        self.shared_pae = shared_pae

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.scaler = torch.amp.GradScaler(enabled=(self.device.type == "cuda"))

        # Dependency Inversion: Extract dynamic hyperparams safely
        if not hyperparams and agents:
            first_agent = list(agents.values())[0]
            if hasattr(first_agent, "hyperparams"):
                hyperparams = first_agent.hyperparams

        self.ppo_optimizer = PPOOptimizer(hyperparams or {}, self.device, self.scaler)
        self.pae_optimizer = PAEOptimizer(device=self.device, scaler=self.scaler)

        self.pae_memory: Optional[StateReplayMemory] = None
        if self.shared_pae is not None:
            raw_hist = getattr(self.shared_pae, "history_len", 12)
            raw_in = getattr(self.shared_pae, "input_dim", 40)
            history_len = raw_hist if isinstance(raw_hist, int) and raw_hist > 0 else 12
            input_dim = raw_in if isinstance(raw_in, int) and raw_in > 0 else 40
            self.pae_memory = StateReplayMemory(
                capacity=10000,
                state_shape=(history_len, input_dim),
                next_state_shape=(input_dim,),
                device=self.device,
            )

        # Initializes TensorBoard Metrics (Moved from LocalAgent)
        import os
        from datetime import datetime

        from utils.paths import get_base_output_dir

        log_dir = os.path.join(get_base_output_dir(), "logs", "rl_metrics", datetime.now().strftime("%Y%m%d-%H%M%S"))
        from torch.utils.tensorboard import SummaryWriter

        os.makedirs(log_dir, exist_ok=True)
        self.writer = SummaryWriter(log_dir)

        logging.info(
            self.locale_manager.get_string("learning_coordinator.init.created", fallback="LearningCoordinator created.")
        )

    def store_experience(self, last_decision_data: dict, rewards: dict, done: bool):
        """
        Stores each agent's experience in their respective memory buffer.
        """
        for tl_id, agent in self.agents.items():
            if tl_id in last_decision_data:
                data = last_decision_data[tl_id]

                base_reward = rewards.get(tl_id, 0)
                policy_bonus = getattr(agent, "current_reward_bonus", 0.0)
                final_reward = base_reward + policy_bonus

                if hasattr(agent, "push_memory"):
                    agent.push_memory(
                        state_sequence=data["state_sequence"],
                        action=data["action"],
                        log_prob=data["log_prob"],
                        reward=final_reward,
                        done=done,
                        state_value=data["state_val"],
                    )

    def _estimate_bootstrap_value(self, tl_id: str, agent, last_done: bool) -> Optional[float]:
        """Estimates V(s_T) for GAE bootstrap when the rollout horizon ends before episode termination."""
        if last_done:
            return 0.0
        hist = self.state_history.get(tl_id) if isinstance(self.state_history, dict) else None
        if not hist:
            return None
        try:
            seq_list = list(hist)
            seq_t = torch.tensor(seq_list, dtype=torch.float32, device=self.device).unsqueeze(0)
            if hasattr(agent, "_augment_with_pae"):
                seq_t = agent._augment_with_pae(seq_t)
            with torch.no_grad():
                _, val_t = agent.policy_net(seq_t)
                v_item = val_t.item() if hasattr(val_t, "item") else float(val_t)
                if isinstance(v_item, (int, float)):
                    return float(v_item)
        except Exception:
            return None
        return None

    def update_agents(self, last_states: dict, last_done: bool):
        """
        Commands all agents to learn from their memories using PPO.
        Orchestrates the global PAE physics engine model sequentially.
        """
        logging.debug(
            self.locale_manager.get_string("learning_coordinator.update.trigger", fallback="Updating agents.")
        )

        pae_loss_sum = 0.0
        pae_batches_trained = 0

        for tl_id, agent in self.agents.items():
            if hasattr(agent, "memory") and len(agent.memory) > 0:
                # Extracts raw transition data directly from agent's memory abstraction
                if hasattr(agent.memory, "get_batch"):
                    old_states, old_actions, old_log_probs, rewards, dones, old_state_values = agent.memory.get_batch()
                else:
                    return  # Fallback for Guardian memory style (Replay buffer vs OnPolicy)

                bootstrap_val = self._estimate_bootstrap_value(tl_id, agent, last_done)
                memory_batch = (old_states, old_actions, old_log_probs, rewards, dones, old_state_values)

                total_loss = self.ppo_optimizer.step(
                    policy_net=agent.policy_net,
                    optimizer=agent.optimizer,
                    memory_batch=memory_batch,
                    evaluate_fn=agent.evaluate,
                    last_next_value=bootstrap_val,
                )

                agent.steps_done += 1
                self.writer.add_scalar(f"Treinamento/Loss_Total_{tl_id}", total_loss, agent.steps_done)

                # 2. Universal Action-Conditioned Batch Training for Physics Engine
                if self.shared_pae is not None and len(old_states) > 1:
                    for t in range(len(old_states) - 1):
                        current_frame = old_states[t]
                        next_frame = (
                            old_states[t + 1][-1, :]
                            if hasattr(old_states[t + 1], "dim") and old_states[t + 1].dim() == 2
                            else (
                                old_states[t + 1][:, -1, :]
                                if hasattr(old_states[t + 1], "dim") and old_states[t + 1].dim() == 3
                                else old_states[t + 1]
                            )
                        )
                        orig_dim = next_frame.size(-1) if hasattr(next_frame, "size") else None
                        valid_dim = orig_dim if isinstance(orig_dim, int) and orig_dim > 0 else None

                        act_val = None
                        try:
                            a_item = old_actions[t].item() if hasattr(old_actions[t], "item") else int(old_actions[t])
                            if isinstance(a_item, (int, float)):
                                act_val = int(a_item)
                        except Exception:
                            act_val = None

                        from models.pae import PredictiveAutoencoder

                        if hasattr(self.shared_pae, "pad_to_input_dim"):
                            current_frame = self.shared_pae.pad_to_input_dim(current_frame)
                            next_frame = self.shared_pae.pad_to_input_dim(next_frame)
                        if isinstance(self.shared_pae, PredictiveAutoencoder) and hasattr(
                            self.shared_pae, "standardize_sequence"
                        ):
                            current_frame = self.shared_pae.standardize_sequence(
                                current_frame.unsqueeze(0) if current_frame.dim() == 2 else current_frame
                            ).squeeze(0)

                        if self.pae_memory is not None:
                            self.pae_memory.push(
                                current_frame, next_frame, action=act_val, valid_dim=valid_dim
                            )
                        else:
                            pae_loss_sum += self.pae_optimizer.step(
                                self.shared_pae,
                                current_frame.to(self.device),
                                next_frame.to(self.device),
                                action=act_val,
                            )
                            pae_batches_trained += 1

                agent.memory.clear()

        # 3. Collective TensorBoard Logging & Memory-Buffered Training
        if self.shared_pae is not None:
            most_advanced_step = max((getattr(a, "steps_done", 0) for a in self.agents.values()), default=0)
            if self.pae_memory is not None and len(self.pae_memory) >= 16:
                batch_size = min(len(self.pae_memory), 64)
                pae_batch_loss = self.pae_optimizer.step_from_memory(
                    self.shared_pae, self.pae_memory, batch_size=batch_size
                )
                self.writer.add_scalar("Treinamento/PAE_Loss_Global", pae_batch_loss, most_advanced_step)
            elif pae_batches_trained > 0:
                avg_pae_loss = pae_loss_sum / pae_batches_trained
                self.writer.add_scalar("Treinamento/PAE_Loss_Global", avg_pae_loss, most_advanced_step)

    def close(self):
        """Closes the TensorBoard writer to release resources."""
        if hasattr(self, "writer") and self.writer is not None:
            try:
                self.writer.close()
            except Exception as _exc:
                logging.debug("[core] Ignored recoverable error: %s", _exc)
            self.writer = None
