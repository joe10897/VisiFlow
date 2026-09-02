import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from visiflow.runner import VisiFlowYAMLRunner

class TestVisiFlowRunner(unittest.TestCase):
    def setUp(self):
        self.sample_yaml = Path(__file__).resolve().parent / "sample_test.yaml"

    def test_runner_load_and_step_normalization(self):
        runner = VisiFlowYAMLRunner(str(self.sample_yaml))
        self.assertIsNotNone(runner.test_data)
        self.assertEqual(runner.test_data.get("name"), "E2E Visual & Spatial Automation Test")
        
        # Test step normalization
        raw_step = {"click": "Delete", "right_of": "Alice Smith"}
        normalized = runner._normalize_step(raw_step)
        self.assertEqual(normalized["action"], "click")
        self.assertEqual(normalized["target"], "Delete")
        self.assertEqual(normalized["right_of"], "Alice Smith")
        print("\n[PASS] YAML runner correctly loaded test and normalized step definitions.")

if __name__ == "__main__":
    unittest.main()
