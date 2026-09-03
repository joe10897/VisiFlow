import os
import cv2
import numpy as np
import difflib
import logging
from typing import List, Dict, Tuple, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VisiFlow")

class VisiFlowDetector:
    def __init__(self, model_path: Optional[str] = None, use_yolo: bool = True, languages: List[str] = ["ch_tra", "en"]):
        """
        Initialize the VisiFlow local visual detector.
        
        :param model_path: Path to the YOLO model file (e.g. yolov8n.pt or a custom UI model pt/onnx).
        :param use_yolo: Whether to attempt loading and running YOLO.
        :param languages: List of languages for EasyOCR. Defaults to Traditional Chinese and English.
        """
        self.use_yolo = use_yolo
        self.model_path = None
        self.model = None
        self.ocr_reader = None
        self.languages = languages
        self.last_match = None
        self.last_ocr_results = []
        self.last_candidates = []
        self._init_yolo(model_path)
        self._init_ocr()

    def _init_yolo(self, model_path: Optional[str]):
        if not self.use_yolo:
            logger.info("YOLO is disabled by user configuration.")
            return
        
        if model_path is None:
            # Check if local yolo26n.onnx exists, else fallback
            if os.path.exists("yolo26n.onnx"):
                model_path = "yolo26n.onnx"
            else:
                model_path = "yolov8n.pt"
        
        self.model_path = model_path
        
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
            self.ocr_reader = easyocr.Reader(self.languages)
            logger.info("EasyOCR initialized successfully.")
        except Exception as e:
            logger.warning(f"Failed to initialize EasyOCR with {self.languages}: {e}. Trying fallback ['ch_tra', 'en']...")
            try:
                import easyocr
                self.ocr_reader = easyocr.Reader(["ch_tra", "en"])
                logger.info("EasyOCR initialized successfully with fallback ['ch_tra', 'en'].")
            except Exception as e2:
                logger.error(f"Failed to initialize EasyOCR: {e2}")
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
                # Force device="cpu" for ONNX models to bypass local GPU execution provider DLL mismatches
                device = "cpu" if self.model_path and str(self.model_path).endswith(".onnx") else None
                results = self.model(img_path, device=device, verbose=False)
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

    def run_ocr(self, img_path_or_array: Any, upscale: float = 2.0) -> List[Dict[str, Any]]:
        """
        Run EasyOCR on the screenshot. Accepts file path string or numpy image array.
        Applies 2.0x bicubic upscaling and contrast enhancement for superior CJK character recognition.
        """
        if not self.ocr_reader:
            logger.warning("OCR reader is not initialized. Skipping OCR.")
            return []
        
        try:
            if isinstance(img_path_or_array, str):
                img = cv2.imread(img_path_or_array)
            else:
                img = img_path_or_array

            if img is None:
                logger.warning("Invalid image provided to run_ocr.")
                return []

            # 1. Convert to 2D Grayscale
            if len(img.shape) == 3:
                if img.shape[2] == 4:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                else:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img.copy()

            # 2. Upscale image 2.0x using bicubic interpolation (enlarges font stroke details for small CJK text)
            if upscale != 1.0:
                h, w = gray.shape[:2]
                gray_proc = cv2.resize(gray, (int(w * upscale), int(h * upscale)), interpolation=cv2.INTER_CUBIC)
            else:
                gray_proc = gray

            results = self.ocr_reader.readtext(gray_proc, contrast_ths=0.1, adjust_contrast=0.5)
            ocr_elements = []
            for item in results:
                if len(item) == 3:
                    bbox, text, conf = item
                elif len(item) == 2:
                    bbox, text = item
                    conf = 1.0
                else:
                    continue

                # Scale coordinates back to original image scale
                xs = [pt[0] / upscale for pt in bbox]
                ys = [pt[1] / upscale for pt in bbox]
                x_min, x_max = int(min(xs)), int(max(xs))
                y_min, y_max = int(min(ys)), int(max(ys))
                
                ocr_elements.append({
                    "text": str(text).strip(),
                    "box": [x_min, y_min, x_max, y_max],
                    "confidence": float(conf)
                })
            self.last_ocr_results = ocr_elements
            return ocr_elements
        except Exception as e:
            import traceback
            logger.error(f"OCR execution error: {e}\n{traceback.format_exc()}")
            return []

    def _compute_text_score(self, query_text: str, target_text: str) -> float:
        """
        Compute similarity score between query text and target text.
        Includes whitespace normalization, substring matching, difflib similarity,
        and CJK character overlap tolerance.
        """
        query_lower = query_text.lower()
        query_clean = "".join(query_lower.split())
        query_chars = set(query_clean)
        
        target_lower = target_text.lower()
        target_clean = "".join(target_lower.split())
        target_chars = set(target_clean)
        
        if not query_clean or not target_clean:
            return 0.0
            
        # Exact or substring match yields full score
        if query_lower in target_lower or query_clean in target_clean:
            return 1.0
            
        score_raw = difflib.SequenceMatcher(None, query_lower, target_lower).ratio()
        score_clean = difflib.SequenceMatcher(None, query_clean, target_clean).ratio()
        score = max(score_raw, score_clean)
        
        # CJK character set overlap fallback
        is_cjk = any(0x4e00 <= ord(c) <= 0x9fff for c in query_clean)
        if is_cjk and query_chars and target_chars:
            overlap_ratio = len(query_chars & target_chars) / len(query_chars)
            if overlap_ratio >= 0.5:
                score = max(score, overlap_ratio * 0.85)
                
        return score

    def find_element_by_text(
        self,
        img_path: str,
        query_text: str,
        fuzzy_threshold: float = 0.6,
        right_of: Optional[str] = None,
        left_of: Optional[str] = None,
        below: Optional[str] = None,
        above: Optional[str] = None,
        index: Optional[int] = None
    ) -> Optional[Tuple[int, int]]:
        """
        Find target element coordinates by searching for text, matching with YOLO/OpenCV bounding boxes.
        Supports spatial relative positioning (right_of, left_of, below, above) and ordinal indexing.
        
        :param img_path: Path to browser screenshot.
        :param query_text: Target text to look for (e.g. "Submit", "登入", "Delete").
        :param fuzzy_threshold: Levenshtein/Gestalt similarity threshold (0.0 to 1.0).
        :param right_of: Text label of an anchor element that the target must be to the right of.
        :param left_of: Text label of an anchor element that the target must be to the left of.
        :param below: Text label of an anchor element that the target must be below.
        :param above: Text label of an anchor element that the target must be above.
        :param index: 0-based ordinal index among matching candidates (e.g. 0 for first, 1 for second).
        :return: Center coordinates (x, y) of the matched element, or None if not found.
        """
        ocr_results = self.run_ocr(img_path)
        if not ocr_results:
            logger.warning("No OCR text detected.")
            return None

        # 1. Collect all candidate OCR matches satisfying fuzzy threshold
        candidates = []
        for ocr_item in ocr_results:
            score = self._compute_text_score(query_text, ocr_item["text"])
            if score >= fuzzy_threshold:
                candidates.append({
                    "item": ocr_item,
                    "score": score,
                    "box": ocr_item["box"]
                })

        best_match = None
        has_spatial = any([right_of, left_of, below, above])

        if candidates and has_spatial:
            # Spatial relative positioning
            anchor_target = right_of or left_of or below or above
            anchor_candidates = []
            for ocr_item in ocr_results:
                s = self._compute_text_score(anchor_target, ocr_item["text"])
                if s >= fuzzy_threshold:
                    anchor_candidates.append({"item": ocr_item, "score": s, "box": ocr_item["box"]})
            
            if not anchor_candidates:
                logger.warning(f"Spatial anchor text '{anchor_target}' not found on page for query '{query_text}'.")
                self.last_match = {"found": False, "query": query_text, "score": 0.0, "matched_text": "", "healed": False}
                return None
            
            # Sort anchors by highest score, then reading order
            anchor_candidates.sort(key=lambda a: (-a["score"], a["box"][1] // 20, a["box"][0]))
            anchor_box = anchor_candidates[0]["box"]
            ax1, ay1, ax2, ay2 = anchor_box
            acx = (ax1 + ax2) / 2.0
            acy = (ay1 + ay2) / 2.0

            spatial_candidates = []
            for cand in candidates:
                cbox = cand["box"]
                cx1, cy1, cx2, cy2 = cbox
                tcx = (cx1 + cx2) / 2.0
                tcy = (cy1 + cy2) / 2.0

                # Directional boundaries
                if right_of and not (tcx > ax1 and cx2 > ax1):
                    continue
                if left_of and not (tcx < ax2 and cx1 < ax2):
                    continue
                if below and not (tcy > ay1 and cy2 > ay1):
                    continue
                if above and not (tcy < ay2 and cy1 < ay2):
                    continue

                # Overlap & distances
                v_overlap = max(0, min(cy2, ay2) - max(cy1, ay1))
                h_overlap = max(0, min(cx2, ax2) - max(cx1, ax1))
                v_dist = abs(tcy - acy)
                h_dist = abs(tcx - acx)

                if right_of:
                    dx = max(0, cx1 - ax2)
                    cost = dx + (v_dist * 1.5 if v_overlap > 0 else v_dist * 4.0)
                elif left_of:
                    dx = max(0, ax1 - cx2)
                    cost = dx + (v_dist * 1.5 if v_overlap > 0 else v_dist * 4.0)
                elif below:
                    dy = max(0, cy1 - ay2)
                    cost = dy + (h_dist * 1.5 if h_overlap > 0 else h_dist * 4.0)
                elif above:
                    dy = max(0, ay1 - cy2)
                    cost = dy + (h_dist * 1.5 if h_overlap > 0 else h_dist * 4.0)
                else:
                    cost = 0.0

                spatial_candidates.append((cost, cand))

            if not spatial_candidates:
                logger.warning(f"No candidate '{query_text}' satisfied spatial relationship relative to '{anchor_target}'.")
                self.last_match = {"found": False, "query": query_text, "score": 0.0, "matched_text": "", "healed": False}
                return None

            spatial_candidates.sort(key=lambda x: x[0])
            target_idx = index if index is not None else 0
            if target_idx < 0 or target_idx >= len(spatial_candidates):
                logger.warning(f"Index {target_idx} out of range for spatial matches (found {len(spatial_candidates)}).")
                self.last_match = {"found": False, "query": query_text, "score": 0.0, "matched_text": "", "healed": False}
                return None

            best_match = spatial_candidates[target_idx][1]
            logger.info(f"Spatial match successful: found '{best_match['item']['text']}' relative to '{anchor_target}' (cost={spatial_candidates[target_idx][0]:.1f})")

        elif candidates and index is not None:
            # Ordinal index among all candidates in natural reading order
            sorted_cands = sorted(candidates, key=lambda c: (c["box"][1] // 20, c["box"][0]))
            if index < 0 or index >= len(sorted_cands):
                logger.warning(f"Index {index} out of range (found {len(sorted_cands)} matches).")
                self.last_match = {"found": False, "query": query_text, "score": 0.0, "matched_text": "", "healed": False}
                return None
            best_match = sorted_cands[index]
            logger.info(f"Selected match at index {index}: '{best_match['item']['text']}'")

        elif candidates:
            # Standard match: highest score, tie-break by reading order
            candidates.sort(key=lambda c: (-c["score"], c["box"][1] // 20, c["box"][0]))
            best_match = candidates[0]

        if not best_match:
            logger.warning(f"No OCR text match found for query: '{query_text}'. Trying class label fallback...")
            
            # --- Fallback: Check if query matches any YOLO or OpenCV class label ---
            # ONLY apply class label fallback if the query itself is a class description (e.g. "input_field", "button", "ui_element"), 
            # to prevent a specific text query (like "Google 商店") from matching a general YOLO box.
            ui_class_patterns = [
                "input", "field", "button", "ui_element", "element", "select", "checkbox",
                "bar", "search", "box", "area", "form", "text", "label", "link", "tab",
                "dropdown", "toggle", "radio", "slider", "icon", "container", "panel"
            ]
            query_clean_lower = "".join(query_text.lower().split())
            is_class_query = any(pat in query_clean_lower for pat in ui_class_patterns)
            
            if is_class_query:
                # Shape-based heuristic: find elements that match the expected visual shape of the query type.
                # This handles the case where YOLO labels are numeric or generic ('ui_element'),
                # so we cannot rely on label text matching at all.
                img_raw = cv2.imread(img_path)
                if img_raw is not None:
                    img_h, img_w = img_raw.shape[:2]
                    ui_elements = self.detect_elements(img_path)
                    
                    # Keyword sets that indicate the user wants to interact with an input-like element.
                    # "fill" and "type" are action words the user might accidentally use as targets.
                    input_keywords  = {
                        "search", "bar", "box", "input", "text", "form", "area", "field",
                        "fill", "type", "enter", "textarea", "query", "keyword"
                    }
                    button_keywords = {
                        "button", "btn", "submit", "ok", "cancel", "click", "press", "link",
                        "tab", "action", "go"
                    }
                    
                    query_words = set(query_clean_lower.replace("_", " ").split())
                    wants_input  = bool(query_words & input_keywords)
                    wants_button = bool(query_words & button_keywords)
                    
                    # If query is ambiguous (neither input nor button), default to input
                    if not wants_input and not wants_button:
                        wants_input = True
                    
                    best_shape_match = None
                    best_shape_score = -1
                    
                    for elem in ui_elements:
                        box = elem["box"]
                        w = box[2] - box[0]
                        h = box[3] - box[1]
                        if h == 0:
                            continue
                        ar = w / h  # Aspect ratio
                        cx = (box[0] + box[2]) / 2
                        cy = (box[1] + box[3]) / 2
                        cy_ratio = cy / img_h
                        
                        score = 0
                        
                        if wants_input:
                            # Input fields: wide & horizontal (AR > 3)
                            if ar >= 3:
                                score += int(min(ar, 20))   # Wider = more likely to be an input bar
                            if ar >= 5:
                                score += 10                  # Extra bonus for very wide elements
                            # Centered horizontally (Google search bar is centred)
                            center_dist = abs(cx / img_w - 0.5)
                            if center_dist < 0.25:
                                score += 10
                            elif center_dist < 0.4:
                                score += 4
                            # PREFER elements in the middle vertical range (20-75% of page height)
                            # PENALISE top navigation bars (< 12% height) which are wider but wrong
                            if 0.20 <= cy_ratio <= 0.75:
                                score += 12   # Strong bonus: this is where search boxes live
                            elif 0.12 <= cy_ratio < 0.20:
                                score += 4
                            elif cy_ratio < 0.12:
                                score -= 8    # Penalty: very likely a nav bar, not an input
                            elif cy_ratio > 0.85:
                                score -= 4    # Penalty: footer area
                            # Prefer elements with reasonable height (not too thin like nav links)
                            elem_h = h
                            if 25 <= elem_h <= 80:
                                score += 6
                        
                        if wants_button:
                            # Buttons: small to medium, roughly square-ish
                            if 0.5 <= ar <= 4:
                                score += 10
                            # Buttons can be anywhere, slight preference for center
                            if abs(cx / img_w - 0.5) < 0.4:
                                score += 3
                        
                        if score > best_shape_score:
                            best_shape_score = score
                            best_shape_match = elem
                    
                    if best_shape_match and best_shape_score > 0:
                        elem_box = best_shape_match["box"]
                        elem_center = ((elem_box[0] + elem_box[2]) // 2, (elem_box[1] + elem_box[3]) // 2)
                        logger.info(f"Shape-heuristic fallback: matched a '{('input' if wants_input else 'button')}-like' element at {elem_box} (score={best_shape_score}) for query '{query_text}'")
                        
                        self.last_match = {
                            "found": True,
                            "query": query_text,
                            "score": 1.0,
                            "matched_text": f"shape:{best_shape_match['label']}",
                            "healed": True
                        }
                        return elem_center
            
            self.last_match = {
                "found": False,
                "query": query_text,
                "score": 0.0,
                "matched_text": "",
                "healed": False
            }
            return None
        
        matched_item = best_match["item"]
        best_score = best_match["score"]
        logger.info(f"Matched text '{matched_item['text']}' for query '{query_text}' with score {best_score:.2f}")
        # Self-healing is true when the match isn't an exact match (score < 1.0) but satisfies fuzzy threshold
        healed = best_score < 1.0
        self.last_match = {
            "found": True,
            "query": query_text,
            "score": best_score,
            "matched_text": matched_item["text"],
            "healed": healed,
            "spatial": {
                "right_of": right_of,
                "left_of": left_of,
                "below": below,
                "above": above,
                "index": index
            }
        }
        
        # 2. Get the bounding box of matched text
        txt_box = matched_item["box"] # [x_min, y_min, x_max, y_max]
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

    def get_closest_candidates(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Return the top_k OCR text items on the screen closest in similarity to query_text.
        Used for smart debugging, failure diagnosis, and auto-suggest.
        """
        if not hasattr(self, 'last_ocr_results') or not self.last_ocr_results:
            return []
        
        scored = []
        seen = set()
        for item in self.last_ocr_results:
            txt = item["text"].strip()
            if not txt or txt in seen:
                continue
            seen.add(txt)
            score = self._compute_text_score(query_text, txt)
            scored.append({
                "text": txt,
                "score": round(score, 2),
                "box": item["box"],
                "confidence": item.get("confidence", 1.0)
            })
        
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def generate_visual_debug_diff(self, img_path: str, query_text: str, output_path: str) -> str:
        """
        Generate an annotated debug screenshot highlighting detected OCR boxes and top candidates.
        Provides instant visual feedback on why an element was not matched.
        """
        img = cv2.imread(img_path)
        if img is None:
            return img_path

        candidates = self.get_closest_candidates(query_text, top_k=3)
        candidate_boxes = [c["box"] for c in candidates]

        # Draw all OCR text boxes in dim gray
        for item in getattr(self, 'last_ocr_results', []):
            box = item["box"]
            if box not in candidate_boxes:
                cv2.rectangle(img, (box[0], box[1]), (box[2], box[3]), (120, 120, 120), 1)

        # Highlight top closest candidates in Bright Amber / Orange
        for idx, cand in enumerate(candidates):
            box = cand["box"]
            # Amber outline
            cv2.rectangle(img, (box[0], box[1]), (box[2], box[3]), (0, 165, 255), 2)
            label = f"#{idx+1} {cand['text']} ({int(cand['score']*100)}%)"
            cv2.putText(img, label, (box[0], max(16, box[1] - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1, cv2.LINE_AA)

        # Draw top banner
        header = f"DEBUG: '{query_text}' not found. Closest: " + ", ".join([f"'{c['text']}' ({int(c['score']*100)}%)" for c in candidates])
        cv2.rectangle(img, (0, 0), (img.shape[1], 34), (30, 30, 40), -1)
        cv2.putText(img, header[:120], (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1, cv2.LINE_AA)

        cv2.imwrite(output_path, img)
        return output_path

