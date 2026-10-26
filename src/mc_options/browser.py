"""Browser-hosted adapter. Uses the same validated estimators as the native Python app.

Only NumPy/SciPy and Python's standard library are required at runtime. Files returned
by this adapter are kept in each visitor's browser, never a shared server directory.
"""

import base64
import csv
import hashlib
import io
import json
import platform
import uuid
import zipfile
from dataclasses import asdict
from datetime import UTC, datetime

import numpy as np
import scipy

from mc_options.config import Option, validate_budget
from mc_options.evaluation.convergence import convergence_data
from mc_options.models.asian import geometric_price, simulate_asian, validate_dates
from mc_options.models.estimators import METHODS, simulate
from mc_options.models.sampling import paths

MAX_BROWSER_SAMPLES = 200_000
RUNTIME_METADATA = {}
COLORS = {"ordinary": "#62a8fa", "antithetic": "#b89aff", "control": "#c2ed83"}


def configure_runtime(metadata_json):
    RUNTIME_METADATA.update(json.loads(metadata_json))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def figure(data, x, y, height=290, **layout):
    axis = {"gridcolor": "#202a35", "zeroline": False, "automargin": True}
    return {
        "data": data,
        "layout": {
            "template": "plotly_dark",
            "height": height,
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": {"family": "Arial, sans-serif", "size": 11, "color": "#8795a8"},
            "margin": {"l": 52, "r": 22, "t": 32, "b": 48},
            "hovermode": "x unified",
            "showlegend": False,
            "xaxis": {**axis, "title": {"text": x}},
            "yaxis": {**axis, "title": {"text": y}},
            **layout,
        },
    }


def visual_paths(times, values):
    palette = ["#44d7b6", "#62a8fa", "#b89aff", "#eab76a"]
    data = [
        {
            "type": "scatter",
            "mode": "lines",
            "x": times.tolist(),
            "y": v.tolist(),
            "name": f"Path {i + 1}",
            "line": {"width": 1, "color": palette[i % 4]},
            "opacity": 0.65,
            "hovertemplate": "t=%{x:.3f} years<br>S=%{y:.3f}<extra>%{fullData.name}</extra>",
        }
        for i, v in enumerate(values)
    ]
    return figure(data, "Time (years)", "Underlying (currency units)")


def payoff_figure(raw):
    zero = float(np.mean(raw == 0))
    data = [
        {
            "type": "bar",
            "x": ["Zero"],
            "y": [100 * zero],
            "marker": {"color": "#eab76a"},
            "name": "Zero-payoff probability",
            "hovertemplate": "Zero payoff: %{y:.2f}%<extra></extra>",
        }
    ]
    positive = raw[raw > 0]
    if len(positive):
        counts, edges = np.histogram(positive, bins=45)
        data.append(
            {
                "type": "bar",
                "x": ((edges[:-1] + edges[1:]) / 2).tolist(),
                "y": (100 * counts / len(raw)).tolist(),
                "width": np.diff(edges).tolist(),
                "xaxis": "x2",
                "yaxis": "y2",
                "marker": {"color": "#62a8fa"},
                "hovertemplate": "Payoff ≈ %{x:.3f}<br>Probability: %{y:.2f}%<extra></extra>",
            }
        )
    axis = {"gridcolor": "#202a35", "zeroline": False, "automargin": True}
    return figure(
        data,
        "",
        "Probability (%)",
        xaxis={**axis, "domain": [0, 0.19]},
        yaxis={**axis, "range": [0, 100], "title": {"text": "Probability (%)"}},
        xaxis2={
            **axis,
            "domain": [0.34, 1],
            "anchor": "y2",
            "title": {"text": "Discounted payoff (currency units)"},
        },
        yaxis2={**axis, "anchor": "x2"},
        annotations=[
            {
                "xref": "paper",
                "yref": "paper",
                "x": x,
                "y": 1.12,
                "text": text,
                "showarrow": False,
                "font": {"size": 10},
            }
            for x, text in [(0.05, "Point mass at zero"), (0.8, "Positive payoffs")]
        ],
    )


def convergence_figure(curve, estimate):
    x = curve["sample_count"].tolist()
    data = [
        {
            "type": "scatter",
            "x": x,
            "y": curve["ci_high"].tolist(),
            "line": {"width": 0},
            "hoverinfo": "skip",
        },
        {
            "type": "scatter",
            "x": x,
            "y": curve["ci_low"].tolist(),
            "fill": "tonexty",
            "fillcolor": "rgba(194,237,131,.13)",
            "line": {"width": 0},
            "hoverinfo": "skip",
        },
        {
            "type": "scatter",
            "x": x,
            "y": curve["price"].tolist(),
            "line": {"width": 2, "color": COLORS[estimate.method]},
            "hovertemplate": "Budget used: %{x:,}<br>Estimate: %{y:.5f}<extra></extra>",
        },
    ]
    fig = figure(data, "Payoff evaluations (pilot included)", "Option price (currency units)", 320)
    fig["layout"]["xaxis"]["type"] = "log" if max(x) > 0 else "linear"
    if estimate.benchmark_price is not None:
        ref = estimate.benchmark_price
        fig["layout"]["shapes"] = [
            {
                "type": "line",
                "xref": "paper",
                "x0": 0,
                "x1": 1,
                "y0": ref,
                "y1": ref,
                "line": {"dash": "dash", "color": "#d6b979"},
            }
        ]
        fig["layout"]["annotations"] = [
            {
                "xref": "paper",
                "x": 1,
                "y": ref,
                "text": f"Black–Scholes {ref:.5f}",
                "showarrow": False,
                "xanchor": "right",
                "yanchor": "bottom",
            }
        ]
    return fig


def csv_bytes(rows):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


def browser_run(config_json):
    started = datetime.now(UTC).isoformat()
    config = json.loads(config_json)
    if not isinstance(config, dict):
        raise ValueError("configuration must be an object")
    o = Option(**config.get("option", {}))
    n, seed = config.get("samples", 100_000), config.get("seed", 42)
    validate_budget(n, seed)
    if n > MAX_BROWSER_SAMPLES:
        raise ValueError(
            "public browser demo is limited to 200,000 payoff evaluations per estimator"
        )
    product = config.get("product", "European")
    if product not in {"European", "Arithmetic Asian"}:
        raise ValueError("choose European or Arithmetic Asian")
    methods = METHODS if product == "European" else ("ordinary", "control")
    method = config.get("method", "control")
    if method not in methods:
        raise ValueError("estimator is not supported for this contract")
    normalized = {
        "product": product,
        "option": asdict(o),
        "samples": n,
        "seed": seed,
        "method": method,
    }
    if product == "Arithmetic Asian":
        dates = validate_dates(o, config.get("observation_dates", []))
        normalized["observation_dates"] = dates.tolist()
        sims = {m: simulate_asian(o, dates, n, seed, m) for m in methods}
        control_ref = geometric_price(o, dates)
    else:
        sims = {m: simulate(o, n, seed, m) for m in methods}
        control_ref = None
    curves = {m: convergence_data(s) for m, s in sims.items()}
    t, v = paths(o, np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(99,))))
    result = {
        "run_id": str(uuid.uuid4()),
        "config": normalized,
        "estimates": {m: s.estimate.to_dict() for m, s in sims.items()},
        "control_reference": control_ref,
        "figures": {
            "paths": visual_paths(t, v),
            "methods": {
                m: {
                    "payoffs": payoff_figure(s.payoffs),
                    "convergence": convergence_figure(curves[m], s.estimate),
                }
                for m, s in sims.items()
            },
        },
        "runtime": {
            "execution": "browser-web-worker",
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            **RUNTIME_METADATA,
        },
    }
    files = {
        "configuration.json": canonical(normalized).encode(),
        "estimates.csv": csv_bytes(list(result["estimates"].values())),
        "result.json": canonical(result).encode(),
    }
    buffer = io.BytesIO()
    np.savez_compressed(
        buffer, **{f"{m}_{k}": getattr(s, k) for m, s in sims.items() for k in ["units", "payoffs"]}
    )
    files["simulation.npz"] = buffer.getvalue()
    buffer = io.BytesIO()
    np.savez_compressed(buffer, times=t, values=v)
    files["visual_paths.npz"] = buffer.getvalue()
    curve_rows = [
        {"method": m, **{k: float(a[i]) for k, a in c.items()}}
        for m, c in curves.items()
        for i in range(len(c["price"]))
    ]
    files["convergence_points.csv"] = csv_bytes(curve_rows)
    files["README.txt"] = (
        b"Browser-computed model prices. Raw independent units/payoffs are in simulation.npz. "
        b"Runtime and source hashes are recorded. Native Python research outputs use their "
        b"own locked versions; browser runtimes can differ. Figures are saved in result.json. "
    )
    artifacts = [
        {"name": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        for name, data in files.items()
    ]
    manifest = {
        "schema_version": "1.1",
        "run_id": result["run_id"],
        "status": "succeeded",
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "config": normalized,
        "config_sha256": hashlib.sha256(canonical(normalized).encode()).hexdigest(),
        "seed": seed,
        "runtime": result["runtime"],
        "dataset_ids": [],
        "artifacts": artifacts,
    }
    files["manifest.json"] = canonical(manifest).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    result["archive_base64"] = base64.b64encode(buffer.getvalue()).decode()
    return canonical(result)
