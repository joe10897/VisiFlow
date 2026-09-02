import os
import sys
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from visiflow import VisiPlaywrightPage, VisiFlowDetector

class TestVisiFlowSpatialLocators(unittest.TestCase):
    def setUp(self):
        self.test_html_path = Path(__file__).resolve().parent / "index.html"
        self.test_url = self.test_html_path.as_uri()

    def test_spatial_relative_clicks(self):
        print("\n=== Running Spatial Relative Locators Test ===")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()
            
            print(f"Navigating to test page: {self.test_url}")
            page.goto(self.test_url)
            
            # Use detector with ONNX/OpenCV heuristics
            visipage = VisiPlaywrightPage(page)
            
            # 1. Click 'Delete' right of 'Alice Smith'
            print("Clicking 'Delete' right of 'Alice Smith'...")
            visipage.visual_click("Delete", right_of="Alice Smith")
            self.assertTrue(visipage.visual_assert_visible("Deleted user Alice Smith!"))
            print("[PASS] Verified: 'Delete' right of 'Alice Smith' clicked correctly.")
            
            # Wait for alert to fade
            page.wait_for_timeout(3200)
            
            # 2. Click 'Edit' right of 'Bob Jones'
            print("Clicking 'Edit' right of 'Bob Jones'...")
            visipage.visual_click("Edit", right_of="Bob Jones")
            self.assertTrue(visipage.visual_assert_visible("Editing user Bob Jones!"))
            print("[PASS] Verified: 'Edit' right of 'Bob Jones' clicked correctly.")
            
            # Wait for alert to fade
            page.wait_for_timeout(3200)
            
            # 3. Click 'Delete' right of 'Bob Jones' (second row delete)
            print("Clicking 'Delete' right of 'Bob Jones'...")
            visipage.visual_click("Delete", right_of="Bob Jones")
            self.assertTrue(visipage.visual_assert_visible("Deleted user Bob Jones!"))
            print("[PASS] Verified: 'Delete' right of 'Bob Jones' clicked correctly.")
            
            browser.close()

if __name__ == "__main__":
    unittest.main()
