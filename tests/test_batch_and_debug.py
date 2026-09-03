import os
import sys
import unittest
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import cv2

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from visiflow import VisiFlowDetector, generate_junit_xml
from visiflow.runner import VisiFlowYAMLRunner

class TestBatchAndDebug(unittest.TestCase):
    def test_junit_xml_generation(self):
        sample_suite_results = [
            {
                "file": "login_test.yaml",
                "name": "Login Test",
                "success": True,
                "duration": 4.5,
                "steps": [
                    {"name": "GOTO /login", "time": 1.0, "status": "passed", "error": None},
                    {"name": "FILL Username", "time": 1.5, "status": "passed", "error": None},
                    {"name": "CLICK Submit", "time": 2.0, "status": "passed", "error": None}
                ]
            },
            {
                "file": "checkout_test.yaml",
                "name": "Checkout Test",
                "success": False,
                "duration": 5.2,
                "steps": [
                    {"name": "GOTO /cart", "time": 1.2, "status": "passed", "error": None},
                    {
                        "name": "CLICK Place Order",
                        "time": 4.0,
                        "status": "failed",
                        "error": "Element not found",
                        "suggestions": ["Confirm & Pay", "Submit Order"],
                        "debug_diff": "debug_diff_step_2.png"
                    }
                ]
            }
        ]

        fd, temp_junit = tempfile.mkstemp(suffix=".xml")
        os.close(fd)
        try:
            generate_junit_xml(sample_suite_results, temp_junit)
            self.assertTrue(os.path.exists(temp_junit))

            tree = ET.parse(temp_junit)
            root = tree.getroot()
            self.assertEqual(root.tag, "testsuites")
            self.assertEqual(root.attrib["tests"], "5")
            self.assertEqual(root.attrib["failures"], "1")
            
            suites = root.findall("testsuite")
            self.assertEqual(len(suites), 2)
            
            # Check failure message in second suite
            failed_case = suites[1].findall("testcase")[1]
            failure = failed_case.find("failure")
            self.assertIsNotNone(failure)
            self.assertIn("Auto-Suggestions: Confirm & Pay, Submit Order", failure.text)
            print("\n[PASS] JUnit XML report structure and failure diagnostics verified.")
        finally:
            if os.path.exists(temp_junit):
                os.remove(temp_junit)

    def test_smart_visual_debugger_and_diff(self):
        detector = VisiFlowDetector(use_yolo=False)
        # Mock last_ocr_results
        detector.last_ocr_results = [
            {"text": "Submit Order Now", "box": [100, 200, 250, 240], "confidence": 0.95},
            {"text": "Cancel Order", "box": [300, 200, 420, 240], "confidence": 0.92},
            {"text": "Shipping Address", "box": [50, 50, 200, 80], "confidence": 0.98}
        ]

        # Query "Submit" -> should match "Submit Order Now" with highest similarity
        candidates = detector.get_closest_candidates("Submit", top_k=2)
        self.assertGreaterEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["text"], "Submit Order Now")
        self.assertGreater(candidates[0]["score"], 0.6)

        # Test visual debug diff generation
        dummy_img = np.zeros((400, 600, 3), dtype=np.uint8)
        fd_in, temp_in = tempfile.mkstemp(suffix=".png")
        os.close(fd_in)
        fd_out, temp_out = tempfile.mkstemp(suffix=".png")
        os.close(fd_out)

        try:
            cv2.imwrite(temp_in, dummy_img)
            diff_path = detector.generate_visual_debug_diff(temp_in, "Submit", temp_out)
            self.assertTrue(os.path.exists(diff_path))
            out_img = cv2.imread(diff_path)
            self.assertIsNotNone(out_img)
            self.assertEqual(out_img.shape, (400, 600, 3))
            print("[PASS] Smart visual debugger candidates ranking and visual diff generation verified.")
        finally:
            for p in [temp_in, temp_out]:
                if os.path.exists(p):
                    os.remove(p)

if __name__ == "__main__":
    unittest.main()
