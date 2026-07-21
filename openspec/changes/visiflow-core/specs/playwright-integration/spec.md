## ADDED Requirements

### Requirement: Playwright Visual Action Execution
The system SHALL extend Playwright Page objects (or provide a wrapper) to support visual-driven operations like clicking and typing.

#### Scenario: Visual click on a button
- **WHEN** `page.visual_click("Submit")` is called
- **THEN** the system SHALL take a screenshot, run YOLO/OCR, find the center coordinates of the target button, and execute a native click at those coordinates

### Requirement: Playwright Visual Input Field Filling
The system SHALL support filling input fields by identifying the field visually.

#### Scenario: Fill a text field labeled Username
- **WHEN** `page.visual_fill("Username", "admin")` is called
- **THEN** the system SHALL find the text input box associated with "Username", click it, and type "admin"

### Requirement: Playwright Visual Verification
The system SHALL support verifying the existence of visual elements on the page.

#### Scenario: Verify success message is visible
- **WHEN** `page.visual_wait_for("Success")` is called
- **THEN** the system SHALL wait until an element with text or label containing "Success" is visually detected
