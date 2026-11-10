# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Stage Derivator
---------------
Utility functions for deriving yellow and all-red states from green states.
"""


def derive_yellow_state(green_state: str) -> str:
    """
    Derive the yellow transition state from a green state.
    Replace all G/g with 'y', keep 'r' as 'r'.

    Args:
        green_state: The green state string

    Returns:
        The derived yellow state string
    """
    return "".join("y" if c in ("G", "g") else "r" for c in green_state)
