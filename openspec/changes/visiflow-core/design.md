## Context

VisiFlow is designed to replace DOM-based selector strategies in Playwright and Selenium with a visual-driven selector engine. Rather than querying XPath or CSS selectors, VisiFlow captures page screenshots, runs a local object detection model (YOLOv8/11/etc.) to identify UI elements (buttons, inputs, dropdowns), runs local OCR (EasyOCR) to read the labels on those elements, and performs fuzzy semantic matching to find the correct coordinates for interaction.

## Goals / Non-Goals

**Goals:**
- Provide a zero-cloud-dependency, 100% local computer vision automation pipeline.
- Keep execution time under 300ms per visual operation (YOLO inference + OCR processing).
- Provide drop-in Python wrappers for Playwright and Selenium.
- Support finding elements via text labels (fuzzy matching) and basic icon/element descriptions.

**Non-Goals:**
- Creating a new browser automation protocol (we use Playwright/Selenium under the hood).
- Training a 100% perfect model in this phase; we will build the core engine capable of loading any standard YOLO weight/format, using a pre-trained model as a baseline.
- Supporting mobile/desktop native testing (this phase focuses strictly on web/HTML screenshots).

## Decisions

### Decision 1: Language and Computer Vision Ecosystem
We will use **Python 3.12** for the implementation.
- **Rationale**: Python has the most mature local CV libraries: `ultralytics` for YOLO models, and `easyocr` (built on PyTorch) for OCR. Playwright and Selenium both have native Python packages.
- **Alternatives Considered**: Node.js/TypeScript. However, running YOLO (via ONNX runtime) and OCR in Node.js requires binding native C++ modules, which is fragile to distribute and configure on cross-platform developer machines.

### Decision 2: OCR Strategy - Full Screen OCR vs. Cropped Image OCR
We will run **EasyOCR on the full screenshot once**, then perform coordinate intersection with YOLO-detected element boxes.
- **Rationale**: OCR inference is typically slower than object detection. Running OCR once on the entire image and doing geometric mapping in memory takes ~200ms. Cropping 20-30 buttons/inputs and running OCR on each cropped image individually would take >2 seconds, which violates our speed goal.
- **Alternatives Considered**: Cropped OCR. Rejected due to latency.

### Decision 3: YOLO Integration and Fallback
We will use `ultralytics` to load YOLOv8/v11/v26 `.pt` or `.onnx` models.
- **Rationale**: Ultralytics is the standard for YOLO. It automatically handles downloading weight files, uses PyTorch for GPU acceleration if available, and falls back to CPU seamlessly.
- **Fallback**: If YOLO detection finds nothing or weights are not loaded, we will implement a hybrid CV fallback using OpenCV contours (hierarchical shape analysis) to detect candidate interactive bounding boxes.

## Risks / Trade-offs

- **[Risk] High CPU/Memory usage by PyTorch/EasyOCR** → *Mitigation*: We will initialize OCR and YOLO lazily and keep their models warm in memory. We will also default to ultra-lightweight models (e.g. `yolov8n.pt` or `yolo11n.pt`).
- **[Risk] OCR Misreadings (e.g., "Login" read as "Log1n")** → *Mitigation*: We will use Levenshtein distance fuzzy string matching to match query strings with extracted text.
- **[Risk] High-resolution screen coordinates vs. Browser viewport coordinates** → *Mitigation*: Playwright and Selenium screenshots can be larger due to device pixel ratio (DPR). We will compute the scaling factor `(viewport_width / screenshot_width)` and scale bounding box coordinates before simulating clicks.
