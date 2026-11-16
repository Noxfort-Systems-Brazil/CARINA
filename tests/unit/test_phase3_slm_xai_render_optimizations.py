# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from blocks.report_number_formatter import ReportNumberFormatter
from rendering.basemap_tile_client import BasemapTileClient
from rendering.mpl_utils import close_offscreen_figure, create_offscreen_figure, render_figure_to_png_bytes
from sas.report_generator import ReportGenerator
from sas.report_transducer_factory import ReportTransducerFactory
from sas.sas_helpers import SyntheticSampleGenerator, TrafficMetricsCalculator
from slm.device_manager import SLMDeviceManager
from slm.model_loader import SLMModelLoader
from slm.semantic_transducer import SemanticTransducer
from slm.slm_lock import slm_process_lock
from xai.report_pipeline import ReportPipeline
from xai.xai_report_generator import XaiReportGenerator
from xai.xai_worker import XaiWorker


def test_slm_process_lock_is_reentrant_without_deadlock(tmp_path):
    with patch("utils.paths.get_base_output_dir", return_value=str(tmp_path)):
        with slm_process_lock():
            with slm_process_lock():
                assert os.path.exists(tmp_path / "locks" / "slm_gguf.lock")


def test_slm_device_manager_uses_pynvml_for_partial_and_cpu_fallback():
    fake_handle = object()
    fake_mem_partial = MagicMock(free=int(2.2 * 1024**3), total=int(8.0 * 1024**3))
    fake_mem_low = MagicMock(free=int(1.1 * 1024**3), total=int(8.0 * 1024**3))
    fake_pynvml = MagicMock()
    fake_pynvml.nvmlDeviceGetHandleByIndex.return_value = fake_handle

    with (
        patch.dict(sys.modules, {"pynvml": fake_pynvml}),
        patch("slm.device_manager._torch_cuda_is_mocked", return_value=False),
    ):
        fake_pynvml.nvmlDeviceGetMemoryInfo.return_value = fake_mem_partial
        dev, layers = SLMDeviceManager.resolve_device_settings("auto", gpu_layers=12)
        assert dev == "gpu"
        assert layers == 12

        fake_pynvml.nvmlDeviceGetMemoryInfo.return_value = fake_mem_low
        dev2, layers2 = SLMDeviceManager.resolve_device_settings("auto", gpu_layers=12)
        assert dev2 == "cpu"
        assert layers2 == 0


def test_model_loader_unload_releases_llm():
    mock_llm = MagicMock()
    SLMModelLoader.unload_model(mock_llm)
    mock_llm.close.assert_called_once()

    st = SemanticTransducer.__new__(SemanticTransducer)
    st.model = mock_llm
    st.unload()
    assert st.model is None


def test_xai_worker_reuses_captum_results_and_runs_slm_only_once(tmp_path):
    mock_agent = MagicMock()
    mock_captum_res = {
        "image_base64": "aW1n",
        "text_report": "Sensor: Queue (0.5)",
        "sorted_analysis": [{"name": "Queue", "importance": 0.5}],
    }
    captured_precomputed = {}

    def fake_multi_report(self, primary_agent_id=None, precomputed_analyses=None):
        captured_precomputed["keys"] = sorted(list((precomputed_analyses or {}).keys()))
        return {"status": "complete", "image_base64": "Z2xvYmFs", "text_content": "Consolidated MD"}

    with patch.object(
        ReportPipeline,
        "__init__",
        lambda self, sdir, rdir: setattr(self, "scenario_results_dir", sdir)
        or setattr(self, "reports_dir", rdir)
        or setattr(self, "locale_manager", MagicMock())
        or setattr(self, "transducer_script", "dummy.py"),
    ):
        worker = XaiWorker(str(tmp_path))
        worker.scanner = MagicMock()
        worker.reconstructor = MagicMock()
        worker.reconstructor.checkpoints_dir = str(tmp_path / "checkpoints")
        os.makedirs(worker.reconstructor.checkpoints_dir, exist_ok=True)
        for aid in ["J1", "J2", "J3"]:
            open(os.path.join(worker.reconstructor.checkpoints_dir, f"agent_{aid}.pth"), "w").close()

        worker.reconstructor.reconstruct_agent.return_value = mock_agent
        worker.pipeline.locale_manager.get_language.return_value = "pt_br"

        slm_calls = []

        def fake_analyze(self_analyzer):
            return dict(mock_captum_res)

        def fake_subproc(cmd, **kwargs):
            slm_calls.append(cmd)
            return MagicMock(returncode=0, stdout="SLM report", stderr="")

        with (
            patch("xai.report_pipeline.CaptumAnalyzer") as mock_ca_cls,
            patch("xai.report_pipeline.subprocess.run", side_effect=fake_subproc),
            patch.object(XaiReportGenerator, "generate_full_multi_agent_report", fake_multi_report),
        ):
            mock_ca_cls.return_value.generate_analysis_in_memory.side_effect = lambda: dict(mock_captum_res)
            worker.process_job("J2")

        assert len(slm_calls) == 1
        assert captured_precomputed["keys"] == ["J1", "J2", "J3"]
        worker.scanner.write_response.assert_called_once()


def test_xai_report_generator_skips_reconstruct_when_precomputed(tmp_path):
    gen = XaiReportGenerator(str(tmp_path), locale_manager=MagicMock())
    gen.reconstructor = MagicMock()
    gen.repository = MagicMock()
    gen.repository.discover_audited_agent_ids.return_value = ["J1", "J2"]
    gen.aggregator = MagicMock()
    gen.aggregator.aggregate_network_analysis.return_value = {"global_image_base64": "Z2xvYmFs"}
    gen.report_builder = MagicMock()
    gen.report_builder.build_markdown.return_value = "Report body"

    precomputed = {
        "J1": {"image_base64": "aW1nMQ==", "sorted_analysis": []},
        "J2": {"image_base64": "aW1nMg==", "sorted_analysis": []},
    }
    res = gen.generate_full_multi_agent_report(primary_agent_id="J1", precomputed_analyses=precomputed)
    gen.reconstructor.reconstruct_agent.assert_not_called()
    assert res["status"] == "complete"
    assert res["image_base64"] == "aW1nMQ=="


def test_sas_report_generator_skips_light_eval_slm_calls_and_unloads():
    mock_transducer = MagicMock()
    mock_transducer.generate_report.return_value = "Generated text."
    mock_transducer.review_text.side_effect = lambda txt, language="pt_br": txt

    junctions = {
        "J1": {
            "primary_edges": {"e1": [{"density": 5.0, "mean_speed": 10.0, "queue_length": 2}]},
            "secondary_edges": {},
            "type": "traffic_light",
            "volume": 300,
        },
        "J2": {
            "primary_edges": {"e2": [{"density": 8.0, "mean_speed": 8.0, "queue_length": 4}]},
            "secondary_edges": {},
            "type": "traffic_light",
            "volume": 450,
        },
    }

    with (
        patch.object(ReportTransducerFactory, "create_transducer", return_value=mock_transducer),
        patch.object(
            ReportTransducerFactory, "release_transducer", wraps=ReportTransducerFactory.release_transducer
        ) as mock_rel,
    ):
        _, md = ReportGenerator.generate_report(junctions, has_last_report=False, has_significant_change=False)

    assert md is not None
    called_modes = [
        call.args[0].get("mode")
        for call in mock_transducer.generate_report.call_args_list
        if isinstance(call.args[0], dict)
    ]
    assert "LIGHT_EVALUATION" not in called_modes
    mock_transducer.unload.assert_called_once()
    mock_rel.assert_called_once_with(mock_transducer)


def test_sas_helpers_compute_percentiles_exact_and_single_accumulated():
    freq = {0: 5, 3: 10, 8: 25, 15: 60}
    expected = [TrafficMetricsCalculator.get_percentile(freq, i / 100.0) for i in range(100)]
    actual = TrafficMetricsCalculator.compute_percentiles(freq, 100)
    assert actual == expected
    assert TrafficMetricsCalculator.compute_percentiles({}, 100) == [0] * 100

    acc = SyntheticSampleGenerator.generate_accumulated("e1", 12.0, 9.5, 120.0, 2, 13.89)
    assert len(acc) == 1
    assert acc[0]["edge_id"] == "e1" and acc[0]["density"] == 12.0


def test_report_number_formatter_respects_thousands_separator():
    mock_sm = MagicMock()
    mock_sm.config_path = None
    mock_sm.get_setting.side_effect = lambda sec, key, default=None: {
        ("REPORT_FORMATTING", "decimal_separator"): ",",
        ("REPORT_FORMATTING", "thousands_separator"): ".",
    }.get((sec, key), default)

    with patch("utils.settings_manager.SettingsManager", return_value=mock_sm):
        assert ReportNumberFormatter.format_number(1234.5, 1) == "1.234,5"

    mock_sm_space = MagicMock()
    mock_sm_space.config_path = None
    mock_sm_space.get_setting.side_effect = lambda sec, key, default=None: {
        ("REPORT_FORMATTING", "decimal_separator"): ".",
        ("REPORT_FORMATTING", "thousands_separator"): ",",
    }.get((sec, key), default)

    with patch("utils.settings_manager.SettingsManager", return_value=mock_sm_space):
        assert ReportNumberFormatter.format_number(1234.5, 1) == "1,234.5"


def test_basemap_tile_client_closes_session_and_returns_image():
    buf = io.BytesIO()
    Image.new("RGB", (256, 256), color=(200, 200, 200)).save(buf, format="PNG")
    png_bytes = buf.getvalue()

    fake_session = MagicMock()
    fake_session.__enter__.return_value = fake_session
    fake_session.get.return_value = MagicMock(status_code=200, content=png_bytes)

    with patch("rendering.basemap_tile_client.requests.Session", return_value=fake_session):
        img, count = BasemapTileClient.fetch_and_stitch_tiles(15, 0, 0, 0, 0)

    assert count == 1
    assert img.size == (256, 256)
    fake_session.__exit__.assert_called_once()


def test_oo_matplotlib_helper_does_not_leak_pyplot_figures():
    import matplotlib.pyplot as plt

    plt.close("all")
    before = len(plt.get_fignums())
    fig, ax = create_offscreen_figure((2.0, 2.0), dpi=72)
    ax.plot([0, 1], [0, 1])
    raw = render_figure_to_png_bytes(fig, format="png")
    close_offscreen_figure(fig)
    after = len(plt.get_fignums())

    assert len(raw) > 50
    assert after == before == 0
