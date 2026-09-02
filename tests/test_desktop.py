import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from visiflow.desktop import VisiDesktop

class TestVisiDesktop(unittest.TestCase):
    def test_desktop_mock_actions(self):
        desktop = VisiDesktop()
        # Mock pyautogui
        mock_pyautogui = MagicMock()
        desktop.pyautogui = mock_pyautogui

        # Test spatial desc formatting
        desc = desktop._format_target_desc("Delete", right_of="Alice Smith")
        self.assertEqual(desc, "Delete (right_of='Alice Smith')")

        # Test press
        desktop.press("Enter")
        mock_pyautogui.press.assert_called_with("enter")

        print("\n[PASS] VisiDesktop formatting and keyboard actions verified.")

if __name__ == "__main__":
    unittest.main()
