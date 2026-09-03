"""
VisiFlow Quickstart Example: Playwright Integration
---------------------------------------------------
Shows how to use VisiFlow to visually interact with a web page
without writing any CSS selectors or XPaths.
"""

from playwright.sync_api import sync_playwright
from visiflow import VisiPlaywrightPage, global_reporter

def run_quickstart():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        
        # 1. Navigate to target URL
        page.goto("https://github.com/login")

        # 2. Wrap Playwright Page with VisiPlaywrightPage
        visipage = VisiPlaywrightPage(page)

        # 3. Visually fill form fields
        visipage.visual_fill("Username or email address", "demo_user@example.com")
        visipage.visual_fill("Password", "SuperSecretPass123")

        # 4. Visually click button
        visipage.visual_click("Sign in")

        # 5. Visually assert presence of warning or message
        # visipage.visual_assert_visible("Incorrect username or password.")

        # 6. Generate Self-Healing HTML Test Report
        global_reporter.generate_html_report("quickstart_report.html")

        browser.close()

if __name__ == "__main__":
    run_quickstart()
