# SPDX-FileCopyrightText: 2024 Peter Urban, Ghent University
#
# SPDX-License-Identifier: MPL-2.0

"""Unit tests for the distance-axis formatting and station-time mapping."""

import types

import numpy as np

from themachinethatgoesping.widgets.echogramviewer_core import (
    EchogramCore,
    timestamp_to_axis_coordinate,
)
from themachinethatgoesping.widgets.pyqtgraph_helpers import DistanceAxis


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


class TestDistanceAxisTicks:
    """The distance axis switches plain-km <-> mixed-anchor format based on span."""

    # ---- legacy helper still works ----
    def test_legacy_meters(self):
        out = DistanceAxis._format_distance_ticks([0.0, 500.0, 1000.0], use_km=False)
        assert out == ["0", "500", "1000"]

    def test_legacy_km(self):
        out = DistanceAxis._format_distance_ticks([0.0, 5000.0, 10000.0], use_km=True)
        assert out == ["0", "5", "10"]

    # ---- plain km ticks (used when span >= threshold) ----
    def test_format_km_ticks_sub_10(self):
        out = DistanceAxis._format_km_ticks([0.0, 5000.0, 10000.0])
        assert out == ["0.00 km", "5.00 km", "10.0 km"]

    def test_format_km_ticks_large(self):
        out = DistanceAxis._format_km_ticks([140000.0, 145000.0, 150000.0])
        assert out == ["140 km", "145 km", "150 km"]

    # ---- mixed anchor format (used when span < threshold) ----
    def test_mixed_single_tick(self):
        # Only one tick -> treated as both left and right -> absolute label
        out = DistanceAxis._format_mixed_ticks([140300.0])
        assert out == ["140 km +300 m"]

    def test_mixed_two_ticks_on_km_boundary(self):
        out = DistanceAxis._format_mixed_ticks([140000.0, 141000.0])
        assert out == ["140 km", "+1000 m"]

    def test_mixed_left_right_absolute_middle_relative(self):
        ticks = [140300.0, 141000.0, 141700.0, 142400.0]
        out = DistanceAxis._format_mixed_ticks(ticks)
        assert out[0] == "140 km +300 m", f"got {out[0]}"
        assert out[-1] == "+2400 m", f"got {out[-1]}"
        # Middle ticks: relative to anchor = floor(140300/1000)*1000 = 140000 m
        assert out[1] == "+1000 m", f"got {out[1]}"   # 141000 - 140000
        assert out[2] == "+1700 m", f"got {out[2]}"   # 141700 - 140000

    def test_mixed_offset_zero_middle(self):
        # A middle tick that falls exactly on the anchor km shows anchor km label
        ticks = [140000.0, 140000.0, 141000.0]
        out = DistanceAxis._format_mixed_ticks(ticks)
        assert out[1] == "140 km"  # offset from anchor 140000 is 0


def _fake_cs(ping_times, ping_numbers=None, custom_pp=None, custom_name=None):
    return types.SimpleNamespace(
        ping_times=np.asarray(ping_times, dtype=float),
        ping_numbers=(np.asarray(ping_numbers) if ping_numbers is not None else None),
        _custom_x_per_ping=(np.asarray(custom_pp, dtype=float) if custom_pp is not None else None),
        _custom_x_axis_name=custom_name,
    )


class TestTimestampToAxisCoordinate:
    """Station times must map onto distance / ping-index axes correctly."""

    def test_distance_axis_interpolates(self):
        ping_times = [100.0, 101.0, 102.0, 103.0]
        dist = [0.0, 10.0, 20.0, 30.0]
        cs = _fake_cs(ping_times, custom_pp=dist, custom_name="Distance")
        coord = timestamp_to_axis_coordinate(cs, "Distance", 101.5)
        assert abs(coord - 15.0) < 1e-6

    def test_distance_axis_endpoints(self):
        cs = _fake_cs([100.0, 110.0], custom_pp=[0.0, 1000.0], custom_name="Distance")
        assert timestamp_to_axis_coordinate(cs, "Distance", 100.0) == 0.0
        assert timestamp_to_axis_coordinate(cs, "Distance", 110.0) == 1000.0

    def test_ping_index_uses_searchsorted(self):
        cs = _fake_cs([100.0, 101.0, 102.0, 103.0], ping_numbers=[0, 1, 2, 3])
        assert timestamp_to_axis_coordinate(cs, "Ping index", 102.0) == 2.0

    def test_ping_number_offset(self):
        cs = _fake_cs([100.0, 101.0, 102.0], ping_numbers=[10, 11, 12])
        assert timestamp_to_axis_coordinate(cs, "Ping index", 101.0) == 11.0

    def test_unmatched_custom_axis_returns_none(self):
        cs = _fake_cs([100.0, 101.0], custom_pp=[0.0, 5.0], custom_name="Other")
        assert timestamp_to_axis_coordinate(cs, "Distance", 100.5) is None

    def test_empty_pingtimes_returns_none(self):
        cs = _fake_cs([])
        assert timestamp_to_axis_coordinate(cs, "Ping index", 1.0) is None

    def test_none_cs_returns_none(self):
        assert timestamp_to_axis_coordinate(None, "Distance", 1.0) is None
