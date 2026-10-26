"""Plotly figures shared by CLI artifacts and the application."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

COLORS = {"ordinary": "#62a8fa", "antithetic": "#b89aff", "control": "#44d7b6"}


def style(fig, title, x, y, height=350):
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=title, font=dict(size=16)),
        paper_bgcolor="#0b1018",
        plot_bgcolor="#0b1018",
        font=dict(family="Arial", color="#c8d4e3"),
        height=height,
        margin=dict(l=45, r=20, t=55, b=45),
        xaxis_title=x,
        yaxis_title=y,
        legend=dict(orientation="h", y=-0.22, x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor="#1d2a3a", zeroline=False)
    fig.update_yaxes(gridcolor="#1d2a3a", zeroline=False)
    return fig


def path_chart(times, values):
    fig = go.Figure()
    palette = ["#44d7b6", "#62a8fa", "#b89aff", "#eab76a"]
    for i, line in enumerate(values):
        fig.add_trace(
            go.Scatter(
                x=times,
                y=line,
                mode="lines",
                line=dict(width=1, color=palette[i % 4]),
                opacity=0.65,
                name=f"Path {i + 1}",
                showlegend=False,
                hovertemplate="t=%{x:.3f} years<br>S=%{y:.3f}<extra>%{fullData.name}</extra>",
            )
        )
    return style(
        fig, "01 / Risk-neutral price paths", "Time (years)", "Underlying (currency units)"
    )


def payoff_chart(payoffs):
    zero = float(np.mean(payoffs == 0))
    fig = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.2, 0.8],
        subplot_titles=["Point mass at zero", "Positive payoffs"],
        horizontal_spacing=0.16,
    )
    fig.add_trace(
        go.Bar(
            x=["Zero"],
            y=[100 * zero],
            marker_color="#eab76a",
            name="Zero-payoff probability",
            hovertemplate="Zero payoff: %{y:.2f}%<extra></extra>",
        ),
        row=1,
        col=1,
    )
    positive = payoffs[payoffs > 0]
    # Fixed bins produce exact counts and retain total probability, including zeros.
    if len(positive):
        counts, edges = np.histogram(positive, bins=45)
        fig.add_trace(
            go.Bar(
                x=(edges[1:] + edges[:-1]) / 2,
                y=100 * counts / len(payoffs),
                width=np.diff(edges),
                marker_color="#62a8fa",
                name="Positive payoff probability",
                hovertemplate=(
                    "Discounted payoff ≈ %{x:.3f}<br>Total probability: %{y:.2f}%<extra></extra>"
                ),
            ),
            row=1,
            col=2,
        )
    fig = style(fig, "02 / Discounted payoff distribution", "", "Probability (%)")
    fig.update_layout(showlegend=False)
    fig.update_yaxes(range=[0, 100], row=1, col=1)
    fig.update_xaxes(title_text="Discounted payoff (currency units)", row=1, col=2)
    return fig


def convergence_chart(curve, reference, method, reference_label="Black–Scholes"):
    color = COLORS[method]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=curve.sample_count,
            y=curve.ci_high,
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=curve.sample_count,
            y=curve.ci_low,
            fill="tonexty",
            fillcolor="rgba(68,215,182,.13)",
            line=dict(width=0),
            name="Pointwise ≈95% CI",
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=curve.sample_count,
            y=curve.price,
            line=dict(color=color, width=2),
            name=method.title(),
            hovertemplate="Budget used: %{x:,}<br>Estimate: %{y:.5f}<extra></extra>",
        )
    )
    if reference is not None:
        fig.add_hline(
            y=reference,
            line_dash="dash",
            line_color="#eab76a",
            annotation_text=f"{reference_label} {reference:.5f}",
        )
    fig = style(
        fig,
        "03 / Price convergence",
        "Payoff evaluations (pilot included)",
        "Option price (currency units)",
        410,
    )
    fig.update_xaxes(type="log" if curve.sample_count.max() > 0 else "linear")
    return fig


def research_charts(summary):
    rmse = go.Figure()
    timing = go.Figure()
    for (case, method), g in summary.groupby(["case_id", "method"]):
        g = g.sort_values("sample_count")
        rmse.add_trace(
            go.Scatter(
                x=g.sample_count,
                y=g.rmse,
                error_y=dict(type="data", array=1.96 * g.rmse_se),
                mode="lines+markers",
                name=f"{case} · {method}",
                line=dict(color=COLORS[method]),
                legendgroup=method,
            )
        )
        timing.add_trace(
            go.Scatter(
                x=g.mean_runtime_seconds,
                y=g.rmse,
                mode="lines+markers",
                name=f"{case} · {method}",
                line=dict(color=COLORS[method]),
                legendgroup=method,
            )
        )
    for f in [rmse, timing]:
        f.update_layout(showlegend=False)
        f.update_xaxes(type="log")
        f.update_yaxes(type="log")
    return {
        "rmse": style(
            rmse, "Repeated-seed RMSE (bars: delta-method ≈95%)", "Total payoff budget", "RMSE", 650
        ),
        "error_time": style(
            timing, "Error versus measured runtime", "Mean wall time (seconds)", "RMSE", 650
        ),
    }
