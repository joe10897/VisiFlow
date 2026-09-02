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

    def _format_target_desc(
        self,
        text_or_label: str,
        right_of: Optional[str] = None,
        left_of: Optional[str] = None,
        below: Optional[str] = None,
        above: Optional[str] = None,
        index: Optional[int] = None
    ) -> str:
        spatial_parts = []
        if right_of: spatial_parts.append(f"right_of='{right_of}'")
        if left_of: spatial_parts.append(f"left_of='{left_of}'")
        if below: spatial_parts.append(f"below='{below}'")
        if above: spatial_parts.append(f"above='{above}'")
        if index is not None: spatial_parts.append(f"index={index}")
        if spatial_parts:
            return f"{text_or_label} ({', '.join(spatial_parts)})"
        return text_or_label

    def _resolve_coordinates(
        self,
        text_or_label: str,
        right_of: Optional[str] = None,
        left_of: Optional[str] = None,
        below: Optional[str] = None,
        above: Optional[str] = None,
        index: Optional[int] = None
    ) -> Optional[tuple]:
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
            
            # 4. Detect target element coordinates with spatial constraints
            coords = self.detector.find_element_by_text(
                temp_path,
                text_or_label,
                right_of=right_of,
                left_of=left_of,
                below=below,
                above=above,
                index=index
            )
            if coords:
                cx, cy = coords
                px = int(cx * scale_x)
                py = int(cy * scale_y)
                target_desc = self._format_target_desc(text_or_label, right_of, left_of, below, above, index)
                logger.info(f"Resolved visual target '{target_desc}' from screen ({cx}, {cy}) to logical browser ({px}, {py})")
                return px, py
            return None
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def visual_click(
        self,
        text_or_label: str,
        right_of: Optional[str] = None,
        left_of: Optional[str] = None,
        below: Optional[str] = None,
        above: Optional[str] = None,
        index: Optional[int] = None,
        timeout_ms: int = 10000
    ) -> bool:
        """
        Locate an element visually by text/label (with optional spatial constraints) and click it.
        """
        target_desc = self._format_target_desc(text_or_label, right_of, left_of, below, above, index)
        screenshot_before = self._capture_temp_screenshot()
        step_idx = global_reporter.start_step("click", target_desc, screenshot_before)
        if screenshot_before and os.path.exists(screenshot_before):
            try:
                os.remove(screenshot_before)
            except Exception:
                pass
                
        start = time.time()
        while time.time() - start < (timeout_ms / 1000.0):
            coords = self._resolve_coordinates(
                text_or_label,
                right_of=right_of,
                left_of=left_of,
                below=below,
                above=above,
                index=index
            )
            if coords:
                x, y = coords
                self.page.mouse.click(x, y)
                logger.info(f"Successfully performed visual_click on '{target_desc}' at ({x}, {y})")
                
                match_data = self.detector.last_match or {"score": 1.0, "healed": False, "matched_text": text_or_label}
                screenshot_after = self._capture_temp_screenshot()
                global_reporter.end_step(
                    step_idx,
                    success=True,
                    score=match_data.get("score", 1.0),
                    healed=match_data.get("healed", False),
                    original_match=target_desc,
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
            
        global_reporter.end_step(step_idx, success=False, score=0.0, healed=False, original_match=target_desc, healed_match="")
        raise TimeoutError(f"Could not locate element '{target_desc}' visually within {timeout_ms}ms")

    def visual_press(self, key: str) -> bool:
        """
        Press a keyboard key on the active/focused element.
        
        :param key: The key name (e.g. "Enter", "{enter}", "Backspace")
        """
        clean_key = key.strip("{}")
        title_key = clean_key.capitalize() if clean_key.lower() in ["enter", "tab", "escape", "backspace"] else clean_key
        self.page.keyboard.press(title_key)
        logger.info(f"Successfully pressed keyboard key: {title_key}")
        return True

    def visual_fill(
        self,
        text_or_label: str,
        value: str,
        right_of: Optional[str] = None,
        left_of: Optional[str] = None,
        below: Optional[str] = None,
        above: Optional[str] = None,
        index: Optional[int] = None,
        timeout_ms: int = 10000
    ) -> bool:
        """
        Locate an input box visually (with optional spatial constraints), click it, clear it, and type the value.
        """
        target_desc = self._format_target_desc(text_or_label, right_of, left_of, below, above, index)
        screenshot_before = self._capture_temp_screenshot()
        step_idx = global_reporter.start_step("fill", f"{target_desc} -> {value}", screenshot_before)
        if screenshot_before and os.path.exists(screenshot_before):
            try:
                os.remove(screenshot_before)
            except Exception:
                pass

        start = time.time()
        while time.time() - start < (timeout_ms / 1000.0):
            coords = self._resolve_coordinates(
                text_or_label,
                right_of=right_of,
                left_of=left_of,
                below=below,
                above=above,
                index=index
            )
            if coords:
                x, y = coords
                self.page.mouse.click(x, y)
                self.page.mouse.click(x, y, click_count=3)
                self.page.keyboard.press("Backspace")
                self.page.keyboard.type(value)
                logger.info(f"Successfully performed visual_fill on '{target_desc}' with value '{value}'")
                
                match_data = self.detector.last_match or {"score": 1.0, "healed": False, "matched_text": text_or_label}
                screenshot_after = self._capture_temp_screenshot()
                global_reporter.end_step(
                    step_idx,
                    success=True,
                    score=match_data.get("score", 1.0),
                    healed=match_data.get("healed", False),
                    original_match=target_desc,
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
            
        global_reporter.end_step(step_idx, success=False, score=0.0, healed=False, original_match=target_desc, healed_match="")
        raise TimeoutError(f"Could not locate input field '{target_desc}' visually within {timeout_ms}ms")

    def visual_wait_for(
        self,
        text_or_label: str,
        right_of: Optional[str] = None,
        left_of: Optional[str] = None,
        below: Optional[str] = None,
        above: Optional[str] = None,
        index: Optional[int] = None,
        timeout_ms: int = 10000
    ) -> bool:
        """
        Wait for an element to be visually present on the page.
        """
        target_desc = self._format_target_desc(text_or_label, right_of, left_of, below, above, index)
        start = time.time()
        while time.time() - start < (timeout_ms / 1000.0):
            coords = self._resolve_coordinates(
                text_or_label,
                right_of=right_of,
                left_of=left_of,
                below=below,
                above=above,
                index=index
            )
            if coords:
                logger.info(f"Visual element '{target_desc}' is now present.")
                return True
            time.sleep(0.5)
            
        raise TimeoutError(f"Timed out waiting for visual element '{target_desc}' to be present within {timeout_ms}ms")

    def visual_assert_visible(
        self,
        text_or_label: str,
        right_of: Optional[str] = None,
        left_of: Optional[str] = None,
        below: Optional[str] = None,
        above: Optional[str] = None,
        index: Optional[int] = None,
        timeout_ms: int = 10000
    ) -> bool:
        """
        Assert that an element is visually visible on the page.
        """
        target_desc = self._format_target_desc(text_or_label, right_of, left_of, below, above, index)
        screenshot_before = self._capture_temp_screenshot()
        step_idx = global_reporter.start_step("assert_visible", target_desc, screenshot_before)
        if screenshot_before and os.path.exists(screenshot_before):
            try:
                os.remove(screenshot_before)
            except Exception:
                pass

        try:
            self.visual_wait_for(
                text_or_label,
                right_of=right_of,
                left_of=left_of,
                below=below,
                above=above,
                index=index,
                timeout_ms=timeout_ms
            )
            match_data = self.detector.last_match or {"score": 1.0, "healed": False, "matched_text": text_or_label}
            screenshot_after = self._capture_temp_screenshot()
            global_reporter.end_step(
                step_idx,
                success=True,
                score=match_data.get("score", 1.0),
                healed=match_data.get("healed", False),
                original_match=target_desc,
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
            global_reporter.end_step(step_idx, success=False, score=0.0, healed=False, original_match=target_desc, healed_match="")
            raise AssertionError(f"Visual assertion failed: '{target_desc}' is not visible on the page. Error: {e}")

    def visual_assert_not_visible(
        self,
        text_or_label: str,
        right_of: Optional[str] = None,
        left_of: Optional[str] = None,
        below: Optional[str] = None,
        above: Optional[str] = None,
        index: Optional[int] = None,
        timeout_ms: int = 5000
    ) -> bool:
        """
        Assert that an element is NOT visually visible on the page.
        """
        target_desc = self._format_target_desc(text_or_label, right_of, left_of, below, above, index)
        screenshot_before = self._capture_temp_screenshot()
        step_idx = global_reporter.start_step("assert_not_visible", target_desc, screenshot_before)
        if screenshot_before and os.path.exists(screenshot_before):
            try:
                os.remove(screenshot_before)
            except Exception:
                pass

        start = time.time()
        while time.time() - start < (timeout_ms / 1000.0):
            try:
                coords = self._resolve_coordinates(
                    text_or_label,
                    right_of=right_of,
                    left_of=left_of,
                    below=below,
                    above=above,
                    index=index
                )
                if not coords:
                    screenshot_after = self._capture_temp_screenshot()
                    global_reporter.end_step(
                        step_idx,
                        success=True,
                        score=1.0,
                        healed=False,
                        original_match=target_desc,
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

        global_reporter.end_step(step_idx, success=False, score=0.0, healed=False, original_match=target_desc, healed_match="")
        raise AssertionError(f"Visual assertion failed: '{target_desc}' is still visible on the page after {timeout_ms}ms")
