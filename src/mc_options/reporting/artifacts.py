"""Immutable per-run folders with configuration, environment and artifact hashes."""

import hashlib
import json
import os
import platform
import subprocess
import uuid
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def now():
    return datetime.now(UTC).isoformat()


def provenance(config):
    git = {"git_commit": None, "dirty": None, "git_note": None}
    try:
        git["git_commit"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        git["dirty"] = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
    except (subprocess.SubprocessError, OSError) as exc:
        git["git_note"] = (
            f"Git unavailable ({type(exc).__name__}); source tree hash recorded instead."
        )
    source_files = sorted(
        p
        for base in ["src", "app", "configs"]
        for p in (ROOT / base).rglob("*")
        if p.is_file() and "__pycache__" not in str(p)
    )
    source_hash = sha(
        b"".join(str(p.relative_to(ROOT)).encode() + p.read_bytes() for p in source_files)
    )
    lock = ROOT / "uv.lock"
    frontend_lock = ROOT / "package-lock.json"
    return {
        "schema_version": "1.0",
        "run_id": str(uuid.uuid4()),
        "project": "monte-carlo-options",
        "started_at": now(),
        "finished_at": None,
        "status": "running",
        "config": config,
        "config_sha256": sha(canonical(config).encode()),
        "seed": config.get("seed"),
        "lock_sha256": sha(lock.read_bytes()) if lock.exists() else None,
        "source_sha256": source_hash,
        "frontend_lock_sha256": (
            sha(frontend_lock.read_bytes()) if frontend_lock.exists() else None
        ),
        "dataset_ids": [],
        "dataset_hashes": [],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "logical_cpus": os.cpu_count(),
            "dependencies": {
                p: version(p) for p in ["numpy", "scipy", "pandas", "pyarrow", "plotly"]
            },
            "timing_note": (
                "perf_counter wall time; single process; no CPU affinity; warmup "
                "excluded; hardware load uncontrolled"
            ),
        },
        **git,
    }


class Run:
    def __init__(self, config, output="reports/experiments"):
        self.manifest = provenance(config)
        base = Path(output).resolve()
        if not base.is_relative_to(ROOT):
            raise ValueError("output must be inside project root")
        self.folder = base / self.manifest["run_id"]
        self.folder.mkdir(parents=True, exist_ok=False)
        self.manifest["artifacts"] = []
        self._write()

    def _write(self):
        (self.folder / "manifest.json").write_text(
            json.dumps(self.manifest, indent=2, allow_nan=False)
        )

    def record(self, name, kind):
        p = self.folder / name
        self.manifest["artifacts"].append(
            {
                "artifact_id": str(uuid.uuid4()),
                "kind": kind,
                "file_uri": str(p.relative_to(ROOT)),
                "sha256": sha(p.read_bytes()),
                "schema_version": "1.0",
            }
        )

    def json(self, name, data):
        (self.folder / name).write_text(json.dumps(data, indent=2, allow_nan=False))
        self.record(name, "json")

    def table(self, name, frame):
        frame.to_parquet(self.folder / f"{name}.parquet", index=False)
        frame.to_csv(self.folder / f"{name}.csv", index=False)
        self.record(f"{name}.parquet", "parquet")
        self.record(f"{name}.csv", "csv")

    def figure(self, name, fig):
        fig.write_html(self.folder / f"{name}.html", include_plotlyjs=True)
        self.record(f"{name}.html", "interactive_figure")

    def finish(self, failure=None):
        self.manifest.update(
            status="failed" if failure else "succeeded",
            finished_at=now(),
            failure_reason=str(failure) if failure else None,
        )
        self._write()


def save_pricing(
    config, sims, curves, figures, output="reports/experiments", visual_paths=None, extra_json=None
):
    run = Run(config, output)
    try:
        run.json("configuration.json", config)
        run.table("pricing_cases", pd.DataFrame([{"case_id": "selected", **config["option"]}]))
        estimates = pd.DataFrame([s.estimate.to_dict() for s in sims.values()])
        estimates.insert(0, "run_id", run.manifest["run_id"])
        estimates.insert(1, "case_id", "selected")
        run.table("estimates", estimates)
        data = pd.concat(
            [
                c.assign(method=m, run_id=run.manifest["run_id"], case_id="selected")
                for m, c in curves.items()
            ]
        )
        run.table("convergence_points", data)
        for name, fig in figures.items():
            run.figure(name, fig)
        np.savez_compressed(
            run.folder / "simulation.npz",
            **{f"{m}_{k}": getattr(s, k) for m, s in sims.items() for k in ["units", "payoffs"]},
        )
        run.record("simulation.npz", "numpy_arrays")
        if visual_paths is not None:
            np.savez_compressed(
                run.folder / "visual_paths.npz", times=visual_paths[0], values=visual_paths[1]
            )
            run.record("visual_paths.npz", "numpy_arrays")
        for name, payload in (extra_json or {}).items():
            run.json(name, payload)
        run.finish()
    except Exception as exc:
        run.finish(exc)
        raise
    return run.folder
