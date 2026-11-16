# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Atomic Checkpoint Service for GuardianAgent Weights & Calibrator State.

Ensures `guardian_{tl_id}.pth` persists across sessions alongside local PPO agents
and `pae_universal.pth` in `{results_base}/results/hft_live_session/checkpoints/`
(and optionally map-specific checkpoint directories via AgentCheckpointRepository).
"""

import logging
import os
from typing import Any, Dict, Optional

import torch

from src.utils.paths import get_base_output_dir


class GuardianCheckpointService:
    """Handles atomic save/restore of GuardianAgent networks, optimizer, and calibrator state."""

    @classmethod
    def get_live_checkpoint_dir(cls) -> str:
        """Returns the active HFT session checkpoint directory."""
        return os.path.join(get_base_output_dir(), "results", "hft_live_session", "checkpoints")

    @staticmethod
    def _safe_id(tl_id: str) -> str:
        return str(tl_id).replace(":", "_").replace("/", "_")

    @classmethod
    def save_guardian(
        cls,
        tl_id: str,
        guardian: Any,
        checkpoints_dir: Optional[str] = None,
        maturity_stage: Optional[str] = None,
    ) -> Optional[str]:
        """Atomically writes `guardian_{safe_id}.pth` with weights and calibration metadata."""
        target_dir = checkpoints_dir or cls.get_live_checkpoint_dir()
        os.makedirs(target_dir, exist_ok=True)
        path = os.path.join(target_dir, f"guardian_{cls._safe_id(tl_id)}.pth")
        tmp_path = f"{path}.tmp"

        calibrator = getattr(guardian, "calibrator", None)
        optimizer = getattr(guardian, "optimizer", None)
        target_net = getattr(guardian, "target_net", None)
        is_frozen = bool(getattr(guardian, "is_frozen", False))
        if is_frozen and getattr(guardian, "_frozen_checkpoint_saved", None) == path and os.path.exists(path):
            return path

        payload: Dict[str, Any] = {
            "policy_net_state_dict": guardian.policy_net.state_dict(),
            "target_net_state_dict": target_net.state_dict() if target_net is not None else None,
            "steps_done": int(getattr(guardian, "steps_done", 0)),
            "is_frozen": is_frozen,
            "maturity_stage": maturity_stage or ("TEEN" if is_frozen else "CHILD"),
            "calibrator_state": calibrator.to_state_dict() if calibrator is not None else None,
        }
        if optimizer is not None and hasattr(optimizer, "state_dict"):
            try:
                payload["optimizer_state_dict"] = optimizer.state_dict()
            except Exception:
                pass

        try:
            torch.save(payload, tmp_path)
            os.replace(tmp_path, path)
            if is_frozen:
                try:
                    guardian._frozen_checkpoint_saved = path
                except Exception:
                    pass
            return path
        except Exception as exc:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            logging.error(f"[GuardianCheckpoint] Failed saving {tl_id} to {path}: {exc}", exc_info=True)
            return None

    @classmethod
    def save_all(
        cls,
        guardians: Optional[Dict[str, Any]],
        checkpoints_dir: Optional[str] = None,
        maturity_manager: Any = None,
    ) -> int:
        """Persists all provided GuardianAgent instances."""
        if not guardians:
            return 0
        saved = 0
        maturity_map = None
        if maturity_manager is not None:
            if callable(getattr(maturity_manager, "get_maturity_map", None)) and isinstance(
                getattr(maturity_manager, "_agents", None), dict
            ):
                maturity_map = maturity_manager.get_maturity_map()
            elif hasattr(maturity_manager, "agent_maturity"):
                maturity_map = maturity_manager.agent_maturity
        for tl_id, guardian in guardians.items():
            stage = None
            if maturity_map is not None:
                phase = maturity_map.get(tl_id)
                if phase is not None:
                    stage = str(getattr(phase, "name", phase))
            if cls.save_guardian(tl_id, guardian, checkpoints_dir=checkpoints_dir, maturity_stage=stage):
                saved += 1
        return saved

    @classmethod
    def load_guardian(
        cls,
        tl_id: str,
        guardian: Any,
        checkpoints_dir: Optional[str] = None,
        device: Optional[Any] = None,
    ) -> bool:
        """Loads GuardianAgent weights and calibrator state if checkpoint exists."""
        target_dir = checkpoints_dir or cls.get_live_checkpoint_dir()
        path = os.path.join(target_dir, f"guardian_{cls._safe_id(tl_id)}.pth")
        if not os.path.exists(path):
            return False

        map_loc = device or getattr(guardian, "device", "cpu")
        try:
            try:
                data = torch.load(path, map_location=map_loc, weights_only=True)
            except Exception:
                data = torch.load(path, map_location=map_loc, weights_only=False)

            if isinstance(data, dict) and "policy_net_state_dict" in data:
                guardian.policy_net.load_state_dict(data["policy_net_state_dict"])
                target_sd = data.get("target_net_state_dict") or data["policy_net_state_dict"]
                if getattr(guardian, "target_net", None) is not None:
                    guardian.target_net.load_state_dict(target_sd)
                if "steps_done" in data:
                    guardian.steps_done = int(data["steps_done"])
                if "optimizer_state_dict" in data and getattr(guardian, "optimizer", None) is not None:
                    try:
                        guardian.optimizer.load_state_dict(data["optimizer_state_dict"])
                    except Exception:
                        pass
                cal_state = data.get("calibrator_state")
                if isinstance(cal_state, dict) and getattr(guardian, "calibrator", None) is not None:
                    guardian.calibrator.load_state_dict(cal_state)
                if data.get("is_frozen"):
                    if callable(getattr(guardian, "freeze_for_deployment", None)):
                        guardian.freeze_for_deployment()
                    else:
                        guardian.is_frozen = True
                    try:
                        guardian._frozen_checkpoint_saved = path
                    except Exception:
                        pass
            else:
                guardian.policy_net.load_state_dict(data)
                if getattr(guardian, "target_net", None) is not None:
                    guardian.target_net.load_state_dict(guardian.policy_net.state_dict())
            return True
        except Exception as exc:
            logging.warning(f"[GuardianCheckpoint] Failed loading {tl_id} from {path}: {exc}", exc_info=True)
            return False

    @classmethod
    def load_all(
        cls,
        guardians: Optional[Dict[str, Any]],
        checkpoints_dir: Optional[str] = None,
        device: Optional[Any] = None,
    ) -> int:
        """Restores all GuardianAgent checkpoints found in `checkpoints_dir`."""
        if not guardians:
            return 0
        loaded = 0
        for tl_id, guardian in guardians.items():
            if cls.load_guardian(tl_id, guardian, checkpoints_dir=checkpoints_dir, device=device):
                loaded += 1
        return loaded
