"""Opt-in full custom-app browser workflow. Start quant-options-app before running."""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
    failures = []
    posts = []
    page.on("pageerror", lambda error: failures.append(str(error)))
    page.on(
        "request", lambda request: posts.append(request.url) if request.method == "POST" else None
    )
    page.goto("http://127.0.0.1:8501")
    expect(page.get_by_role("heading", name="The pricing lab.")).to_be_visible()
    page.get_by_role("button", name="Reset ↺").click()
    page.locator("#samples").fill("10000")
    page.get_by_role("button", name="Run simulation").click()
    expect(page.locator("#result-state")).to_contain_text("SEED 42", timeout=60000)
    expect(page.locator("#convergence-chart .main-svg").first).to_be_visible()
    expect(page.locator("#comparison-body tr")).to_have_count(3)
    run_text = page.locator("#run-provenance").inner_text()
    before = len(posts)
    page.locator("#convergence-chart").hover(position={"x": 300, "y": 140})
    page.get_by_role("button", name="Antithetic", exact=True).click()
    expect(page.locator("#result-state")).to_contain_text("ANTITHETIC")
    page.get_by_role("button", name="Control variate", exact=True).click()
    expect(page.locator("#result-state")).to_contain_text("CONTROL VARIATE")
    assert page.locator("#run-provenance").inner_text() == run_text
    assert len(posts) == before, "Chart hover and estimator switches must never resample"
    # Editing does not replace existing results until explicit Run.
    page.locator("#spot").fill("110")
    expect(page.locator("#stale-note")).to_be_visible()
    assert page.locator("#run-provenance").inner_text() == run_text
    page.get_by_role("button", name="Reset ↺").click()
    page.get_by_role("button", name="Budget details").click()
    expect(page.get_by_role("dialog")).to_be_visible()
    expect(page.locator("#budget-details")).to_contain_text("pilot")
    page.get_by_role("button", name="Close budget details").click()
    for name, ext in [
        ("Export CSV ↗", ".csv"),
        ("Config JSON ↓", ".json"),
        ("Download run ↓", ".zip"),
    ]:
        with page.expect_download() as item:
            page.get_by_role("button", name=name).click()
        download = item.value
        assert download.suggested_filename.endswith(ext)
        target = ROOT / "reports/experiments" / download.suggested_filename
        download.save_as(target)
        assert target.stat().st_size > 10
        if ext == ".json":
            assert json.loads(target.read_text())["samples"] == 10000
    # Reopen a saved run on refresh without a POST.
    before = len(posts)
    page.reload()
    expect(page.locator("#run-provenance")).to_have_text(run_text, timeout=30000)
    assert len(posts) == before
    page.get_by_role("button", name="Research").click()
    expect(page.locator("#research-count")).to_contain_text("21,600", timeout=30000)
    expect(page.locator("#research-body tr")).to_have_count(9)
    expect(page.locator("#research-rmse .main-svg").first).to_be_visible()
    page.locator("#research-case").select_option("put_K120_v0.4_T2.0")
    expect(page.locator("#research-body tr")).to_have_count(9)
    page.get_by_role("button", name="Methodology").click()
    expect(page.get_by_role("heading", name="Know your assumptions.")).to_be_visible()
    page.get_by_role("button", name="Pricing lab", exact=False).click()
    # Reject invalid model assumptions while retaining the last successful run.
    page.locator("#volatility").fill("300")
    page.locator("#maturity").fill("50")
    page.get_by_role("button", name="Run simulation").click()
    expect(page.locator("#form-error")).to_contain_text("moment limit", timeout=30000)
    assert page.locator("#run-provenance").inner_text() == run_text
    page.get_by_role("button", name="Reset ↺").click()
    # Asian flow: numerical result, no mislabeled arithmetic analytical price.
    page.locator("#product").select_option("Arithmetic Asian")
    page.locator("#dates").fill("0.25,0.5,0.75,1")
    page.locator("#samples").fill("10000")
    page.get_by_role("button", name="Run simulation").click()
    expect(page.locator("#reference-label")).to_contain_text("Geometric control", timeout=60000)
    expect(page.locator("#comparison-body tr")).to_have_count(2)
    expect(page.locator('[data-method="antithetic"]')).to_be_disabled()
    expect(page.locator("#warning")).to_contain_text("no analytical reference")
    # Restore the European default for the primary screenshot and user handoff.
    page.get_by_role("button", name="Reset ↺").click()
    page.get_by_role("button", name="Run simulation").click()
    expect(page.locator("#reference-label")).to_contain_text("Black–Scholes", timeout=60000)
    expect(page.locator("#comparison-body tr")).to_have_count(3)
    page.locator("#toast").wait_for(state="hidden", timeout=10000)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(300)
    page.screenshot(path=str(ROOT / "reports/figures/interface.png"), full_page=True)
    for width, name in [(768, "interface-tablet.png"), (390, "interface-mobile.png")]:
        page.set_viewport_size({"width": width, "height": 1000})
        page.wait_for_timeout(500)
        page.evaluate("window.scrollTo(0, 0)")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
            "Page must not overflow"
        )
        page.screenshot(path=str(ROOT / "reports/figures" / name), full_page=True)
    assert not failures, failures
    browser.close()
print("Custom app browser checks passed: seeded pricing, no resampling on hover/switch,")
print("retention, downloads, research, invalid inputs, Asian extension, desktop/tablet/mobile.")
