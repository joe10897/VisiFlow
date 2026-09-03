"""
VisiFlow Spatial Locators Example
---------------------------------
Demonstrates how to interact with tables containing multiple identical buttons
(e.g., "Edit", "Delete") by anchoring with spatial relative locators.
"""

from pathlib import Path
from playwright.sync_api import sync_playwright
from visiflow import VisiPlaywrightPage, global_reporter

def run_spatial_example():
    # Point to the local test HTML fixture
    test_page = (Path(__file__).resolve().parent.parent / "tests" / "index.html").as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(test_page)

        visipage = VisiPlaywrightPage(page)

        # 1. Click "Delete" specifically in the table row of "Alice Smith"
        print("Clicking Delete for Alice Smith...")
        visipage.visual_click("Delete", right_of="Alice Smith")

        # 2. Click "Edit" specifically in the table row of "Bob Jones"
        print("Clicking Edit for Bob Jones...")
        visipage.visual_click("Edit", right_of="Bob Jones")

        # 3. Fill input field situated below a section title
        # visipage.visual_fill("Username", "admin_user", below="Developer Login")

        # 4. Generate report
        global_reporter.generate_html_report("spatial_example_report.html")

        browser.close()

if __name__ == "__main__":
    run_spatial_example()
