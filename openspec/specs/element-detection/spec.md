# element-detection Specification

## Purpose
TBD - created by archiving change visiflow-core. Update Purpose after archive.
## Requirements
### Requirement: Local UI Object Detection Inference
The system SHALL run object detection locally on a browser screenshot using a YOLO model, without uploading files to external APIs.

#### Scenario: Element detection on standard webpage screenshot
- **WHEN** the engine is initialized with a YOLO model and runs detection on a screenshot image
- **THEN** it SHALL return a list of detected bounding boxes, each containing coordinates (x_min, y_min, x_max, y_max), element type (e.g., "button", "input"), and confidence score

### Requirement: Model Initialization and Fallback
The system SHALL support loading custom YOLO models (.pt or .onnx format) and fall back to a default pre-trained web component detection model if none is specified.

#### Scenario: Fallback to default model
- **WHEN** the detection core is instantiated without a model path
- **THEN** it SHALL load the default pre-trained model automatically

