# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for src/database/worker_monitor.py
"""

from unittest.mock import MagicMock, patch
import pytest

from src.database.worker_monitor import WorkerMonitor


class TestWorkerMonitor:
    def test_worker_monitor_lifecycle(self):
        mock_queue = MagicMock()
        mock_queue.qsize.return_value = 12

        with patch("src.database.worker_monitor.MetricsManager") as mock_metrics_cls:
            mock_metrics = MagicMock()
            mock_metrics_cls.return_value = mock_metrics

            monitor = WorkerMonitor(
                process_name="test_worker",
                port=9100,
                monitered_queues={"db_data": mock_queue},
            )

            assert mock_metrics.register_metric.call_count == 3

            # Test start_loop executes one iteration then stops
            with patch("time.sleep", side_effect=lambda s: monitor.stop()):
                monitor.start_loop(interval=1)

            assert mock_metrics.update_metric.called
            mock_metrics.update_metric.assert_any_call("db_data_queue_size", 12)
