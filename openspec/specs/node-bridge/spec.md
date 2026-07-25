# node-bridge Specification

## Purpose
TBD - created by archiving change node-bridge-and-playground. Update Purpose after archive.
## Requirements
### Requirement: Node.js Playwright Page Wrapper
The system SHALL provide a JavaScript/TypeScript module (`visiflow-js`) that wraps Playwright JS `Page` objects.

#### Scenario: Visual click in Node.js Playwright
- **WHEN** a Node.js script invokes `visipage.visualClick("Submit")`
- **THEN** it SHALL capture a screenshot, call the local VisiFlow HTTP daemon, and trigger a native Playwright mouse click at the returned coordinates

