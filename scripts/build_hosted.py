"""Build a static public demo that runs the original Python engine in a web worker."""

import hashlib
import json
import shutil
import tomllib
import zipfile

from plotly.offline import get_plotlyjs

from mc_options.reporting.artifacts import ROOT
from mc_options.web import execute, research_payload

DIST = ROOT / "hosted/dist"
DIST.mkdir(parents=True, exist_ok=True)
for folder in ["static", "assets", "data", "docs"]:
    (DIST / folder).mkdir(exist_ok=True)
for file in (ROOT / "app/web/static").glob("*.js"):
    shutil.copy2(file, DIST / "static" / file.name)
shutil.copy2(ROOT / "app/web/pricing-worker.mjs", DIST / "static/pricing-worker.mjs")
shutil.copy2(ROOT / "app/web/styles.css", DIST / "static/styles.css")
(DIST / "assets/plotly.min.js").write_text(get_plotlyjs())
html = (ROOT / "app/web/index.html").read_text()
html = html.replace('<html lang="en">', '<html lang="en" data-runtime="browser">')
html = html.replace("Local Python engine", "Python in your browser")
html = html.replace("RUNNING LOCALLY", "PUBLIC LIVE DEMO")
html = html.replace("All computation stays local", "All computation stays in your browser")
html = html.replace("ALL COMPUTATION STAYS LOCAL", "CALCULATED IN YOUR BROWSER")
html = html.replace(
    'id="samples" name="samples" type="number" min="100" max="2000000"',
    'id="samples" name="samples" type="number" min="100" max="200000"',
)
html = html.replace('data-budget="1000000">1m', 'data-budget="200000">200k')
html = html.replace(
    "Exact terminal sampling.<br>Pilot draws included in your budget.",
    "Up to 200,000 payoffs per estimator.<br>First run loads the calculation engine.",
)
html = html.replace('href="/docs/methodology"', 'href="/docs/METHODOLOGY.md"')
html = html.replace('href="/docs/results"', 'href="/docs/RESULTS.md"')
(DIST / "index.html").write_text(html)
for name in ["METHODOLOGY.md", "RESULTS.md"]:
    shutil.copy2(ROOT / "docs" / name, DIST / "docs" / name)
shutil.copy2(ROOT / "LICENSE", DIST / "LICENSE.txt")
shutil.copy2(ROOT / "LICENSES/plotly.txt", DIST / "assets/plotly-LICENSE.txt")

modules = [
    "__init__.py",
    "config.py",
    "browser.py",
    "models/__init__.py",
    "models/black_scholes.py",
    "models/controls.py",
    "models/estimators.py",
    "models/payoffs.py",
    "models/sampling.py",
    "models/asian.py",
    "evaluation/__init__.py",
    "evaluation/convergence.py",
]
source_bundle = DIST / "assets/python-engine.zip"
with zipfile.ZipFile(source_bundle, "w", zipfile.ZIP_DEFLATED) as archive:
    for name in modules:
        archive.write(ROOT / "src/mc_options" / name, f"mc_options/{name}")
meta = {
    "engine_source_sha256": hashlib.sha256(source_bundle.read_bytes()).hexdigest(),
    "native_lock_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
    "frontend_lock_sha256": hashlib.sha256((ROOT / "package-lock.json").read_bytes()).hexdigest(),
    "native_project_version": tomllib.loads((ROOT / "pyproject.toml").read_text())["project"][
        "version"
    ],
    "browser_budget_limit": 200000,
    "persistence": "per-browser IndexedDB; most recent five runs",
}
(DIST / "data/runtime.json").write_text(json.dumps(meta, indent=2))

initial = research_payload()
bundle = {
    "default_case": initial["selected"],
    "payloads": {case: research_payload(case) for case in initial["cases"]},
}
(DIST / "data/research.json").write_text(json.dumps(bundle, allow_nan=False))
example = execute(
    {"product": "European", "option": {}, "samples": 100000, "seed": 42, "method": "control"}
)
(DIST / "data/example.json").write_text(json.dumps(example, allow_nan=False))
example_folder = ROOT / "reports/experiments" / example["run_id"]
with zipfile.ZipFile(DIST / "data/example.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for file in sorted(example_folder.iterdir()):
        if file.is_file():
            archive.write(file, file.name)
print(f"Built public demo: {len(list(DIST.rglob('*')))} entries; example {example['run_id']}")
