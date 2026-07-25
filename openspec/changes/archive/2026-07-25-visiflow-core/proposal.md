## Why

Traditional E2E testing frameworks (like Playwright and Selenium) are heavily reliant on fragile HTML DOM structures, including XPath, IDs, and complex CSS selectors. When front-end architectures change, or CSS frameworks are upgraded, these selectors frequently break, leading to high test-maintenance costs. VisiFlow aims to solve this by using computer vision (YOLO) and local OCR to identify and interact with page elements based on how they actually look to users. By running everything locally, VisiFlow provides an extremely fast, zero-dependency, cloud-free, and cost-effective visual automation testing plugin.

## What Changes

We will introduce a Python library `visiflow` that integrates with existing Playwright and Selenium test suites. Key changes include:
- A local UI object detection pipeline using YOLOv8/YOLO11 (or latest YOLO models) to identify interactive elements (buttons, text inputs, dropdowns, checkboxes) directly from browser screenshots in milliseconds.
- A semantic matching and text-anchoring layer utilizing a local OCR library (like EasyOCR) to associate text with detected element coordinates.
- An easy-to-use API wrapper for Playwright and Selenium that allows developers to write `page.visual_click("Login")` or `page.visual_fill("Search", "AI testing")` instead of DOM selectors.

## Capabilities

### New Capabilities

- `element-detection`: YOLO-based UI element object detection that outputs coordinates of page components (buttons, input boxes, checkboxes, etc.) from screenshots.
- `text-anchoring`: Local OCR text identification and semantic mapping, matching natural language queries (e.g., "Login", "Confirm") to the correct visual bounding boxes.
- `playwright-integration`: A wrapper/plugin for Playwright (Python) providing visual-driven APIs (`visual_click`, `visual_fill`, etc.).
- `selenium-integration`: A wrapper/plugin for Selenium (Python) providing equivalent visual-driven APIs.

## Impact

- **Dependencies**: Adds lightweight runtime dependencies: `ultralytics` (for YOLO), `easyocr` (for OCR), `playwright`, `selenium`, and `opencv-python`.
- **Performance**: Test runs will perform local inference (YOLO + OCR) on screenshots, introducing a slight overhead (~50-100ms per action) but completely eliminating DOM-lookup failures and cloud API costs.
