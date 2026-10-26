"""Opt-in browser-runtime and visitor-storage integration check."""

import hashlib
import json
import os
import zipfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from mc_options.config import Option
from mc_options.models.estimators import simulate

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 1600, "height": 1200})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(os.environ.get("APP_URL", "http://127.0.0.1:8502"))
    expect(page.locator("#run-provenance")).to_contain_text("RUN", timeout=30000)
    page.locator("#samples").fill("1000")
    page.get_by_role("button", name="Run simulation").click()
    expect(page.locator("#run-provenance")).to_contain_text("1,000 total budget", timeout=180000)
    expect(page.locator("#stale-note")).to_be_hidden()
    run_text = page.locator("#run-provenance").inner_text()
    with page.expect_download() as item:
        page.get_by_role("button", name="Download run ↓").click()
    archive_path = ROOT / "reports/experiments/browser-check.zip"
    item.value.save_as(archive_path)
    with zipfile.ZipFile(archive_path) as z:
        result = json.loads(z.read("result.json"))
        manifest = json.loads(z.read("manifest.json"))
        for artifact in manifest["artifacts"]:
            assert hashlib.sha256(z.read(artifact["name"])).hexdigest() == artifact["sha256"]
        option = Option(**result["config"]["option"])
        for method, estimate in result["estimates"].items():
            native = simulate(option, 1000, 42, method).estimate
            assert abs(native.price - estimate["price"]) < 1e-10
    page.reload()
    expect(page.locator("#run-provenance")).to_have_text(run_text, timeout=30000)
    page.get_by_role("button", name="Antithetic", exact=True).click()
    assert page.locator("#run-provenance").inner_text() == run_text
    page.get_by_role("button", name="Research", exact=False).click()
    expect(page.locator("#research-count")).to_contain_text("21,600", timeout=30000)
    page.get_by_role("button", name="Pricing lab", exact=False).click()
    page.locator("#product").select_option("Arithmetic Asian")
    page.locator("#dates").fill("0.25,0.5,0.75,1")
    page.get_by_role("button", name="Run simulation").click()
    expect(page.locator("#reference-label")).to_contain_text("Geometric control", timeout=60000)
    expect(page.locator("#comparison-body tr")).to_have_count(2)
    page.get_by_role("button", name="Reset ↺").click()
    page.locator("#samples").fill("10000")
    page.get_by_role("button", name="Run simulation").click()
    expect(page.locator("#run-provenance")).to_contain_text("10,000 total budget", timeout=60000)
    page.screenshot(path=str(ROOT / "reports/figures/interface.png"), full_page=True)
    other = browser.new_context().new_page()
    other.goto(os.environ.get("APP_URL", "http://127.0.0.1:8502"))
    expect(other.locator("#run-provenance")).to_contain_text("100,000 total budget", timeout=30000)
    assert not errors, errors
    browser.close()
print("PASS: Python/WASM agreement, ZIP hashes, reload, research, Asian and isolation.")
