# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Decodes physical NTCIP 1202 / UTMC2 hardware bitmasks and telemetry dictionaries
into 0-based SUMO signal stage indices for closed-loop feedback and F.E.N.I.X. handover.
"""

from typing import Any, Dict, Iterable, List, Optional


def safe_telemetry_int(value: Any, default: int = 0) -> int:
    """Safely extracts an integer from telemetry values, ignoring booleans and mocks."""
    if isinstance(value, bool) or value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped)
    return default


def resolve_tl_key(tl_id: str, mapping: Any) -> Optional[str]:
    """Resolves exact or tl_-prefixed/stripped key inside a dictionary."""
    if not isinstance(mapping, dict):
        return None
    s_id = str(tl_id)
    alt_id = s_id[3:] if s_id.startswith("tl_") else f"tl_{s_id}"
    for candidate in (s_id, alt_id):
        if candidate in mapping:
            return candidate
    return None


def _compute_signal_mask(state_str: str, chars: Iterable[str]) -> int:
    mask = 0
    target_chars = set(chars)
    for idx, ch in enumerate(state_str):
        if ch in target_chars:
            mask |= 1 << (idx % 8)
    return mask


def decode_stage_from_telemetry(
    telemetry: Any,
    green_stages: Optional[List[int]] = None,
    stage_codes: Optional[Dict[int, str]] = None,
    current_stage_hint: Optional[int] = None,
) -> Optional[int]:
    """
    Maps a controller telemetry packet (NTCIP/UTMC bitmasks & current_stage) to a 0-based SUMO stage index.
    Returns None when telemetry is missing, offline, or insufficient to decode safely.
    """
    if not isinstance(telemetry, dict):
        return None

    status = str(telemetry.get("status", "")).strip().lower()
    if status != "online":
        return None

    greens = safe_telemetry_int(telemetry.get("active_greens", 0))
    yellows = safe_telemetry_int(telemetry.get("active_yellows", 0))
    reds = safe_telemetry_int(telemetry.get("active_reds", 0))
    hw_curr = safe_telemetry_int(telemetry.get("current_stage", 0))
    protocol = str(telemetry.get("protocol", "")).upper()

    g_list = [int(s) for s in green_stages] if isinstance(green_stages, (list, tuple)) else []
    codes = {int(k): str(v) for k, v in stage_codes.items()} if isinstance(stage_codes, dict) else {}
    total_stages = len(codes)

    # 1. Active green bitmask present
    if greens > 0:
        if "UTMC" in protocol and g_list:
            # UTMC2 StatusActive reports 1 << ordinal position in green_stages
            matching_ordinals = [pos for pos in range(len(g_list)) if (greens & (1 << pos)) != 0]
            if len(matching_ordinals) == 1:
                return g_list[matching_ordinals[0]]

        if codes:
            candidate_stages = g_list if g_list else sorted(codes.keys())
            exact_matches = [
                s for s in candidate_stages if s in codes and _compute_signal_mask(codes[s], ("G", "g")) == greens
            ]
            if len(exact_matches) == 1:
                return exact_matches[0]

        # Ordinal single-bit fallback (e.g., NTCIP StageToPhaseMap 1 << pos)
        if g_list and (greens & (greens - 1)) == 0:
            pos = greens.bit_length() - 1
            if 0 <= pos < len(g_list):
                return g_list[pos]

        # NTCIP 1-based hardware stage fallback when bitmask differs (multi-movement StageToPhaseMap)
        if hw_curr >= 1:
            if "UTMC" in protocol and g_list and hw_curr <= len(g_list):
                return g_list[hw_curr - 1]
            if not codes or (hw_curr - 1) in codes:
                return hw_curr - 1

    # 2. Active yellow intergreen (no greens active)
    if greens == 0 and yellows > 0 and codes and total_stages > 0:
        yellow_matches = [
            s for s, st in codes.items() if "y" in st.lower() and _compute_signal_mask(st, ("Y", "y")) == yellows
        ]
        if len(yellow_matches) == 1:
            return yellow_matches[0]

        if isinstance(current_stage_hint, int):
            if "y" in codes.get(current_stage_hint, "").lower():
                return current_stage_hint
            nxt = (current_stage_hint + 1) % total_stages
            if "y" in codes.get(nxt, "").lower():
                return nxt

        if g_list and (yellows & (yellows - 1)) == 0:
            pos = yellows.bit_length() - 1
            if 0 <= pos < len(g_list):
                nxt = (g_list[pos] + 1) % total_stages
                if "y" in codes.get(nxt, "").lower():
                    return nxt

    # 3. All-red clearance (neither green nor yellow active)
    if greens == 0 and yellows == 0 and reds > 0 and codes and total_stages > 0 and isinstance(current_stage_hint, int):
        curr_str = codes.get(current_stage_hint, "").lower()
        if "g" not in curr_str and "y" not in curr_str and curr_str:
            return current_stage_hint
        nxt = (current_stage_hint + 1) % total_stages
        nxt_str = codes.get(nxt, "").lower()
        if nxt_str and "g" not in nxt_str and "y" not in nxt_str:
            return nxt

    # 4. Online driver without signal bitmasks populated yet
    if hw_curr >= 1:
        if "UTMC" in protocol and g_list and hw_curr <= len(g_list):
            return g_list[hw_curr - 1]
        if not codes or (hw_curr - 1) in codes:
            return hw_curr - 1

    return None
