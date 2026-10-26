"""Validate a source ZIP in a clean local checkout, not the working environment tree."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
archive_path = ROOT / f"release/monte-carlo-options-v{version}-source.zip"
with tempfile.TemporaryDirectory(prefix="source-check-", dir=ROOT / "release") as tmp:
    extraction = Path(tmp)
    with zipfile.ZipFile(archive_path) as archive:
        for item in archive.infolist():
            if not (extraction / item.filename).resolve().is_relative_to(extraction):
                raise ValueError("unsafe source archive path")
        archive.extractall(extraction)
    checkout = extraction / f"monte-carlo-options-{version}"
    manifest = json.loads((checkout / "RELEASE_MANIFEST.json").read_text())
    for item in manifest["files"]:
        content = (checkout / item["path"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == item["sha256"]
    env = {**os.environ, "PYTHONPATH": str(checkout / "src")}
    probe = subprocess.run(
        [sys.executable, "-c", "from mc_options.reporting.artifacts import ROOT; print(ROOT)"],
        cwd=checkout,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    assert Path(probe.stdout.strip()) == checkout
    subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=checkout, env=env, check=True)
    subprocess.run(
        [sys.executable, "-m", "mc_options.cli", "price", "--config", "configs/european.json"],
        cwd=checkout,
        env=env,
        check=True,
    )
    assert not (checkout / "AGENTS.md").exists()
    assert not (checkout / ".venv").exists()
print("Clean extracted source: hashes, package-root resolution, tests and CLI price passed.")
