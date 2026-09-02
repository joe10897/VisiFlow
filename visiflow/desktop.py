import os
import sys
import time
import tempfile
import cv2
from typing import Optional, Tuple, Any

from .core import VisiFlowDetector, logger
from .reporter import global_reporter

class VisiDesktop:
    """
    Cross-platform Visual Desktop & OS-level RPA Automation Controller.
    Automates native desktop applications (Windows, macOS, Linux), Electron apps,
    and OS dialog boxes without requiring DOM selectors.
    """
    def __init__(self, detector: Optional[VisiFlowDetector] = None):
        try:
            import pyautogui
            self.pyautogui = pyautogui
            # Disable pyautogui failsafe pause by default for faster execution
            self.pyautogui.PAUSE = 0.1
        except ImportError:
            self.pyautogui = None

        self.detector = detector or VisiFlowDetector()

    def _ensure_pyautogui(self):
        if self.pyautogui is None:
            raise ImportError(
                "VisiDesktop requires 'pyautogui'. Please install it using: "
                "pip install \"visiflow[desktop]\" or pip install pyautogui mss"
            )

    def capture_screenshot(self) -> str:
        """
        Capture the current desktop screen and return the temporary file path.
        """
        self._ensure_pyautogui()
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        
        try:
            screenshot = self.pyautogui.screenshot()
            screenshot.save(temp_path)
            return temp_path
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise RuntimeError(f"Failed to capture desktop screenshot: {e}")

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
    ) -> Optional[Tuple[int, int]]:
        temp_path = self.capture_screenshot()
        try:
            coords = self.detector.find_element_by_text(
                temp_path,
                text_or_label,
                right_of=right_of,
                left_of=left_of,
                below=below,
                above=above,
                index=index
            )
            return coords
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def click(
        self,
        text_or_label: str,
        right_of: Optional[str] = None,
        left_of: Optional[str] = None,
        below: Optional[str] = None,
        above: Optional[str] = None,
        index: Optional[int] = None,
        timeout_s: float = 10.0,
        button: str = "left",
        clicks: int = 1
    ) -> bool:
        """
        Visually locate an element on the desktop and click it.
        """
        self._ensure_pyautogui()
        desc = self._format_target_desc(text_or_label, right_of, left_of, below, above, index)
        start = time.time()

        while time.time() - start < timeout_s:
            coords = self._resolve_coordinates(text_or_label, right_of, left_of, below, above, index)
            if coords:
                x, y = coords
                self.pyautogui.click(x=x, y=y, button=button, clicks=clicks)
                logger.info(f"[VisiDesktop] Clicked '{desc}' at ({x}, {y})")
                return True
            time.sleep(0.5)

        raise TimeoutError(f"[VisiDesktop] Could not visually locate desktop element '{desc}' within {timeout_s}s")

    def fill(
        self,
        text_or_label: str,
        value: str,
        right_of: Optional[str] = None,
        left_of: Optional[str] = None,
        below: Optional[str] = None,
        above: Optional[str] = None,
        index: Optional[int] = None,
        timeout_s: float = 10.0
    ) -> bool:
        """
        Visually locate an input field on the desktop, click it, select all, and type value.
        """
        self._ensure_pyautogui()
        desc = self._format_target_desc(text_or_label, right_of, left_of, below, above, index)
        start = time.time()

        while time.time() - start < timeout_s:
            coords = self._resolve_coordinates(text_or_label, right_of, left_of, below, above, index)
            if coords:
                x, y = coords
                self.pyautogui.click(x=x, y=y, clicks=3)
                self.pyautogui.press("backspace")
                self.pyautogui.write(value, interval=0.02)
                logger.info(f"[VisiDesktop] Filled '{desc}' with '{value}'")
                return True
            time.sleep(0.5)

        raise TimeoutError(f"[VisiDesktop] Could not visually locate desktop input '{desc}' within {timeout_s}s")

    def press(self, key: str):
        """
        Press a keyboard key on the active desktop application.
        """
        self._ensure_pyautogui()
        clean_key = key.strip("{}").lower()
        self.pyautogui.press(clean_key)
        logger.info(f"[VisiDesktop] Pressed keyboard key: '{clean_key}'")

    def assert_visible(
        self,
        text_or_label: str,
        right_of: Optional[str] = None,
        left_of: Optional[str] = None,
        below: Optional[str] = None,
        above: Optional[str] = None,
        index: Optional[int] = None,
        timeout_s: float = 5.0
    ) -> bool:
        """
        Assert that an element is visible on the desktop screen.
        """
        desc = self._format_target_desc(text_or_label, right_of, left_of, below, above, index)
        start = time.time()

        while time.time() - start < timeout_s:
            coords = self._resolve_coordinates(text_or_label, right_of, left_of, below, above, index)
            if coords:
                return True
            time.sleep(0.5)

        raise AssertionError(f"[VisiDesktop] Assertion failed: '{desc}' is not visible on desktop screen after {timeout_s}s")
