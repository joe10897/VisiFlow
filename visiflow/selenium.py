import os
import tempfile
import time
import cv2
from typing import Optional, Any
from .core import VisiFlowDetector, logger

class VisiSeleniumDriver:
    def __init__(self, driver: Any, detector: Optional[VisiFlowDetector] = None):
        """
        Wrapper/Helper for Selenium WebDriver to add visual action capabilities.
        
        :param driver: The Selenium WebDriver instance
        :param detector: An optional custom VisiFlowDetector instance
        """
        self.driver = driver
        self.detector = detector or VisiFlowDetector()

    def _resolve_coordinates(self, text_or_label: str) -> Optional[tuple]:
        """
        Take a screenshot, run visual detection, scale coordinates to page viewport, and return them.
        """
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        
        try:
            self.driver.save_screenshot(temp_path)
            
            # 2. Get image dimensions (physical pixels)
            img = cv2.imread(temp_path)
            if img is None:
                logger.error("Failed to read captured screenshot.")
                return None
            sh, sw = img.shape[:2]
            
            # 3. Get viewport size (logical browser pixels)
            viewport = self.driver.execute_script(
                "return {width: window.innerWidth, height: window.innerHeight};"
            )
            if not viewport or "width" not in viewport or "height" not in viewport:
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
                # Execute click via JS at viewport coordinates (reliable across platforms)
                clicked = self.driver.execute_script(
                    f"const el = document.elementFromPoint({x}, {y}); if (el) {{ el.click(); return true; }} return false;"
                )
                if clicked:
                    logger.info(f"Successfully performed JS visual_click on '{text_or_label}' at ({x}, {y})")
                    return True
                else:
                    # Fallback to ActionChains relative to body element
                    try:
                        from selenium.webdriver.common.action_chains import ActionChains
                        body = self.driver.find_element("tag name", "body")
                        # Move to body top-left, then offset
                        ActionChains(self.driver).move_to_element_with_offset(body, x, y).click().perform()
                        logger.info(f"Successfully performed ActionChains visual_click on '{text_or_label}' at ({x}, {y})")
                        return True
                    except Exception as e:
                        logger.warning(f"ActionChains click fallback failed: {e}")
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
                # Focus the input field and select all text to clear it
                focused = self.driver.execute_script(
                    f"""
                    const el = document.elementFromPoint({x}, {y});
                    if (el) {{
                        el.focus();
                        if (typeof el.select === 'function') {{
                            el.select();
                        }}
                        return true;
                    }}
                    return false;
                    """
                )
                if focused:
                    # Send text to currently active/focused element
                    from selenium.webdriver.common.action_chains import ActionChains
                    from selenium.webdriver.common.keys import Keys
                    actions = ActionChains(self.driver)
                    # Clear using backspace
                    actions.send_keys(Keys.BACKSPACE * 100)
                    actions.send_keys(value)
                    actions.perform()
                    logger.info(f"Successfully performed visual_fill on '{text_or_label}' with value '{value}'")
                    return True
            time.sleep(0.5)
            
        raise TimeoutError(f"Could not locate input field with text/label '{text_or_label}' visually within {timeout_ms}ms")
