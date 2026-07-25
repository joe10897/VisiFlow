import cv2
import numpy as np
import difflib
import logging
from typing import List, Dict, Tuple, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VisiFlow")

class VisiFlowDetector:
    def __init__(self, model_path: Optional[str] = "yolov8n.pt", use_yolo: bool = True, languages: List[str] = ["en", "ch_tra", "ch_sim"]):
        """
        Initialize the VisiFlow local visual detector.
        
        :param model_path: Path to the YOLO model file (e.g. yolov8n.pt or a custom UI model pt/onnx).
        :param use_yolo: Whether to attempt loading and running YOLO.
        :param languages: List of languages for EasyOCR. Defaults to English, Traditional Chinese, and Simplified Chinese.
        """
        self.use_yolo = use_yolo
        self.model = None
        self.ocr_reader = None
        self.languages = languages
        self._init_yolo(model_path)
        self._init_ocr()

    def _init_yolo(self, model_path: Optional[str]):
        if not self.use_yolo:
            logger.info("YOLO is disabled by user configuration.")
            return
        
        try:
            from ultralytics import YOLO
            logger.info(f"Loading local YOLO model from {model_path}...")
            self.model = YOLO(model_path)
            logger.info("YOLO model loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load YOLO model (will fallback to OpenCV contour heuristic): {e}")
            self.model = None

    def _init_ocr(self):
        try:
            import easyocr
            logger.info(f"Initializing local EasyOCR reader for languages: {self.languages}...")
            self.ocr_reader = easyocr.Reader(self.languages, gpu=True) # Automatically detects CUDA/GPU
            logger.info("EasyOCR initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}. Please ensure torch and easyocr are installed.")
            self.ocr_reader = None

    def detect_contours(self, img: np.ndarray) -> List[Dict[str, Any]]:
        """
        OpenCV heuristic fallback: detect potential interactive UI elements (buttons, inputs)
        using hierarchical contour detection.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Apply bilateral filter to preserve edges while removing noise
        blurred = cv2.bilateralFilter(gray, 9, 75, 75)
        # Adaptive thresholding to handle different lighting / styles
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Find contours
        contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        detected = []
        
        height, width = img.shape[:2]
        min_area = 100
        max_area = (width * height) * 0.25 # Ignore containers that are too large (e.g. body/header)
        
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            area = w * h
            aspect_ratio = float(w) / h
            
            # Heuristic filter for buttons and inputs (typically wider than tall, but not too thin)
            if min_area < area < max_area:
                if 0.5 < aspect_ratio < 15 and w > 15 and h > 10:
                    detected.append({
                        "box": [x, y, x + w, y + h],
                        "label": "ui_element",
                        "confidence": 0.8,
                        "source": "opencv"
                    })
        return detected

    def detect_elements(self, img_path: str) -> List[Dict[str, Any]]:
        """
        Run YOLO detection on the screenshot.
        """
        img = cv2.imread(img_path)
        if img is None:
            logger.error(f"Image not found or unable to read: {img_path}")
            return []

        elements = []
        if self.model:
            try:
                results = self.model(img_path, verbose=False)
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        cls = int(box.cls[0].item())
                        label = self.model.names[cls]
                        conf = float(box.conf[0].item())
                        elements.append({
                            "box": [x1, y1, x2, y2],
                            "label": label,
                            "confidence": conf,
                            "source": "yolo"
                        })
            except Exception as e:
                logger.error(f"YOLO inference error: {e}")

        # Always run OpenCV heuristics as a complementary source or fallback
        contour_elements = self.detect_contours(img)
        
        # Merge YOLO and OpenCV detections (remove duplicates/heavily overlapping ones)
        all_elements = elements + contour_elements
        merged_elements = self._non_max_suppression(all_elements, iou_threshold=0.5)
        return merged_elements

    def _non_max_suppression(self, elements: List[Dict[str, Any]], iou_threshold: float) -> List[Dict[str, Any]]:
        if not elements:
            return []
        
        # Sort by confidence/source priority (YOLO preferred over OpenCV)
        sorted_elements = sorted(
            elements, 
            key=lambda e: (1 if e["source"] == "yolo" else 0, e["confidence"]), 
            reverse=True
        )
        
        keep = []
        while sorted_elements:
            best = sorted_elements.pop(0)
            keep.append(best)
            
            remaining = []
            for item in sorted_elements:
                if self._calculate_iou(best["box"], item["box"]) < iou_threshold:
                    remaining.append(item)
            sorted_elements = remaining
        return keep

    def _calculate_iou(self, boxA: List[int], boxB: List[int]) -> float:
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        
        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        
        unionArea = boxAArea + boxBArea - interArea
        if unionArea == 0:
            return 0.0
        return interArea / unionArea

    def run_ocr(self, img_path: str) -> List[Dict[str, Any]]:
        """
        Run EasyOCR on the screenshot.
        """
        if not self.ocr_reader:
            logger.warning("OCR reader is not initialized. Skipping OCR.")
            return []
        
        try:
            results = self.ocr_reader.readtext(img_path)
            ocr_elements = []
            for item in results:
                if len(item) == 3:
                    bbox, text, conf = item
                elif len(item) == 2:
                    bbox, text = item
                    conf = 1.0
                else:
                    continue

                # bbox is [[x0, y0], [x1, y1], [x2, y2], [x3, y3]]
                xs = [pt[0] for pt in bbox]
                ys = [pt[1] for pt in bbox]
                x_min, x_max = int(min(xs)), int(max(xs))
                y_min, y_max = int(min(ys)), int(max(ys))
                
                ocr_elements.append({
                    "text": str(text).strip(),
                    "box": [x_min, y_min, x_max, y_max],
                    "confidence": float(conf)
                })
            return ocr_elements
        except Exception as e:
            logger.error(f"OCR execution error: {e}")
            return []

    def find_element_by_text(self, img_path: str, query_text: str, fuzzy_threshold: float = 0.6) -> Optional[Tuple[int, int]]:
        """
        Find target element coordinates by searching for text, matching with YOLO/OpenCV bounding boxes.
        
        :param img_path: Path to browser screenshot.
        :param query_text: Target text to look for (e.g. "Submit", "登入").
        :param fuzzy_threshold: Levenshtein/Gestalt similarity threshold (0.0 to 1.0).
        :return: Center coordinates (x, y) of the matched element, or None if not found.
        """
        ocr_results = self.run_ocr(img_path)
        if not ocr_results:
            logger.warning("No OCR text detected.")
            return None

        # 1. Look for fuzzy text match with whitespace normalization (crucial for Chinese/CJK OCR)
        best_match = None
        best_score = 0.0
        
        query_lower = query_text.lower()
        query_clean = "".join(query_lower.split())
        
        for ocr_item in ocr_results:
            text = ocr_item["text"]
            text_lower = text.lower()
            text_clean = "".join(text_lower.split())
            
            # Substring match (with or without spaces) yields full score
            if query_lower in text_lower or (query_clean and query_clean in text_clean):
                score = 1.0
            else:
                # Compare ratio on clean strings
                score_raw = difflib.SequenceMatcher(None, query_lower, text_lower).ratio()
                score_clean = difflib.SequenceMatcher(None, query_clean, text_clean).ratio() if query_clean else 0.0
                score = max(score_raw, score_clean)
            
            if score > best_score and score >= fuzzy_threshold:
                best_score = score
                best_match = ocr_item

        if not best_match:
            logger.warning(f"No text match found for query: '{query_text}' (best score was below threshold {fuzzy_threshold})")
            return None
        
        logger.info(f"Matched text '{best_match['text']}' for query '{query_text}' with score {best_score:.2f}")
        
        # 2. Get the bounding box of matched text
        txt_box = best_match["box"] # [x_min, y_min, x_max, y_max]
        txt_center = ((txt_box[0] + txt_box[2]) // 2, (txt_box[1] + txt_box[3]) // 2)

        # 3. Find if there is a YOLO/contour element bounding box enclosing or heavily overlapping this text
        ui_elements = self.detect_elements(img_path)
        containing_element = None
        
        for elem in ui_elements:
            box = elem["box"] # [x_min, y_min, x_max, y_max]
            # Check if text center is inside the UI element box
            if box[0] <= txt_center[0] <= box[2] and box[1] <= txt_center[1] <= box[3]:
                containing_element = elem
                break
        
        if containing_element:
            # Return center of the containing UI element (e.g., the actual button border, which is safer for clicking)
            elem_box = containing_element["box"]
            elem_center = ((elem_box[0] + elem_box[2]) // 2, (elem_box[1] + elem_box[3]) // 2)
            logger.info(f"Target text resides inside UI element: {containing_element['label']} {elem_box}. Clicking element center.")
            return elem_center
        else:
            # Fallback to clicking the text center directly
            logger.info("Target text center is not inside any detected UI element container. Clicking text center directly.")
            return txt_center
