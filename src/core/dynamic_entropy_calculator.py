# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import math
from typing import Optional


class DynamicEntropyCalculator:
    """
    Calculates dynamic entropy thresholds based on the time configured in the UI.
    Ensures that AI certainty requirements respect urban engineering safety ceilings.
    """

    def __init__(
        self,
        n_actions: int = 2,
        e_max: Optional[float] = None,
        e_ideal: float = 0.1,
        normalize: bool = False,
    ) -> None:
        """
        Initializes the dynamic entropy calculator.

        Args:
            n_actions: Number of discrete actions in the policy action space (default: 2 — ADVANCE/KEEP).
            e_max: Safety ceiling (maximum chaos allowed). If None or higher than the theoretical
                   maximum entropy ln(n_actions) (or 1.0 if normalize=True), it is clamped to
                   prevent impossible entropy thresholds where random policies would be promoted.
            e_ideal: Absolute certainty limit (perfect convergence, default: 0.1).
            normalize: If True, operates on normalized entropy in the range [0.0, 1.0].
        """
        self.n_actions = max(2, int(n_actions))
        self.normalize = bool(normalize)
        self.max_theoretical_entropy = 1.0 if self.normalize else math.log(self.n_actions)

        if e_max is None:
            self.e_max = self.max_theoretical_entropy
        else:
            # Prevent impossible thresholds: e_max can never exceed theoretical maximum entropy
            self.e_max = min(float(e_max), self.max_theoretical_entropy)

        self.e_ideal = max(0.0, min(float(e_ideal), self.e_max))

    def normalize_entropy(self, entropy: float) -> float:
        """
        Normalizes raw Shannon entropy (in nats) to [0.0, 1.0] by dividing by ln(n_actions).

        Args:
            entropy: Shannon entropy in nats.

        Returns:
            Normalized entropy value in [0.0, 1.0].
        """
        max_ent = math.log(self.n_actions)
        if max_ent <= 0.0:
            return 0.0
        return max(0.0, min(1.0, float(entropy) / max_ent))

    def calculate_threshold(self, configured_episodes: int, is_adult_transition: bool = False) -> float:
        """
        Calculates the maximum allowed entropy threshold for an agent's promotion.
        The more time (episodes) configured, the stricter (closer to e_ideal) the threshold becomes.

        Args:
            configured_episodes: The time limit set by the user in the menu.
            is_adult_transition: If True, applies an extremely rigorous decay curve (Teen -> Adult).

        Returns:
            The calculated entropy threshold (float).
        """
        if configured_episodes <= 0:
            return self.e_max

        # Decay constant k.
        k = 0.05

        if is_adult_transition:
            # Rigorous transition to Adult: we multiply the decay constant
            # to force the threshold down aggressively, demanding near-absolute certainty.
            k = 0.15

        # Exponential decay formula: E(t) = E_ideal + (E_max - E_ideal) * e^(-k * t)
        threshold = self.e_ideal + (self.e_max - self.e_ideal) * math.exp(-k * configured_episodes)

        # Clamp between ideal and max for absolute safety
        return max(self.e_ideal, min(self.e_max, threshold))
