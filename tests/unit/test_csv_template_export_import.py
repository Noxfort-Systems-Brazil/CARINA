# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import tempfile

import pytest

from src.controller.connection_config_repo import ConnectionConfigRepository


def test_export_and_import_standard_csv():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "test_template.csv")
        saved_ips = {"Intersection_1": "192.168.1.10", "Intersection_2": "192.168.1.20"}
        known_intersections = ["Intersection_1", "Intersection_2", "Intersection_3"]

        # Export
        assert ConnectionConfigRepository.export_csv_template(csv_path, saved_ips, known_intersections) is True
        assert os.path.exists(csv_path)

        # Import
        imported = ConnectionConfigRepository.import_csv_config(csv_path)
        assert imported["Intersection_1"] == "192.168.1.10"
        assert imported["Intersection_2"] == "192.168.1.20"
        # Intersection_3 had empty IP, so not in active configured dictionary
        assert "Intersection_3" not in imported


def test_export_enforces_csv_extension():
    with tempfile.TemporaryDirectory() as tmpdir:
        no_ext_path = os.path.join(tmpdir, "test_template_no_ext")
        saved_ips = {"Intersection_1": "10.0.0.1"}
        known = ["Intersection_1"]

        assert ConnectionConfigRepository.export_csv_template(no_ext_path, saved_ips, known) is True
        expected_path = f"{no_ext_path}.csv"
        assert os.path.exists(expected_path)


def test_import_semicolon_excel_and_bom():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "excel_br.csv")
        # Simulating Excel PT-BR export with UTF-8 BOM and semicolon separator
        content = "\ufeffID do Cruzamento;Endereço IP\nCruzamento_A;10.1.1.50\nCruzamento_B;10.1.1.51\n"
        with open(csv_path, "w", encoding="utf-8-sig") as f:
            f.write(content)

        imported = ConnectionConfigRepository.import_csv_config(csv_path)
        assert imported["Cruzamento_A"] == "10.1.1.50"
        assert imported["Cruzamento_B"] == "10.1.1.51"


def test_import_tab_delimited_and_custom_headers():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "custom.tsv")
        content = "agent_id\thost\nTL_100\t172.16.0.10\nTL_101\t172.16.0.11\n"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(content)

        imported = ConnectionConfigRepository.import_csv_config(csv_path)
        assert imported["TL_100"] == "172.16.0.10"
        assert imported["TL_101"] == "172.16.0.11"
