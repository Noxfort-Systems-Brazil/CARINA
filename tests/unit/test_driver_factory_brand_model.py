# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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
