import traceback
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from visiflow.core import VisiFlowDetector

try:
    print("Initializing detector...")
    detector = VisiFlowDetector()
    print("Detector initialized.")
    
    # Run test on dummy image
    import numpy as np
    import cv2
    dummy_img = np.zeros((1024, 1024, 3), dtype=np.uint8)
    cv2.imwrite("dummy_test.png", dummy_img)
    
    print("Running detect_elements...")
    res = detector.detect_elements("dummy_test.png")
    print(f"detect_elements count: {len(res)}")
    
    print("Running run_ocr...")
    ocr_res = detector.run_ocr("dummy_test.png")
    print(f"run_ocr count: {len(ocr_res)}")
    
except Exception as e:
    print("=== CRASH DETECTED ===")
    traceback.print_exc()
