# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Stage Extractor
---------------
Utility functions for extracting green stages from SUMO traffic light programs.
"""


def extract_green_stages(tls_id: str, original_stages: list, green_chars: frozenset) -> list:
    """
    From the full SUMO stage list, extract all stages (no filtering).

    Args:
        tls_id: The ID of the traffic light system
        original_stages: List of original SUMO stages
        green_chars: Set of characters considered as green signals

    Returns:
        List of stage state strings
    """
    return [stage.state for stage in original_stages]
