# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
EVP Preemption Evaluator (Engine Layer / SOLID: SRP).
Queries active emergency preemption state and disarms offline/silent vehicles.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EvpPreemptionEvaluator:
    """Evaluates active EVP green corridor status for a specific traffic light."""

    @staticmethod
    def get_evp_preemption_state(tl_id: str) -> Optional[str]:
        """
        Queries whether the intersection is under emergency preemption (EVP).
        Returns 'EVP:<vehicle_id>' or 'EVP' if active, or None for normal traffic.
        """
        try:
            from evp.evp_service import EVPService

            service = EVPService.get_instance()
            if service and service.is_preemption_active(tl_id):
                preempt = getattr(service, "preemption_engine", None)
                if preempt and hasattr(preempt, "_active_preemptions"):
                    info = preempt._active_preemptions.get(tl_id, {})
                    v_id = str(info.get("vehicle_id", "")).strip()
                    # Defensive self-cleanup: if vehicle turned off siren or went offline, disarm
                    if v_id and hasattr(service, "_vehicles"):
                        vehicle = service._vehicles.get(v_id)
                        if vehicle and (not vehicle.is_online or not vehicle.siren_active):
                            service.release_preemption(tl_id, v_id)
                            return None
                    return f"EVP:{v_id}" if v_id else "EVP"
                return "EVP"
        except Exception as exc:
            logger.warning("[EvpPreemptionEvaluator] Falha ao consultar estado EVP para %s: %s", tl_id, exc, exc_info=True)
        return None
