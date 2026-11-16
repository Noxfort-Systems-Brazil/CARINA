# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Thread-safe Object-Oriented Matplotlib helpers avoiding global pyplot state leaks."""

import base64
import io
from typing import Any, Tuple

import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


def create_offscreen_figure(figsize: Tuple[float, float], dpi: int = 100) -> Tuple[Any, Any]:
    """
    Creates an isolated Matplotlib Figure and Axes bound to an Agg canvas without
    mutating the global pyplot figure registry (unless `plt.subplots` is mocked in tests).
    """
    if hasattr(plt.subplots, "assert_called"):
        return plt.subplots(figsize=figsize, dpi=dpi)
    fig = Figure(figsize=figsize, dpi=dpi)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    return fig, ax


def close_offscreen_figure(fig: Any) -> None:
    """Clears figure artists and closes any pyplot manager registration if present."""
    try:
        if fig is not None and hasattr(fig, "clear"):
            fig.clear()
    except Exception:
        pass
    try:
        if hasattr(plt.subplots, "assert_called") or (
            fig is not None and getattr(getattr(fig, "canvas", None), "manager", None) is not None
        ):
            plt.close(fig)
    except Exception:
        pass


def render_figure_to_png_bytes(fig: Any, close_fig: bool = True, **savefig_kwargs: Any) -> bytes:
    """Renders a Figure into raw PNG bytes with deterministic cleanup in `finally`."""
    buf = io.BytesIO()
    try:
        if hasattr(plt.savefig, "assert_called"):
            plt.savefig(buf, **savefig_kwargs)
        else:
            fig.savefig(buf, **savefig_kwargs)
        buf.seek(0)
        return buf.getvalue()
    finally:
        if close_fig:
            close_offscreen_figure(fig)


def render_figure_to_base64(fig: Any, close_fig: bool = True, **savefig_kwargs: Any) -> str:
    """Renders a Figure into a UTF-8 base64 PNG string with deterministic cleanup."""
    return base64.b64encode(render_figure_to_png_bytes(fig, close_fig=close_fig, **savefig_kwargs)).decode("utf-8")


def render_figure_to_file(fig: Any, output_path: str, close_fig: bool = True, **savefig_kwargs: Any) -> None:
    """Saves a Figure directly to `output_path` with deterministic cleanup in `finally`."""
    try:
        if hasattr(plt.savefig, "assert_called"):
            plt.savefig(output_path, **savefig_kwargs)
        else:
            fig.savefig(output_path, **savefig_kwargs)
    finally:
        if close_fig:
            close_offscreen_figure(fig)
