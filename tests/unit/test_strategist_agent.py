# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
from unittest.mock import MagicMock, patch

import pytest
import torch

import src.agents.strategist_agent as sa
from src.agents.strategist_agent import StrategistAgent


@pytest.fixture
def mock_sumo_net():
    """Creates a fake traffic mesh (structural graph) where A points to B and C."""
    net = MagicMock()

    # Create Nodes
    node_a = MagicMock()
    node_b = MagicMock()
    node_c = MagicMock()

    node_a.getID.return_value = "TL_A"
    node_b.getID.return_value = "TL_B"
    node_c.getID.return_value = "TL_C"

    # Map A -> B and A -> C
    edge_ab = MagicMock()
    edge_ab.getToNode.return_value = node_b
    edge_ac = MagicMock()
    edge_ac.getToNode.return_value = node_c

    node_a.getOutgoing.return_value = [edge_ab, edge_ac]
    node_b.getOutgoing.return_value = []
    node_c.getOutgoing.return_value = []

    # Traffic Lights on network
    tls_a = MagicMock()
    tls_a.getID.return_value = "TL_A"
    tls_b = MagicMock()
    tls_b.getID.return_value = "TL_B"
    tls_c = MagicMock()
    tls_c.getID.return_value = "TL_C"

    net.getTrafficLights.return_value = [tls_a, tls_b, tls_c]

    def get_node(tl_id):
        return {"TL_A": node_a, "TL_B": node_b, "TL_C": node_c}.get(tl_id)

    net.getNode = get_node
    return net


@patch.object(sa.os.path, "exists", return_value=True)  # Fakes that SUMO XML exists
@patch.object(sa.sumolib.net, "readNet")
@patch.object(sa, "GATv2Lite")
@patch.object(sa.optim, "Adam")
def test_strategist_topology_builder(mock_adam, mock_gat, mock_readnet, mock_exists, mock_sumo_net):
    """Ensures Breadth-First Search (BFS) maps physical connections correctly."""
    mock_readnet.return_value = mock_sumo_net

    # Instance
    agent = StrategistAgent(input_dim=10, hidden_dim=8, output_dim=4, map_path="dummy.xml")

    # 3 mocked Traffic Lights
    assert agent.num_nodes == 3
    assert agent.tls_id_to_idx["TL_A"] == 0
    assert agent.tls_id_to_idx["TL_B"] == 1
    assert agent.tls_id_to_idx["TL_C"] == 2

    # Edges must be [0 -> 1] and [0 -> 2] for Pytorch Geometric Edge Index
    edges_tensor = agent.edge_index
    assert edges_tensor is not None

    # source_nodes = [0, 0]
    # target_nodes = [1, 2]
    # edge_index.shape should be [2, 2]
    assert tuple(edges_tensor.shape) == (2, 2)
    # Sources list
    assert edges_tensor[0][0].item() == 0
    assert edges_tensor[0][1].item() == 0
    # Targets list
    assert edges_tensor[1][0].item() == 1
    assert edges_tensor[1][1].item() == 2


@patch.object(sa.os.path, "exists", return_value=True)
@patch.object(sa.sumolib.net, "readNet")
@patch.object(sa, "GATv2Lite")
@patch.object(sa.optim, "Adam")
def test_strategic_vectors_generation(mock_adam, mock_gat, mock_readnet, mock_exists, mock_sumo_net):
    """Tests context features extraction (Strategist Action)."""
    mock_readnet.return_value = mock_sumo_net

    agent = StrategistAgent(input_dim=10, hidden_dim=8, output_dim=4, map_path="dummy.xml")

    # Mocking GATv2 output
    mock_nn_output = torch.zeros((3, 4))  # 3 nodes, dimension 4
    agent.model.return_value = mock_nn_output

    # Fake tensor
    fake_node_features = torch.rand((3, 10))

    result = agent.get_strategic_vectors(fake_node_features)
    assert tuple(result.shape) == (3, 4)


def test_st_gatv2_lite_causal_temporal_layers():
    """Verifies that STGATv2Lite correctly instantiates causal TCN and GATv2 layers with edge dimensions."""
    from src.models.st_gatv2_lite import STGATv2Lite, TemporalConvNetLite

    model = STGATv2Lite(
        input_dim=10,
        hidden_dim=16,
        output_dim=8,
        heads=2,
        edge_dim=3,
        pred_dim=10,
    )

    assert model.input_dim == 10
    assert model.hidden_dim == 16
    assert model.output_dim == 8
    assert model.edge_dim == 3
    assert model.pred_dim == 10
    assert isinstance(model.tcn, TemporalConvNetLite)
    assert hasattr(model, "conv1")
    assert hasattr(model, "conv2")
    assert hasattr(model, "pred_head")


@patch.object(sa.os.path, "exists", return_value=True)
@patch.object(sa.sumolib.net, "readNet")
@patch.object(sa, "GATv2Lite")
@patch.object(sa.optim, "Adam")
def test_strategist_agent_wrapper_methods(mock_adam, mock_gat, mock_readnet, mock_exists, mock_sumo_net):
    """Tests .to(), .eval(), .train(), __call__(), and update() on StrategistAgent."""
    mock_readnet.return_value = mock_sumo_net
    agent = StrategistAgent(input_dim=10, hidden_dim=8, output_dim=4, map_path="dummy.xml", device="cpu")

    # Configure mock output
    mock_out = torch.zeros((3, 4))
    agent.model.return_value = mock_out

    # Wrappers
    assert agent.eval() is agent
    assert agent.train() is agent
    assert agent.to("cpu") is agent

    # Callable __call__
    x = torch.rand((3, 10))
    out = agent(x)
    assert tuple(out.shape) == (3, 4)

    # Update step
    loss_mock = MagicMock()
    loss_mock.item.return_value = 0.42
    loss_val = agent.update(loss_mock)
    assert loss_val == 0.42

