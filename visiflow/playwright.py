import os
import tempfile
import time
import cv2
from typing import Optional, Any
from .core import VisiFlowDetector, logger
from .reporter import global_reporter

class VisiPlaywrightPage:
    def __init__(self, page: Any, detector: Optional[VisiFlowDetector] = None):
        """
        Wrapper for Playwright Page to add visual action and assertion capabilities.
        
        :param page: The playwright Page object
        :param detector: An optional custom VisiFlowDetector instance
        """
        self.page = page
        self.detector = detector or VisiFlowDetector()

    def _capture_temp_screenshot(self) -> Optional[str]:
        try:
            fd, temp_path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            self.page.screenshot(path=temp_path)
            return temp_path
        except Exception as e:
            logger.error(f"Failed to capture temporary screenshot: {e}")
            return None

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
                scale_x, scale_y = 1.0, 1.0
            else:
                scale_x = viewport["width"] / sw
                scale_y = viewport["height"] / sh
            
            # 4. Detect target element coordinates
            coords = self.detector.find_element_by_text(temp_path, text_or_label)
            if coords:
                cx, cy = coords
                px = int(cx * scale_x)
                py = int(cy * scale_y)
                logger.info(f"Resolved visual target '{text_or_label}' from screen ({cx}, {cy}) to logical browser ({px}, {py})")
                return px, py
            return None
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def visual_click(self, text_or_label: str, timeout_ms: int = 10000) -> bool:
        """
        Locate an element visually by text/label and click it.
        """
        screenshot_before = self._capture_temp_screenshot()
        step_idx = global_reporter.start_step("click", text_or_label, screenshot_before)
        if screenshot_before and os.path.exists(screenshot_before):
            try:
                os.remove(screenshot_before)
            except Exception:
                pass
                
        start = time.time()
        while time.time() - start < (timeout_ms / 1000.0):
            coords = self._resolve_coordinates(text_or_label)
            if coords:
                x, y = coords
                self.page.mouse.click(x, y)
                logger.info(f"Successfully performed visual_click on '{text_or_label}' at ({x}, {y})")
                
                match_data = self.detector.last_match or {"score": 1.0, "healed": False, "matched_text": text_or_label}
                screenshot_after = self._capture_temp_screenshot()
                global_reporter.end_step(
                    step_idx,
                    success=True,
                    score=match_data.get("score", 1.0),
                    healed=match_data.get("healed", False),
                    original_match=text_or_label,
                    healed_match=match_data.get("matched_text", text_or_label),
                    screenshot_path_after=screenshot_after
                )
                if screenshot_after and os.path.exists(screenshot_after):
                    try:
                        os.remove(screenshot_after)
                    except Exception:
                        pass
                return True
            time.sleep(0.5)
            
        global_reporter.end_step(step_idx, success=False, score=0.0, healed=False, original_match=text_or_label, healed_match="")
        raise TimeoutError(f"Could not locate element with text/label '{text_or_label}' visually within {timeout_ms}ms")

    def visual_fill(self, text_or_label: str, value: str, timeout_ms: int = 10000) -> bool:
        """
        Locate an input box visually, click it, clear it, and type the value.
        """
        screenshot_before = self._capture_temp_screenshot()
        step_idx = global_reporter.start_step("fill", f"{text_or_label} -> {value}", screenshot_before)
        if screenshot_before and os.path.exists(screenshot_before):
            try:
                os.remove(screenshot_before)
            except Exception:
                pass

        start = time.time()
        while time.time() - start < (timeout_ms / 1000.0):
            coords = self._resolve_coordinates(text_or_label)
            if coords:
                x, y = coords
                self.page.mouse.click(x, y)
                self.page.mouse.click(x, y, click_count=3)
                self.page.keyboard.press("Backspace")
                self.page.keyboard.type(value)
                logger.info(f"Successfully performed visual_fill on '{text_or_label}' with value '{value}'")
                
                match_data = self.detector.last_match or {"score": 1.0, "healed": False, "matched_text": text_or_label}
                screenshot_after = self._capture_temp_screenshot()
                global_reporter.end_step(
                    step_idx,
                    success=True,
                    score=match_data.get("score", 1.0),
                    healed=match_data.get("healed", False),
                    original_match=text_or_label,
                    healed_match=match_data.get("matched_text", text_or_label),
                    screenshot_path_after=screenshot_after
                )
                if screenshot_after and os.path.exists(screenshot_after):
                    try:
                        os.remove(screenshot_after)
                    except Exception:
                        pass
                return True
            time.sleep(0.5)
            
        global_reporter.end_step(step_idx, success=False, score=0.0, healed=False, original_match=text_or_label, healed_match="")
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

    def visual_assert_visible(self, text_or_label: str, timeout_ms: int = 10000) -> bool:
        """
        Assert that an element is visually visible on the page.
        """
        screenshot_before = self._capture_temp_screenshot()
        step_idx = global_reporter.start_step("assert_visible", text_or_label, screenshot_before)
        if screenshot_before and os.path.exists(screenshot_before):
            try:
                os.remove(screenshot_before)
            except Exception:
                pass

        try:
            self.visual_wait_for(text_or_label, timeout_ms)
            match_data = self.detector.last_match or {"score": 1.0, "healed": False, "matched_text": text_or_label}
            screenshot_after = self._capture_temp_screenshot()
            global_reporter.end_step(
                step_idx,
                success=True,
                score=match_data.get("score", 1.0),
                healed=match_data.get("healed", False),
                original_match=text_or_label,
                healed_match=match_data.get("matched_text", text_or_label),
                screenshot_path_after=screenshot_after
            )
            if screenshot_after and os.path.exists(screenshot_after):
                try:
                    os.remove(screenshot_after)
                except Exception:
                    pass
            return True
        except Exception as e:
            global_reporter.end_step(step_idx, success=False, score=0.0, healed=False, original_match=text_or_label, healed_match="")
            raise AssertionError(f"Visual assertion failed: '{text_or_label}' is not visible on the page. Error: {e}")

    def visual_assert_not_visible(self, text_or_label: str, timeout_ms: int = 5000) -> bool:
        """
        Assert that an element is NOT visually visible on the page.
        """
        screenshot_before = self._capture_temp_screenshot()
        step_idx = global_reporter.start_step("assert_not_visible", text_or_label, screenshot_before)
        if screenshot_before and os.path.exists(screenshot_before):
            try:
                os.remove(screenshot_before)
            except Exception:
                pass

        start = time.time()
        while time.time() - start < (timeout_ms / 1000.0):
            try:
                coords = self._resolve_coordinates(text_or_label)
                if not coords:
                    screenshot_after = self._capture_temp_screenshot()
                    global_reporter.end_step(
                        step_idx,
                        success=True,
                        score=1.0,
                        healed=False,
                        original_match=text_or_label,
                        healed_match="",
                        screenshot_path_after=screenshot_after
                    )
                    if screenshot_after and os.path.exists(screenshot_after):
                        try:
                            os.remove(screenshot_after)
                        except Exception:
                            pass
                    return True
            except Exception:
                pass
            time.sleep(0.5)

        global_reporter.end_step(step_idx, success=False, score=0.0, healed=False, original_match=text_or_label, healed_match="")
        raise AssertionError(f"Visual assertion failed: '{text_or_label}' is still visible on the page after {timeout_ms}ms")
