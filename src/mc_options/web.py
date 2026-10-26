"""Loopback-only HTTP application for the custom options lab interface.

The browser presents existing package results; no numerical formulas live in JS.
"""

import argparse
import io
import json
import logging
import zipfile
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import BoundedSemaphore
from urllib.parse import unquote, urlparse
from uuid import UUID

import numpy as np
import pandas as pd
import plotly.io as pio
from plotly.offline import get_plotlyjs

from mc_options.config import Option, validate_budget
from mc_options.evaluation.convergence import convergence
from mc_options.models.asian import geometric_price, simulate_asian, validate_dates
from mc_options.models.estimators import METHODS, simulate
from mc_options.models.sampling import paths
from mc_options.reporting.artifacts import ROOT, save_pricing
from mc_options.reporting.charts import (
    convergence_chart,
    path_chart,
    payoff_chart,
    research_charts,
)

WEB = ROOT / "app/web"
RUNS = ROOT / "reports/experiments"
BUSY = BoundedSemaphore(1)
LOGGER = logging.getLogger("mc_options.web")


def figure_json(fig, height=290):
    """Use local Plotly's matching JS bundle and serialisation (including typed arrays)."""
    fig.update_layout(
        title=None,
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", size=11, color="#8795a8"),
        margin=dict(l=52, r=22, t=32, b=48),
        legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
    )
    fig.update_xaxes(gridcolor="#202a35", automargin=True)
    fig.update_yaxes(gridcolor="#202a35", automargin=True)
    return json.loads(pio.to_json(fig))


def execute(config, output="reports/experiments"):
    """Validate a request, call the existing estimators, and persist a complete run."""
    if not isinstance(config, dict):
        raise ValueError("configuration must be a JSON object")
    option_data = config.get("option", {})
    if not isinstance(option_data, dict):
        raise ValueError("option must be a JSON object")
    o = Option(**option_data)
    n, seed = config.get("samples", 100_000), config.get("seed", 42)
    validate_budget(n, seed)
    product = config.get("product", "European")
    if product not in {"European", "Arithmetic Asian"}:
        raise ValueError("choose European or Arithmetic Asian")
    method = config.get("method", "control")
    methods = METHODS if product == "European" else ("ordinary", "control")
    if method not in methods:
        raise ValueError("selected estimator is not supported for this contract")
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
        control_reference = geometric_price(o, dates)
    else:
        sims = {m: simulate(o, n, seed, m) for m in methods}
        control_reference = None
    curves = {m: convergence(s) for m, s in sims.items()}
    t, v = paths(o, np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(99,))))
    visual = path_chart(t, v)
    method_figures = {}
    saved = {"paths": visual}
    for m, s in sims.items():
        payoff = payoff_chart(s.payoffs)
        trace = convergence_chart(curves[m], s.estimate.benchmark_price, m)
        trace.update_layout(showlegend=False)
        trace.data[-1].line.color = {
            "ordinary": "#62a8fa",
            "antithetic": "#b89aff",
            "control": "#c2ed83",
        }[m]
        payoff.update_annotations(font=dict(size=10, color="#8795a8"))
        method_figures[m] = {
            "payoffs": figure_json(payoff),
            "convergence": figure_json(trace, 320),
        }
        if m == method:
            saved.update(payoffs=payoff, convergence=trace)
    payload = {
        "config": normalized,
        "estimates": {m: s.estimate.to_dict() for m, s in sims.items()},
        "control_reference": control_reference,
        "figures": {"paths": figure_json(visual), "methods": method_figures},
    }
    folder = save_pricing(
        normalized,
        sims,
        curves,
        saved,
        output,
        visual_paths=(t, v),
        extra_json={"web_result.json": payload},
    )
    return {"run_id": folder.name, **payload}


def research_payload(case=None):
    published = ROOT / "reports/published/benchmark"
    if not (published / "summary.parquet").exists():
        return {"available": False}
    summary = pd.read_parquet(published / "summary.parquet")
    manifest = json.loads((published / "manifest.json").read_text())
    cases = sorted(summary.case_id.unique().tolist())
    selected = case or "call_K100_v0.15_T2.0"
    if selected not in cases:
        raise ValueError("unknown research case")
    focused = summary[summary.case_id == selected]
    overview = summary.groupby("method", as_index=False).agg(
        variance_reduction=("variance_reduction", "median"),
        coverage=("coverage", "mean"),
    )
    figures = {}
    for name, fig in research_charts(focused).items():
        fig.update_layout(showlegend=True)
        for trace in fig.data:
            trace.name = trace.legendgroup.title()
        figures[name] = figure_json(fig, 340)
    return {
        "available": True,
        "run_id": manifest["run_id"],
        "cases": cases,
        "selected": selected,
        "replicates": manifest["config"]["replicates"],
        "case_count": len(cases),
        "estimate_count": len(cases)
        * len(manifest["config"]["sample_counts"])
        * manifest["config"]["replicates"]
        * 3,
        "overview": json.loads(overview.to_json(orient="records")),
        "rows": json.loads(focused.to_json(orient="records")),
        "figures": figures,
    }


def run_folder(identifier):
    try:
        valid = str(UUID(identifier))
    except (ValueError, AttributeError) as exc:
        raise ValueError("invalid run identifier") from exc
    folder = RUNS / valid
    if not folder.is_dir():
        raise FileNotFoundError("run not found")
    return folder


class Handler(BaseHTTPRequestHandler):
    server_version = "OptionsLab/1.0"

    def send(self, body, mime="application/json", status=200, filename=None):
        if isinstance(body, dict):
            body = json.dumps(body, allow_nan=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def local_request(self):
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        origin = self.headers.get("Origin")
        return self.headers.get("Host") in allowed and (
            origin is None or origin in {f"http://{h}" for h in allowed}
        )

    def do_GET(self):
        if not self.local_request():
            return self.send({"error": "local requests only"}, status=403)
        route = unquote(urlparse(self.path).path)
        try:
            static = {
                "/": (WEB / "index.html", "text/html; charset=utf-8"),
                "/static/styles.css": (WEB / "styles.css", "text/css; charset=utf-8"),
                "/static/app.js": (WEB / "static/app.js", "text/javascript; charset=utf-8"),
            }
            if route in static:
                file, mime = static[route]
                return self.send(file.read_bytes(), mime)
            if route == "/assets/plotly.min.js":
                return self.send(get_plotlyjs(), "text/javascript; charset=utf-8")
            if route == "/api/health":
                return self.send({"status": "ok", "interface": "custom", "local_only": True})
            if route == "/api/latest":
                files = sorted(
                    RUNS.glob("*/web_result.json"), key=lambda p: p.stat().st_mtime, reverse=True
                )
                for file in files:
                    manifest = json.loads((file.parent / "manifest.json").read_text())
                    if manifest.get("status") == "succeeded":
                        return self.send(
                            {"run_id": file.parent.name, **json.loads(file.read_text())}
                        )
                raise FileNotFoundError("no saved app run yet")
            if route == "/api/research":
                from urllib.parse import parse_qs

                case = parse_qs(urlparse(self.path).query).get("case", [None])[0]
                return self.send(research_payload(case))
            if route in {"/docs/methodology", "/docs/results"}:
                name = "METHODOLOGY.md" if route.endswith("methodology") else "RESULTS.md"
                return self.send((ROOT / "docs" / name).read_bytes(), "text/plain; charset=utf-8")
            if route.startswith("/api/runs/"):
                parts = route.split("/")
                if len(parts) != 5:
                    raise FileNotFoundError("unknown run resource")
                folder = run_folder(parts[3])
                resource = parts[4]
                if resource == "result":
                    return self.send(
                        {
                            "run_id": folder.name,
                            **json.loads((folder / "web_result.json").read_text()),
                        }
                    )
                files = {
                    "csv": ("estimates.csv", "text/csv"),
                    "config": ("configuration.json", "application/json"),
                }
                if resource in files:
                    name, mime = files[resource]
                    return self.send((folder / name).read_bytes(), mime, filename=name)
                if resource == "zip":
                    buffer = io.BytesIO()
                    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                        for file in sorted(folder.iterdir()):
                            if file.is_file():
                                archive.write(file, file.name)
                    return self.send(
                        buffer.getvalue(),
                        "application/zip",
                        filename=f"options-{folder.name[:8]}.zip",
                    )
            raise FileNotFoundError("resource not found")
        except (FileNotFoundError, ValueError) as exc:
            return self.send({"error": str(exc)}, status=404)

    def do_POST(self):
        if not self.local_request():
            return self.send({"error": "local requests only"}, status=403)
        if self.path != "/api/run":
            return self.send({"error": "resource not found"}, status=404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 32_768:
                return self.send({"error": "configuration must be 1–32768 bytes"}, status=413)
            config = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            return self.send({"error": "invalid JSON configuration"}, status=400)
        if not BUSY.acquire(blocking=False):
            return self.send(
                {"error": "a simulation is already running; try again shortly"}, status=429
            )
        try:
            return self.send(execute(config))
        except (ValueError, TypeError, KeyError) as exc:
            return self.send({"error": str(exc)}, status=400)
        except Exception:
            LOGGER.exception("simulation failed")
            return self.send(
                {"error": "simulation could not be saved; check local server logs"}, status=500
            )
        finally:
            BUSY.release()

    def log_message(self, message, *args):
        LOGGER.info(message, *args)


def make_server(port=8501):
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description="Run the custom options lab locally")
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    if not (WEB / "static/app.js").exists():
        parser.error("frontend bundle missing: run npm ci && npm run build")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        server = make_server(args.port)
    except OSError as exc:
        parser.error(str(exc))
    print(f"Options Lab is running locally: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
