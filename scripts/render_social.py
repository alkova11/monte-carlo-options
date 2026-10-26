"""Render local, code-authored publication graphics from the actual app screenshot."""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=1)
    page.goto((ROOT / "docs/social/launch-card.html").as_uri())
    page.locator(".shot img").wait_for(state="visible")
    assert page.locator(".shot img").evaluate("img => img.complete && img.naturalWidth > 0")
    page.screenshot(path=str(ROOT / "reports/figures/linkedin-launch.png"))
    page.set_viewport_size({"width": 1600, "height": 1200})
    page.goto((ROOT / "docs/social/app-preview.html").as_uri())
    page.locator("img").wait_for(state="visible")
    assert page.locator("img").evaluate("img => img.complete && img.naturalWidth > 0")
    page.screenshot(path=str(ROOT / "reports/figures/github-preview.png"))
    browser.close()
print("Rendered LinkedIn launch card and actual app preview from local files.")
