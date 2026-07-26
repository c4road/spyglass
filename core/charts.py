"""Plotly chart builders for SpyGlass — pure figure factories, no Streamlit.

Kept separate from the lenses so the plotting is reusable and the lens stays a
thin render layer. Colors follow a validated categorical/status palette (see the
data-viz method): a muted base distribution, a red loss tail, and amber→orange
VaR→CVaR markers (a warning→serious escalation, since CVaR sits deeper in the
tail than VaR). VaR/CVaR lines carry direct text labels, so identity never rests
on color alone.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Palette (validated). Two steps per role for light/dark surfaces.
_C = {
    "light": {
        "bars": "#9aa0a6",   # muted neutral — the base distribution
        "tail": "#e34948",   # red — loss region beyond VaR
        "var": "#eda100",    # amber — VaR marker (warning)
        "cvar": "#eb6834",   # orange — CVaR marker (serious, deeper in tail)
        "text": "#0b0b0b",
        "surface": "#fcfcfb",
    },
    "dark": {
        "bars": "#8a8f94",
        "tail": "#e66767",
        "var": "#c98500",
        "cvar": "#d95926",
        "text": "#ffffff",
        "surface": "#1a1a19",
    },
}


def return_distribution(
    returns: pd.Series,
    var_fraction: float,
    cvar_fraction: float,
    confidence: float = 0.95,
    theme: str = "light",
    bins: int = 60,
) -> go.Figure:
    """Histogram of daily returns with VaR and CVaR percentile markers.

    Parameters
    ----------
    returns : pd.Series
        Daily returns (fractional, e.g. -0.02 = −2%).
    var_fraction, cvar_fraction : float
        Positive fractional losses (as produced by ``core.risk``). Drawn as
        vertical lines at ``-var_fraction`` / ``-cvar_fraction`` on the return
        axis (i.e. on the loss side).
    confidence : float
        VaR/CVaR confidence, for the labels (0.95 → "95%").
    theme : {"light", "dark"}
        Palette variant to match the surrounding page.
    bins : int
        Histogram bin count.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    c = _C.get(theme, _C["light"])
    r = pd.Series(returns).dropna().astype(float) * 100.0  # percent for readability
    var_pct = -var_fraction * 100.0
    cvar_pct = -cvar_fraction * 100.0
    pct_label = f"{int(round(confidence * 100))}%"

    # Split bars into the loss tail (≤ VaR) and the body, so the tail reads red.
    lo, hi = float(r.min()), float(r.max())
    edges = np.linspace(lo, hi, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2.0
    counts, _ = np.histogram(r, bins=edges)
    tail_mask = centers <= var_pct
    bar_colors = [c["tail"] if t else c["bars"] for t in tail_mask]

    fig = go.Figure()
    fig.add_bar(
        x=centers,
        y=counts,
        width=(edges[1] - edges[0]) * 0.92,  # 2px-ish surface gap between bars
        marker_color=bar_colors,
        marker_line_width=0,
        hovertemplate="return %{x:.2f}%<br>%{y} days<extra></extra>",
        showlegend=False,
    )

    y_max = counts.max() if counts.size else 1
    # VaR and CVaR vertical markers with direct labels (relief for the amber WARN).
    # The two lines can sit very close together (CVaR is only slightly deeper than
    # VaR), so labels are STACKED at different heights — never relying on horizontal
    # spacing to avoid overlap. A short leader arrow ties each label to its line.
    for value, color, name, y_frac in (
        (cvar_pct, c["cvar"], f"CVaR {pct_label}: {cvar_pct:.2f}%", 0.97),
        (var_pct, c["var"], f"VaR {pct_label}: {var_pct:.2f}%", 0.82),
    ):
        fig.add_shape(
            type="line", x0=value, x1=value, y0=0, y1=y_max,
            line=dict(color=color, width=2, dash="solid"),
        )
        fig.add_annotation(
            x=value, y=y_max * y_frac, text=name,
            showarrow=True, arrowhead=0, arrowwidth=1, arrowcolor=color,
            ax=-28, ay=0,               # label sits to the LEFT of its line, same height
            xanchor="right", yanchor="middle",
            font=dict(color=color, size=12),
            bgcolor="rgba(255,255,255,0.0)",
        )

    fig.update_layout(
        title=None,
        xaxis_title="Daily return (%)",
        yaxis_title="Days",
        bargap=0,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=c["text"]),
        margin=dict(l=10, r=10, t=30, b=10),
        height=380,
    )
    fig.update_xaxes(showgrid=False, zeroline=True, zerolinecolor="rgba(128,128,128,0.35)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)", zeroline=False)
    return fig
