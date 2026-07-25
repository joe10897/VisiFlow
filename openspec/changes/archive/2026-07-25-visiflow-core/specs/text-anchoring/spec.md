## ADDED Requirements

### Requirement: Local OCR Text Extraction
The system SHALL run a local OCR engine on browser screenshots or specific cropped element regions to extract text content and their bounding boxes.

#### Scenario: Extract text from buttons and inputs
- **WHEN** OCR is run on a screenshot
- **THEN** it SHALL return a list of text annotations, each containing the recognized text string and its bounding box coordinates

### Requirement: Semantic Element Anchoring
The system SHALL combine YOLO element coordinates and OCR text detections to find the element that matches a given query string (e.g., "Login", "Search").

#### Scenario: Find button by text label
- **WHEN** matching element with label "Submit"
- **THEN** it SHALL return the bounding box of the YOLO-detected button that contains or is adjacent to the text "Submit"

### Requirement: Fuzzy Text Matching
The system SHALL support fuzzy matching (e.g., Levenshtein distance or case-insensitive partial match) to align query text with OCR results.

#### Scenario: Match button with minor OCR misspelling
- **WHEN** user searches for "Login" but OCR detects "Log1n" or "login"
- **THEN** the system SHALL match the login button within acceptable similarity thresholds
