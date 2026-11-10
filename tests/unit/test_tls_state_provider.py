# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later


import pytest

from sds.tls_map_extractor import TlsMapExtractor
from sds.tls_state_provider import TlsStateProvider


@pytest.mark.unit
def test_get_live_states_for_junction_direct_mapping():
    # Setup test scenario
    tl_id = "J_TEST"

    # Manually populate TlsMapExtractor cached topology details
    TlsMapExtractor._tl_phases[tl_id] = {0: "GGggrrrr", 1: "yyyyrrrr", 2: "rrrrGGgg"}

    TlsMapExtractor._tl_connections[tl_id] = {
        0: {"edge": "edge_east", "dir": "s"},
        1: {"edge": "edge_east", "dir": "l"},
        2: {"edge": "edge_west", "dir": "s"},
        3: {"edge": "edge_west", "dir": "l"},
        4: {"edge": "edge_north", "dir": "s"},
        5: {"edge": "edge_north", "dir": "l"},
        6: {"edge": "edge_south", "dir": "s"},
        7: {"edge": "edge_south", "dir": "l"},
    }

    # 1. Test phase index 0 (Green for East/West)
    state = TlsStateProvider.get_live_states_for_junction([], tl_id, 0)
    assert state["display_state"] == "GREEN"
    assert state["lanes_state"]["edge_east (S)"] == "G"
    assert state["lanes_state"]["edge_west (S)"] == "G"
    assert state["lanes_state"]["edge_north (S)"] == "r"
    assert state["lanes_state"]["edge_south (S)"] == "r"

    # 2. Test phase index 1 (Yellow for East/West)
    state = TlsStateProvider.get_live_states_for_junction([], tl_id, 1)
    assert state["display_state"] == "YELLOW"
    assert state["lanes_state"]["edge_east (S)"] == "y"
    assert state["lanes_state"]["edge_north (S)"] == "r"

    # 3. Test phase index 2 (Green for North/South)
    state = TlsStateProvider.get_live_states_for_junction([], tl_id, 2)
    assert state["display_state"] == "GREEN"
    assert state["lanes_state"]["edge_east (S)"] == "r"
    assert state["lanes_state"]["edge_north (S)"] == "G"

    # Clean up test modifications
    TlsMapExtractor._tl_phases.pop(tl_id, None)
    TlsMapExtractor._tl_connections.pop(tl_id, None)
