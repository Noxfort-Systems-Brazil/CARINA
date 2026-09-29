# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
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

# File: tests/unit/test_driver_factory_brand_model.py
# Author: Gabriel Moraes
# Date: September 2026

import pytest

from src.drivers.driver_factory import DriverFactory


def test_extract_brand_and_model_siemens():
    descr = "Siemens UTC Traffic Light Controller ST950 v4.2"
    brand, model = DriverFactory.extract_brand_and_model(descr)
    assert brand == "Siemens"
    assert model == "ST950"


def test_extract_brand_and_model_peek():
    descr = "Peek Traffic Controller M60 NTCIP 1202"
    brand, model = DriverFactory.extract_brand_and_model(descr)
    assert brand == "Peek"
    assert model == "M60"


def test_extract_brand_and_model_unknown():
    brand, model = DriverFactory.extract_brand_and_model(None)
    assert brand == "Não informado"
    assert model == "Não informado"

    brand2, model2 = DriverFactory.extract_brand_and_model("")
    assert brand2 == "Não informado"
    assert model2 == "Não informado"


def test_driver_factory_creates_go_proxy():
    from unittest.mock import MagicMock, patch

    from src.drivers.go_driver_proxy import GoTrafficDriverProxy

    mock_client = MagicMock()
    mock_client.is_running.return_value = True
    mock_client.connect_intersection.return_value = {
        "success": True,
        "data": {
            "protocol": "NTCIP 1202",
            "brand": "Econolite",
            "model": "ASC/3",
        },
    }

    with patch("src.drivers.go_gateway_client.GoGatewayClient.get_instance", return_value=mock_client):
        driver = DriverFactory.create_and_connect_driver(
            ip_address="192.168.1.50",
            port=161,
            intersection_id="J_FACTORY_TEST",
        )

        assert driver is not None
        assert isinstance(driver, GoTrafficDriverProxy)
        assert driver.get_protocol_name() == "NTCIP 1202"
        assert driver.brand == "Econolite"
        assert driver.model == "ASC/3"
