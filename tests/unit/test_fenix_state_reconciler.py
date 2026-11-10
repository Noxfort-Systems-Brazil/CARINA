# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from src.fenix.state_reconciler import StateReconciler


def test_state_reconciler_option_b_clean_boundary_handover():
    """
    Tests the Option B Clean Boundary Handover flow:
    1. Reconcile with field stages (e.g. node_1 at Stage 5, node_2 at Stage 3).
    2. Inference must be FROZEN for both nodes during their respective initial stages.
    3. Untracked nodes default to inference allowed.
    4. Transition to NEXT stage unlocks inference for each node individually.
    """
    reconciler = StateReconciler()

    # Step 1: Sync with field
    reconciler.reconcile_with_field({"node_1": 5, "node_2": 3})

    # Step 2: Nodes are frozen
    assert reconciler.is_inference_allowed("node_1") is False
    assert reconciler.is_inference_allowed("node_2") is False
    assert reconciler.is_all_unfrozen() is False
    assert reconciler.get_current_stage("node_1") == 5
    assert reconciler.get_current_stage("node_2") == 3

    # Untracked node is allowed
    assert reconciler.is_inference_allowed("node_untracked") is True

    # Step 3: Ticks in the same stage do NOT unlock
    unlocked = reconciler.on_stage_transition_detected("node_1", 5)
    assert unlocked is False
    assert reconciler.is_inference_allowed("node_1") is False

    # Step 4: Field hardware transitions node_1 to Stage 6 (Option B Handover)
    unlocked = reconciler.on_stage_transition_detected("node_1", 6)
    assert unlocked is True
    assert reconciler.is_inference_allowed("node_1") is True
    assert reconciler.get_current_stage("node_1") == 6

    # node_2 is still frozen at stage 3
    assert reconciler.is_inference_allowed("node_2") is False
    assert reconciler.is_all_unfrozen() is False

    # Step 5: Field hardware transitions node_2 to Stage 1 (Option B Handover)
    unlocked_2 = reconciler.on_stage_transition_detected("node_2", 1)
    assert unlocked_2 is True
    assert reconciler.is_inference_allowed("node_2") is True
    assert reconciler.is_all_unfrozen() is True

    # Summary
    summary = reconciler.get_status_summary()
    assert summary["node_1"]["is_unfrozen"] is True
    assert summary["node_2"]["is_unfrozen"] is True

    # Reset
    reconciler.reset()
    assert reconciler.is_all_unfrozen() is True
    assert reconciler.is_inference_allowed("node_1") is True
