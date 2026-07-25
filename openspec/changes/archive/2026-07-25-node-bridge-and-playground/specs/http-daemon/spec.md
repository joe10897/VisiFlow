## ADDED Requirements

### Requirement: Local HTTP Vision Daemon Server
The system SHALL provide a local HTTP server that exposes endpoints for image object detection and OCR text matching.

#### Scenario: Match visual target via HTTP API
- **WHEN** a client sends a POST request to `/match` with a screenshot image and a query string
- **THEN** the server SHALL run VisiFlow detection locally and return JSON containing the target coordinates (x, y) and bounding box
