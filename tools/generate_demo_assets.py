import os
import sys
import cv2
import numpy as np
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from visiflow.core import VisiFlowDetector

def generate_demo_banner():
    """
    Generate an eye-catching visual demonstration banner image highlighting
    YOLO element detection boxes, EasyOCR text bounding boxes, and click crosshairs.
    """
    test_page = Path(__file__).resolve().parent.parent / "tests" / "index.html"
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    assets_dir.mkdir(exist_ok=True)

    print("Generating high-resolution VisiFlow demonstration banner...")

    # We use Playwright to capture a crisp screenshot of tests/index.html
    from playwright.sync_api import sync_playwright
    screenshot_path = assets_dir / "raw_screenshot.png"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(test_page.as_uri())
        page.screenshot(path=str(screenshot_path))
        browser.close()

    img = cv2.imread(str(screenshot_path))
    if img is None:
        print("Error reading screenshot.")
        return

    # Run detection
    detector = VisiFlowDetector(use_yolo=False) # Uses OpenCV contour fallback for deterministic demo boxes
    elements = detector.detect_elements(str(screenshot_path))
    ocr_items = detector.run_ocr(str(screenshot_path))

    # 1. Draw UI element bounding boxes (Neon Cyan)
    for elem in elements:
        x1, y1, x2, y2 = elem["box"]
        # Draw translucent filled box
        overlay = img.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (248, 189, 56), -1) # BGR: Cyan #38bdf8
        cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)
        cv2.rectangle(img, (x1, y1), (x2, y2), (248, 189, 56), 2)

    # 2. Draw OCR bounding boxes (Emerald Green)
    for item in ocr_items:
        x1, y1, x2, y2 = item["box"]
        cv2.rectangle(img, (x1, y1), (x2, y2), (153, 211, 52), 1) # BGR: Emerald #34d399

    # 3. Simulate target match crosshair on "Submit" button
    coords = detector.find_element_by_text(str(screenshot_path), "Submit")
    if coords:
        cx, cy = coords
        # Glowing magenta circle
        cv2.circle(img, (cx, cy), 22, (94, 63, 244), 3) # BGR: Magenta #f43f5e
        cv2.circle(img, (cx, cy), 6, (255, 255, 255), -1)

    banner_output = assets_dir / "visiflow_demo_banner.png"
    cv2.imwrite(str(banner_output), img)
    print(f"Successfully generated demo banner at: {banner_output}")

if __name__ == "__main__":
    generate_demo_banner()
