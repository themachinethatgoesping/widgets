# SPDX-FileCopyrightText: 2024 Peter Urban, Ghent University
#
# SPDX-License-Identifier: MPL-2.0

"""Unit tests for the distance-axis hover formatter in the echogram viewer."""

from themachinethatgoesping.widgets.echogramviewer_core import EchogramCore


class TestFormatDistance:
    def test_meters(self):
        assert EchogramCore._format_distance(500.0) == "500.0 m"

    def test_kilometers(self):
        assert EchogramCore._format_distance(2500.0) == "2.500 km"
        assert "km" in EchogramCore._format_distance(1500.0)

    def test_centimeters(self):
        assert EchogramCore._format_distance(0.5) == "50.0 cm"
        assert EchogramCore._format_distance(0.0) == "0.0 cm"

    def test_negative(self):
        # sign preserved, unit chosen by magnitude
        assert EchogramCore._format_distance(-2000.0) == "-2.000 km"
