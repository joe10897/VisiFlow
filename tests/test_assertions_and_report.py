import os
import sys
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from visiflow import VisiPlaywrightPage, global_reporter

class TestVisiFlowAssertionsAndReport(unittest.TestCase):
    def setUp(self):
        self.test_html_path = Path(__file__).resolve().parent / "index.html"
        self.test_url = self.test_html_path.as_uri()

    def test_playwright_assertions_and_report(self):
        print("\n=== Running Playwright Assertions & HTML Report Test ===")
        
        with sync_playwright() as p:
            # 1. Launch Browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            page = context.new_page()
            
            print(f"Navigating to test page: {self.test_url}")
            page.goto(self.test_url)
            
            # 2. Wrap Page
            visipage = VisiPlaywrightPage(page)
            
            # 3. Test Visual Assertions
            print("Asserting 'VisiFlow Testing Ground' is visible...")
            self.assertTrue(visipage.visual_assert_visible("VisiFlow Testing Ground"))
            
            print("Asserting 'Logged in successfully!' is NOT visible initially...")
            self.assertTrue(visipage.visual_assert_not_visible("Logged in successfully!"))
            
            # 4. Perform Visual Actions (Will trigger step recording & self-healing log)
            print("Filling Username visually...")
            visipage.visual_fill("Username", "assertion_test_user")
            
            print("Filling Password visually...")
            visipage.visual_fill("Password", "assertion_pass_123")
            
            print("Clicking Submit visually...")
            visipage.visual_click("Submit")
            
            # 5. Assert Logged In Success Alert is now visible
            print("Asserting 'Logged in successfully!' is now visible...")
            self.assertTrue(visipage.visual_assert_visible("Logged in successfully!"))
            
            browser.close()

        # 6. Generate Self-Healing HTML Report
        report_output = Path(__file__).resolve().parent / "visiflow_report.html"
        global_reporter.generate_html_report(str(report_output))
        
        print(f"✅ Self-Healing HTML Report generated at: {report_output}")
        self.assertTrue(report_output.exists())
        self.assertGreater(report_output.stat().st_size, 1000)

if __name__ == "__main__":
    unittest.main()
