# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_infrastructure_client.py
# Author: Gabriel Moraes
# Date: September 2026

import queue
import time
from unittest.mock import MagicMock

from ui.clients.infrastructure_client import InfrastructureClient


def test_infrastructure_client_fetches_valid_result():
    mock_queue = queue.Queue()
    callback = MagicMock()

    client = InfrastructureClient(on_complete_callback=callback, sas_result_queue=mock_queue)

    t_trigger = time.time()
    payload = {"status": "success", "timestamp": t_trigger + 0.1, "report_content": "Test Report"}

    mock_queue.put(payload)

    # Run fetch directly (synchronously for unit testing)
    client._fetch_thread_target(trigger_time=t_trigger)

    callback.assert_called_once_with(payload)


def test_infrastructure_client_drains_stale_message_and_accepts_valid():
    mock_queue = queue.Queue()
    callback = MagicMock()

    client = InfrastructureClient(on_complete_callback=callback, sas_result_queue=mock_queue)

    t_trigger = time.time()
    stale_payload = {"status": "success", "timestamp": t_trigger - 10.0, "report_content": "Old Report"}
    valid_payload = {"status": "success", "timestamp": t_trigger + 0.1, "report_content": "New Report"}

    mock_queue.put(stale_payload)
    mock_queue.put(valid_payload)

    client._fetch_thread_target(trigger_time=t_trigger)

    callback.assert_called_once_with(valid_payload)


def test_infrastructure_client_accepts_result_with_slight_timestamp_lag():
    mock_queue = queue.Queue()
    callback = MagicMock()

    client = InfrastructureClient(on_complete_callback=callback, sas_result_queue=mock_queue)

    t_trigger = time.time()
    # Payload created 0.2s before trigger_time (microsecond drift/resolution tolerance test)
    payload = {"status": "success", "timestamp": t_trigger - 0.2, "report_content": "Valid Report"}

    mock_queue.put(payload)

    client._fetch_thread_target(trigger_time=t_trigger)

    callback.assert_called_once_with(payload)
