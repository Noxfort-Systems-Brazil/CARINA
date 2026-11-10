# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import unittest
from unittest.mock import MagicMock, patch

from src.sds.sds_process_starter import SDSProcessStarter


class TestSDSProcessStarter(unittest.TestCase):
    """Unit tests for SDS autonomous process manager."""

    def setUp(self):
        self.starter = SDSProcessStarter()
        self.starter._process = None
        self.starter._started_by_us = False

    def test_singleton_instance(self):
        inst1 = SDSProcessStarter.get_instance()
        inst2 = SDSProcessStarter.get_instance()
        self.assertIs(inst1, inst2)

    @patch("urllib.request.urlopen")
    def test_is_port_active_true(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        self.assertTrue(self.starter.is_port_active(8550))

    @patch("urllib.request.urlopen", side_effect=OSError("Connection refused"))
    def test_is_port_active_false(self, mock_urlopen):
        self.assertFalse(self.starter.is_port_active(8550))

    @patch.object(SDSProcessStarter, "is_orchestrator_running", return_value=False)
    @patch.object(SDSProcessStarter, "is_port_active", side_effect=[False, True])
    @patch("multiprocessing.Process")
    def test_start_if_not_running_launches_process(self, mock_proc_cls, mock_is_active, mock_is_orch):
        mock_proc = MagicMock()
        mock_proc.is_alive.return_value = True
        mock_proc.pid = 12345
        mock_proc_cls.return_value = mock_proc

        result = self.starter.start_if_not_running(port=8550)
        self.assertTrue(result)
        self.assertTrue(mock_proc.start.called)
        self.assertTrue(self.starter._started_by_us)
        self.assertIsNotNone(self.starter._sds_q)
        self.assertIsNotNone(self.starter._ui_cmd_q)

    @patch.object(SDSProcessStarter, "is_orchestrator_running", return_value=True)
    def test_start_if_not_running_skips_when_orchestrator_running(self, mock_is_orch):
        with patch.object(self.starter, "is_port_active", return_value=False):
            result = self.starter.start_if_not_running(port=8550)
            self.assertTrue(result)
            self.assertIsNone(self.starter._process)
            self.assertFalse(self.starter._started_by_us)

    def test_stop_terminates_started_process(self):
        mock_proc = MagicMock()
        mock_proc.is_alive.side_effect = [True, False]
        self.starter._process = mock_proc
        self.starter._started_by_us = True
        mock_q1 = MagicMock()
        mock_q2 = MagicMock()
        self.starter._sds_q = mock_q1
        self.starter._ui_cmd_q = mock_q2

        self.starter.stop()
        self.assertTrue(mock_proc.terminate.called)
        self.assertIsNone(self.starter._process)
        self.assertFalse(self.starter._started_by_us)
        self.assertTrue(mock_q1.close.called)
        self.assertTrue(mock_q2.close.called)
        self.assertIsNone(self.starter._sds_q)
        self.assertIsNone(self.starter._ui_cmd_q)


if __name__ == "__main__":
    unittest.main()
