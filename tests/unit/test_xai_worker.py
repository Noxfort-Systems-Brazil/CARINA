# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import os
from unittest.mock import MagicMock, patch
import pytest

from src.xai.xai_worker import XaiWorker, run_xai_worker


@pytest.fixture
def worker_fixture(tmp_path):
    results_dir = str(tmp_path / "results" / "scen1")
    os.makedirs(results_dir, exist_ok=True)
    checkpoints_dir = os.path.join(results_dir, "checkpoints")
    os.makedirs(checkpoints_dir, exist_ok=True)

    with patch("src.xai.xai_worker.ReportPipeline") as MockPipe, \
         patch("src.xai.xai_worker.RequestScanner") as MockScan, \
         patch("src.xai.xai_worker.AgentReconstructor") as MockRecon:
        mock_pipe = MagicMock()
        mock_pipe.locale_manager = MagicMock()
        MockPipe.return_value = mock_pipe

        mock_scan = MagicMock()
        MockScan.return_value = mock_scan

        mock_recon = MagicMock()
        mock_recon.checkpoints_dir = checkpoints_dir
        MockRecon.return_value = mock_recon

        worker = XaiWorker(results_dir)
        return worker, results_dir, mock_scan, mock_recon, mock_pipe


def test_xai_worker_init(worker_fixture):
    worker, results_dir, mock_scan, mock_recon, mock_pipe = worker_fixture
    assert worker.scenario_results_dir == results_dir
    assert worker.scanner is mock_scan
    assert worker.reconstructor is mock_recon
    assert worker.pipeline is mock_pipe


def test_xai_worker_process_job_success(worker_fixture, tmp_path):
    worker, results_dir, mock_scan, mock_recon, mock_pipe = worker_fixture

    # Create dummy checkpoint files
    cp_dir = worker.reconstructor.checkpoints_dir
    with open(os.path.join(cp_dir, "agent_tl1.pth"), "w") as f:
        f.write("dummy")
    with open(os.path.join(cp_dir, "agent_ALL.pth"), "w") as f:
        f.write("dummy")

    mock_recon.reconstruct_agent.return_value = MagicMock()
    mock_pipe.generate_full_report.return_value = {
        "status": "complete",
        "image_base64": "img_b64",
        "text_content": "Report for tl1",
    }

    with patch("src.xai.xai_report_generator.XaiReportGenerator") as MockRepGen, \
         patch("src.database.database_manager.DatabaseManager") as MockDB:
        mock_db_inst = MagicMock()
        mock_db_inst.step_decision_repo.get_all_audited_agent_ids.return_value = ["tl1", "tl2"]
        MockDB.return_value = mock_db_inst

        mock_rep_gen = MagicMock()
        mock_rep_gen.generate_full_multi_agent_report.return_value = {
            "text_content": "Multi Agent Summary",
            "image_base64": "multi_img",
        }
        MockRepGen.return_value = mock_rep_gen

        worker.process_job("tl1")

        mock_scan.write_response.assert_called_once()
        resp_payload = mock_scan.write_response.call_args[0][1]
        assert resp_payload["status"] == "complete"
        assert resp_payload["text_content"] == "Multi Agent Summary"
        mock_scan.clear_request.assert_called_once_with("tl1")


def test_xai_worker_process_job_error_handled(worker_fixture):
    worker, _, mock_scan, mock_recon, _ = worker_fixture
    mock_recon.reconstruct_agent.side_effect = RuntimeError("Fatal reconstruction crash")

    with patch("src.xai.xai_report_generator.XaiReportGenerator", side_effect=RuntimeError("Report crash")):
        worker.process_job("tl_fail")

        mock_scan.write_response.assert_called_once()
        resp = mock_scan.write_response.call_args[0][1]
        assert resp["status"] == "error"
        mock_scan.clear_request.assert_called_once_with("tl_fail")


def test_xai_worker_run_forever(worker_fixture):
    worker, _, mock_scan, _, _ = worker_fixture

    mock_scan.get_pending_requests.side_effect = [
        ["tl_1"],
        [],
        KeyboardInterrupt(),
    ]
    worker.process_job = MagicMock()

    with patch("time.sleep", return_value=None):
        worker.run_forever()

    worker.process_job.assert_called_once_with("tl_1")


def test_run_xai_worker_entrypoint(tmp_path):
    settings = configparser.ConfigParser()
    scenario_dir = str(tmp_path / "scen")

    with patch("src.xai.xai_worker.XaiWorker") as MockWorker, \
         patch("src.utils.paths.get_base_output_dir", return_value=str(tmp_path)), \
         patch("src.utils.logging_setup.setup_logging"), \
         patch("os._exit") as mock_exit:
        mock_inst = MagicMock()
        mock_inst.run_forever.side_effect = KeyboardInterrupt()
        MockWorker.return_value = mock_inst

        run_xai_worker(settings, scenario_dir)

        mock_inst.run_forever.assert_called_once()
        mock_exit.assert_called_once_with(0)
