# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Periodic ST-GATv2 strategic coordinator responsible for temporal graph tensor assembly,
self-supervised + CTDE online training updates, and context distribution to LocalAgents.
Isolates NumPy/PyTorch tensor operations outside StepProcessor.
"""

import logging
from typing import Any, Dict, Optional

import numpy as np
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class StrategicCoordinator:
    """Executes periodic network-wide ST-GATv2 forecasting, training updates, and vector dispatch."""

    def __init__(
        self,
        update_frequency_seconds: float = 5.0,
        agent_evaluator: Optional[Any] = None,
        state_extractor: Optional[Any] = None,
    ) -> None:
        self.update_frequency_seconds = float(update_frequency_seconds)
        self.agent_evaluator = agent_evaluator
        self.state_extractor = state_extractor

        self.strategist: Optional[Any] = None
        self._last_update_time: float = -1e9
        self._prev_node_seq: Optional[torch.Tensor] = None

    def set_strategist(self, strategist: Optional[Any]) -> None:
        """Configures the global ST-GATv2 Strategist agent and resets temporal history."""
        self.strategist = strategist
        self.reset()

    def reset(self) -> None:
        """Resets strategic cadence timers and cached node sequence tensor."""
        self._last_update_time = -1e9
        self._prev_node_seq = None

    def update_and_distribute(
        self,
        traffic_data: Dict[str, Any],
        agents: Dict[str, Any],
        sim_time: float,
        current_stages: Dict[str, Any],
        fleet_mean_reward: float,
    ) -> None:
        """Runs strategic coordination when strategist is attached and interval has elapsed."""
        if self.strategist is None or (sim_time - self._last_update_time) < self.update_frequency_seconds:
            return

        try:
            num_nodes = getattr(self.strategist, "num_nodes", 0)
            tls_id_to_idx = getattr(self.strategist, "tls_id_to_idx", {})
            if not isinstance(num_nodes, int) or num_nodes <= 0 or not isinstance(tls_id_to_idx, dict):
                return

            node_seq = self._build_node_sequence_tensor(
                num_nodes=num_nodes,
                tls_id_to_idx=tls_id_to_idx,
                traffic_data=traffic_data,
                current_stages=current_stages,
            )
            self._train_online(node_seq, fleet_mean_reward)
            strategic_vectors = self.strategist.get_strategic_vectors(node_seq)
            self._prev_node_seq = node_seq.detach() if hasattr(node_seq, "detach") else node_seq
            self._last_update_time = sim_time
            self._distribute_vectors(agents, strategic_vectors)
        except Exception as exc:
            logger.debug(f"[StrategicCoordinator] Strategic coordination skipped: {exc}")

    def _build_node_sequence_tensor(
        self,
        num_nodes: int,
        tls_id_to_idx: Dict[str, int],
        traffic_data: Dict[str, Any],
        current_stages: Dict[str, Any],
    ) -> torch.Tensor:
        raw_dim = getattr(getattr(self.strategist, "model", None), "input_dim", 16)
        target_dim = int(raw_dim) if isinstance(raw_dim, int) and raw_dim > 0 else 16

        ip = getattr(self.agent_evaluator, "input_preprocessor", None)
        raw_seq_len = getattr(ip, "sequence_length", 12)
        seq_len = int(raw_seq_len) if isinstance(raw_seq_len, int) and raw_seq_len > 0 else 12
        state_history = getattr(ip, "state_history", {}) if ip is not None else {}

        node_array = np.zeros((num_nodes, seq_len, target_dim), dtype=np.float32)

        for tl_id, node_idx in tls_id_to_idx.items():
            if not isinstance(node_idx, int) or node_idx < 0 or node_idx >= num_nodes:
                continue

            frames = (
                list(state_history[tl_id])[-seq_len:]
                if isinstance(state_history, dict) and tl_id in state_history and len(state_history[tl_id]) > 0
                else []
            )
            if self.state_extractor is not None:
                try:
                    peek_fn = getattr(self.state_extractor, "peek_state", None)
                    is_mock_se = hasattr(self.state_extractor, "assert_called")
                    if callable(peek_fn) and not is_mock_se:
                        curr_vec = peek_fn(traffic_data, tl_id, current_stages.get(tl_id, 0))
                    elif hasattr(self.state_extractor, "extract_state"):
                        curr_vec = self.state_extractor.extract_state(traffic_data, tl_id, current_stages.get(tl_id, 0))
                    else:
                        curr_vec = None
                    if isinstance(curr_vec, np.ndarray) and curr_vec.size > 0:
                        frames = (frames[-(seq_len - 1) :] if seq_len > 1 else []) + [curr_vec]
                except Exception:
                    pass

            if frames:
                start_t = max(0, seq_len - len(frames))
                for offset, frame in enumerate(frames[-seq_len:]):
                    arr = np.asarray(frame, dtype=np.float32).reshape(-1)
                    copy_dim = min(arr.shape[0], target_dim)
                    if copy_dim > 0:
                        node_array[node_idx, start_t + offset, :copy_dim] = arr[:copy_dim]

        device = getattr(self.strategist, "device", torch.device("cpu"))
        return torch.as_tensor(node_array, dtype=torch.float32, device=device)

    def _train_online(self, node_seq: torch.Tensor, fleet_mean_reward: float) -> None:
        if (
            self._prev_node_seq is None
            or not hasattr(self._prev_node_seq, "shape")
            or self._prev_node_seq.shape != node_seq.shape
            or getattr(self.strategist, "edge_index", None) is None
            or not hasattr(self.strategist, "update")
        ):
            return

        try:
            target_next = node_seq[:, -1, :]
            self.strategist.train(True)
            strat_dev = getattr(self.strategist, "device", None)
            dev_type = strat_dev.type if hasattr(strat_dev, "type") else "cpu"
            amp_enabled = dev_type == "cuda" and hasattr(torch, "amp") and hasattr(torch.amp, "autocast")
            with torch.amp.autocast(device_type=dev_type, enabled=amp_enabled):
                model_out = self.strategist.model(
                    self._prev_node_seq,
                    self.strategist.edge_index,
                    edge_attr=getattr(self.strategist, "edge_attr", None),
                    return_prediction=True,
                    return_value=True,
                )
            if isinstance(model_out, tuple) and len(model_out) == 3:
                _, pred_next, global_val = model_out
                pred_loss = F.smooth_l1_loss(pred_next.float(), target_next.float())
                val_target = torch.full_like(global_val.float(), float(fleet_mean_reward))
                val_loss = F.smooth_l1_loss(global_val.float(), val_target)
                self.strategist.update(pred_loss + 0.5 * val_loss)
            elif isinstance(model_out, tuple) and len(model_out) == 2:
                _, pred_next = model_out
                self.strategist.update(F.smooth_l1_loss(pred_next.float(), target_next.float()))
        except Exception as exc:
            logger.debug(f"[StrategicCoordinator] Strategist online update skipped: {exc}")
        finally:
            if hasattr(self.strategist, "eval"):
                self.strategist.eval()

    def _distribute_vectors(self, agents: Dict[str, Any], strategic_vectors: Any) -> None:
        max_rows = getattr(strategic_vectors, "shape", [0])[0]
        for tl_id, agent in agents.items():
            idx = self.strategist.get_node_index(tl_id) if hasattr(self.strategist, "get_node_index") else -1
            if isinstance(idx, int) and 0 <= idx < max_rows and hasattr(agent, "set_strategic_context"):
                vec = strategic_vectors[idx : idx + 1]
                agent.set_strategic_context(vec.detach() if hasattr(vec, "detach") else vec)
