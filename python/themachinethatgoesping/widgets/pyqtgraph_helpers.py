"""Utility helpers shared by PyQtGraph-based widget viewers."""
from __future__ import annotations

from datetime import datetime
from typing import Callable, Dict, List, Optional, Union

import ipywidgets
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets

__all__ = [
    "MatplotlibDateAxis",
    "TimedeltaAxis",
    "DistanceAxis",
    "ensure_qapp",
    "resolve_colormap",
    "list_colormaps",
    "apply_widget_layout",
]


class MatplotlibDateAxis(pg.AxisItem):
    """AxisItem that formats matplotlib-style ordinal dates."""

    def __init__(self, converter: Callable[[float], datetime], orientation: str = "bottom") -> None:
        super().__init__(orientation=orientation)
        self._converter = converter

    def tickStrings(self, values: List[float], scale: float, spacing: float) -> List[str]:  # noqa: N802
        labels: List[str] = []
        for value in values:
            try:
                dt_value = self._converter(float(value))
                labels.append(dt_value.strftime("%Y-%m-%d\n%H:%M:%S"))
            except Exception:  # pragma: no cover - formatting failure should not crash UI
                labels.append("")
        return labels


class TimedeltaAxis(pg.AxisItem):
    """AxisItem that formats seconds as human-readable time strings.

    The format is chosen once based on *max_seconds* (the overall data range)
    and stays fixed regardless of zoom level:

    - < 1 s:  "0.123 s"
    - < 60 s: "12.3 s"
    - < 1 h:  "05:23"  (mm:ss)
    - < 24 h: "1:05:23" (h:mm:ss)
    - >= 24 h: "2d 03:15" (Nd hh:mm)
    """

    def __init__(self, max_seconds: float = 60.0, orientation: str = "bottom") -> None:
        super().__init__(orientation=orientation)
        self._max_seconds = abs(max_seconds)

    def tickStrings(self, values: List[float], scale: float, spacing: float) -> List[str]:  # noqa: N802
        if not values:
            return []
        return [self._format_seconds(float(v), self._max_seconds) for v in values]

    @staticmethod
    def _format_seconds(total_seconds: float, max_seconds: float) -> str:
        negative = total_seconds < 0
        s = abs(total_seconds)
        prefix = "-" if negative else ""

        if max_seconds < 1:
            return f"{prefix}{s:.3f} s"
        if max_seconds < 60:
            return f"{prefix}{s:.1f} s"

        days = int(s // 86400)
        remainder = s - days * 86400
        hours = int(remainder // 3600)
        remainder -= hours * 3600
        minutes = int(remainder // 60)
        secs = int(remainder - minutes * 60)

        if max_seconds >= 86400 or days > 0:
            return f"{prefix}{days}d {hours:02d}:{minutes:02d}"
        if max_seconds >= 3600:
            return f"{prefix}{hours}:{minutes:02d}:{secs:02d}"
        # Minute-level
        total_min = int(s // 60)
        secs = int(s - total_min * 60)
        return f"{prefix}{total_min}:{secs:02d}"


class DistanceAxis(pg.AxisItem):
    """AxisItem for along-track distance that switches between m and km by zoom.

    When the visible span is below ``km_threshold_m`` meters the ticks and the
    axis label use meters; otherwise kilometers. The unit therefore adapts to
    the current zoom level (e.g. it shows meters once zoomed in below 5 km even
    if the full survey spans tens of kilometers).
    """

    def __init__(
        self,
        km_threshold_m: float = 10000.0,
        show_unit_label: bool = True,
        orientation: str = "bottom",
    ) -> None:
        self._km_threshold_m = abs(float(km_threshold_m))
        self._show_unit_label = show_unit_label
        self._use_km_cached: Optional[bool] = None
        # AxisItem.__init__ calls setRange(), so initialize fields first.
        super().__init__(orientation=orientation)
        # Manage the unit ourselves; disable pyqtgraph's own SI prefixing.
        self.enableAutoSIPrefix(False)
        if show_unit_label:
            self.setLabel(text="Distance (m)")

    def _use_km(self) -> bool:
        try:
            span = abs(self.range[1] - self.range[0])
        except Exception:  # pragma: no cover - defensive
            span = 0.0
        return span >= self._km_threshold_m

    def setRange(self, mn: float, mx: float) -> None:  # noqa: N802
        super().setRange(mn, mx)
        threshold = getattr(self, "_km_threshold_m", 5000.0)
        use_km = abs(mx - mn) >= threshold
        if use_km != self._use_km_cached:
            self._use_km_cached = use_km
            if self._show_unit_label:
                self.setLabel(text=f"Distance ({'km' if use_km else 'm'})")

    def tickValues(self, minVal: float, maxVal: float, size: int):  # noqa: N802
        """Ensure a fixed left-edge anchor tick in mixed mode.

        This guarantees that the absolute km label is always rendered on the
        left edge, independent of pyqtgraph's automatic tick placement.
        """
        levels = super().tickValues(minVal, maxVal, size)
        use_km = self._use_km_cached if self._use_km_cached is not None else self._use_km()
        if use_km or not levels:
            return levels

        spacing, values = levels[0]
        vals = [float(v) for v in values]
        tol = max(abs(float(spacing)) * 1e-6, 1e-9)
        if not any(abs(v - minVal) <= tol for v in vals):
            vals.append(float(minVal))
            vals.sort()

        out = list(levels)
        out[0] = (spacing, vals)
        return out

    def tickStrings(self, values: List[float], scale: float, spacing: float) -> List[str]:  # noqa: N802
        if not values:
            return []
        use_km = self._use_km_cached if self._use_km_cached is not None else self._use_km()
        if use_km:
            return self._format_km_ticks(values)
        return self._format_mixed_ticks(values, axis_min=self.range[0])

    @staticmethod
    def _format_km_label(v_m: float) -> str:
        """Format a single tick value (in metres) as a km label with adaptive precision."""
        km = float(v_m) / 1000.0
        if abs(km) >= 100:
            return f"{km:.0f} km"
        if abs(km) >= 10:
            return f"{km:.1f} km"
        return f"{km:.2f} km"

    @classmethod
    def _format_km_ticks(cls, values: List[float]) -> List[str]:
        """All ticks in km (used when span >= km_threshold)."""
        return [cls._format_km_label(v) for v in values]

    @classmethod
    def _format_mixed_ticks(cls, values: List[float], axis_min: Optional[float] = None) -> List[str]:
        """Left edge shows absolute km; all other ticks show +offset m.

        Offsets are relative to the floor-km anchor derived from ``axis_min``
        (or the smallest provided tick value when ``axis_min`` is not given).
        """
        if not values:
            return []
        floats = [float(v) for v in values]
        left = float(axis_min) if axis_min is not None else min(floats)
        # Anchor: floor km of the left edge
        anchor_m = int(left // 1000) * 1000  # metres, rounded down to km
        def _abs_label(v: float) -> str:
            km_int = int(v // 1000)
            m_off = round(v - km_int * 1000)
            if m_off == 0:
                return f"{km_int} km"
            return f"{km_int} km +{m_off} m"

        def _rel_label(v: float) -> str:
            offset = round(v - anchor_m)
            if offset == 0:
                return f"{anchor_m // 1000} km"
            return f"+{offset} m"

        # Find the tick closest to the left edge; only this one gets absolute km.
        left_idx = int(np.argmin([abs(v - left) for v in floats]))

        labels: List[str] = []
        for i, v in enumerate(floats):
            if i == left_idx:
                labels.append(_abs_label(v))
            else:
                labels.append(_rel_label(v))
        return labels

    # kept for backward-compatibility with existing tests
    @staticmethod
    def _format_distance_ticks(values: List[float], use_km: bool) -> List[str]:
        """Legacy helper: format ticks as plain km or plain m numbers."""
        if use_km:
            return [f"{float(v) / 1000.0:.3g}" for v in values]
        return [f"{float(v):.4g}" for v in values]


def ensure_qapp() -> None:
    """Ensure a QApplication exists for PyQtGraph widgets."""

    if QtWidgets.QApplication.instance() is None:
        QtWidgets.QApplication([])


def resolve_colormap(cmap) -> pg.ColorMap:
    """Return a PyQtGraph ColorMap from a name, pg.ColorMap, or matplotlib Colormap.
    
    Parameters
    ----------
    cmap : str, pg.ColorMap, or matplotlib.colors.Colormap
        Colormap name (pyqtgraph or matplotlib), a PyQtGraph ColorMap
        instance, or a matplotlib Colormap (e.g. ``colorcet.cm.CET_L20``).
    
    Returns
    -------
    pg.ColorMap
        Resolved colormap. Falls back to 'viridis' if not found.
    """

    if isinstance(cmap, pg.ColorMap):
        return cmap

    # Accept matplotlib Colormap objects (e.g. from colorcet)
    try:
        from matplotlib.colors import Colormap as MplColormap
        if isinstance(cmap, MplColormap):
            positions = np.linspace(0.0, 1.0, 256)
            colors = (cmap(positions) * 255).astype(np.uint8)
            return pg.ColorMap(positions, colors)
    except ImportError:
        pass

    if isinstance(cmap, str):
        try:
            return pg.colormap.get(cmap)
        except Exception:
            fallback = _matplotlib_colormap(cmap)
            if fallback is not None:
                return fallback
    return pg.colormap.get("viridis")


def list_colormaps(source: Optional[str] = None) -> List[str]:
    """List available colormap names.
    
    Parameters
    ----------
    source : str, optional
        Filter by source: 'pyqtgraph', 'matplotlib', or None for all.
    
    Returns
    -------
    List[str]
        Sorted list of colormap names that can be passed to :func:`resolve_colormap`.
    
    Examples
    --------
    >>> list_colormaps()                    # All colormaps
    >>> list_colormaps('matplotlib')        # Only matplotlib colormaps
    >>> list_colormaps('pyqtgraph')         # Only pyqtgraph colormaps
    """
    names: List[str] = []
    
    # PyQtGraph colormaps
    if source is None or source == "pyqtgraph":
        try:
            pg_names = pg.colormap.listMaps()
            if isinstance(pg_names, dict):
                # listMaps() returns dict with categories
                for category_maps in pg_names.values():
                    names.extend(category_maps)
            else:
                names.extend(pg_names)
        except Exception:  # pragma: no cover
            pass
    
    # Matplotlib colormaps
    if source is None or source == "matplotlib":
        try:
            import matplotlib
            mpl_names = list(matplotlib.colormaps)
            names.extend(mpl_names)
        except Exception:  # pragma: no cover - matplotlib optional
            pass
    
    return sorted(set(names))


def apply_widget_layout(widget: ipywidgets.Widget, width_px: int, height_px: int) -> None:
    """Attach a resizable layout to the GraphicsLayoutWidget wrapper."""

    width = f"{width_px}px"
    height = f"{height_px}px"
    layout = getattr(widget, "layout", None)
    if layout is None:
        layout = ipywidgets.Layout(
            width=width,
            height=height,
            min_height="0px",
            resize="vertical",
            overflow="auto",
        )
        widget.layout = layout
    else:
        layout.width = width
        layout.height = height
        layout.min_height = "0px"
        layout.resize = "vertical"
        layout.overflow = "auto"


def _matplotlib_colormap(name: str) -> Optional[pg.ColorMap]:
    """Convert a matplotlib colormap to a PyQtGraph ColorMap."""
    try:
        import matplotlib
    except Exception:  # pragma: no cover - matplotlib optional
        return None
    try:
        # Use modern API (matplotlib >= 3.7)
        cmap = matplotlib.colormaps.get_cmap(name)
    except (KeyError, AttributeError):
        # Fallback for older matplotlib or invalid name
        try:
            import matplotlib.cm as mpl_cm
            cmap = mpl_cm.get_cmap(name)
        except (ValueError, AttributeError):  # pragma: no cover
            return None
    positions = np.linspace(0.0, 1.0, 256)
    colors = (cmap(positions) * 255).astype(np.uint8)
    return pg.ColorMap(positions, colors)
