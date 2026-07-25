import os
import tempfile
import time
import cv2
from typing import Optional, Any
from .core import VisiFlowDetector, logger

class VisiPlaywrightPage:
    def __init__(self, page: Any, detector: Optional[VisiFlowDetector] = None):
        """
        Wrapper for Playwright Page to add visual action capabilities.
        
        :param page: The playwright Page object
        :param detector: An optional custom VisiFlowDetector instance
        """
        self.page = page
        self.detector = detector or VisiFlowDetector()

    def _resolve_coordinates(self, text_or_label: str) -> Optional[tuple]:
        """
        Take a screenshot, run visual detection, scale coordinates to page viewport, and return them.
        """
        # 1. Capture screen to a temporary file
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        
        try:
            self.page.screenshot(path=temp_path)
            
            # 2. Get image dimensions (physical pixels)
            img = cv2.imread(temp_path)
            if img is None:
                logger.error("Failed to read captured screenshot.")
                return None
            sh, sw = img.shape[:2]
            
            # 3. Get viewport size (logical browser pixels)
            viewport = self.page.viewport_size
            if not viewport:
                # Fallback to physical size if viewport is none (e.g. in some browser settings)
                scale_x, scale_y = 1.0, 1.0
            else:
                scale_x = viewport["width"] / sw
                scale_y = viewport["height"] / sh
            
            # 4. Detect target element coordinates
            coords = self.detector.find_element_by_text(temp_path, text_or_label)
            if coords:
                cx, cy = coords
                # Scale from screenshot coords to logical browser viewport coords
                px = int(cx * scale_x)
                py = int(cy * scale_y)
                logger.info(f"Resolved visual target '{text_or_label}' from screen ({cx}, {cy}) to logical browser ({px}, {py})")
                return px, py
            return None
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def visual_click(self, text_or_label: str, timeout_ms: int = 10000) -> bool:
        """
        Locate an element visually by text/label and click it.
        """
        start = time.time()
        while time.time() - start < (timeout_ms / 1000.0):
            coords = self._resolve_coordinates(text_or_label)
            if coords:
                x, y = coords
                self.page.mouse.click(x, y)
                logger.info(f"Successfully performed visual_click on '{text_or_label}' at ({x}, {y})")
                return True
            time.sleep(0.5)
        
        raise TimeoutError(f"Could not locate element with text/label '{text_or_label}' visually within {timeout_ms}ms")

    def visual_fill(self, text_or_label: str, value: str, timeout_ms: int = 10000) -> bool:
        """
        Locate an input box visually using its text label or placeholder, click it, clear it, and type the value.
        """
        start = time.time()
        while time.time() - start < (timeout_ms / 1000.0):
            coords = self._resolve_coordinates(text_or_label)
            if coords:
                x, y = coords
                # Click to focus the input field
                self.page.mouse.click(x, y)
                
                # Highlight and clear existing text
                # We can perform Triple click to select all text, then type
                self.page.mouse.click(x, y, click_count=3)
                self.page.keyboard.press("Backspace")
                
                # Type the new value
                self.page.keyboard.type(value)
                logger.info(f"Successfully performed visual_fill on '{text_or_label}' with value '{value}'")
                return True
            time.sleep(0.5)
            
        raise TimeoutError(f"Could not locate input field with text/label '{text_or_label}' visually within {timeout_ms}ms")

    def visual_wait_for(self, text_or_label: str, timeout_ms: int = 10000) -> bool:
        """
        Wait for an element to be visually present on the page.
        """
        start = time.time()
        while time.time() - start < (timeout_ms / 1000.0):
            coords = self._resolve_coordinates(text_or_label)
            if coords:
                logger.info(f"Visual element '{text_or_label}' is now present.")
                return True
            time.sleep(0.5)
            
        raise TimeoutError(f"Timed out waiting for visual element '{text_or_label}' to be present within {timeout_ms}ms")
