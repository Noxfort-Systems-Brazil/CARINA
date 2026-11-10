# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import gzip
import os
import tempfile
import pytest

from src.utils.sumo_geo_bounds_reader import SumoGeoBounds, SumoGeoBoundsReader


def test_read_bounds_plain_xml():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<net version="1.20" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <location netOffset="-500000.00,-7000000.00" convBoundary="100.0,200.0,1500.0,1200.0" origBoundary="-46.6610,-23.5650,-46.6320,-23.5410" projParameter="+proj=utm +zone=23 +ellps=WGS84"/>
    <edge id="e1"/>
</net>
"""
    with tempfile.NamedTemporaryFile("w", suffix=".net.xml", delete=False) as f:
        f.write(xml_content)
        temp_path = f.name

    try:
        bounds = SumoGeoBoundsReader.read_bounds(temp_path)
        assert bounds is not None
        assert isinstance(bounds, SumoGeoBounds)
        assert bounds.min_lon == -46.6610
        assert bounds.min_lat == -23.5650
        assert bounds.max_lon == -46.6320
        assert bounds.max_lat == -23.5410
        assert bounds.min_x == 100.0
        assert bounds.min_y == 200.0
        assert bounds.max_x == 1500.0
        assert bounds.max_y == 1200.0
        assert bounds.net_offset == (-500000.00, -7000000.00)
        assert bounds.proj_parameter == "+proj=utm +zone=23 +ellps=WGS84"
        assert bounds.has_geo_coords is True
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_read_bounds_gzipped_xml():
    xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<net version="1.20">
    <location netOffset="0.0,0.0" convBoundary="0.0,0.0,500.0,500.0" origBoundary="-43.20,-22.90,-43.15,-22.85"/>
</net>
"""
    with tempfile.NamedTemporaryFile("wb", suffix=".net.xml.gz", delete=False) as f:
        with gzip.GzipFile(fileobj=f, mode="wb") as gz:
            gz.write(xml_content)
        temp_path = f.name

    try:
        bounds = SumoGeoBoundsReader.read_bounds(temp_path)
        assert bounds is not None
        assert bounds.min_lon == -43.20
        assert bounds.max_lat == -22.85
        assert bounds.max_x == 500.0
        assert bounds.has_geo_coords is True
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_read_bounds_missing_file():
    bounds = SumoGeoBoundsReader.read_bounds("/non/existent/path/network.net.xml")
    assert bounds is None


def test_read_bounds_no_location_tag():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<net version="1.20">
    <edge id="e1"/>
</net>
"""
    with tempfile.NamedTemporaryFile("w", suffix=".net.xml", delete=False) as f:
        f.write(xml_content)
        temp_path = f.name

    try:
        bounds = SumoGeoBoundsReader.read_bounds(temp_path)
        assert bounds is None
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
