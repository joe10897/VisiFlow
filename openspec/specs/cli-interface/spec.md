# cli-interface Specification

## Purpose
TBD - created by archiving change node-bridge-and-playground. Update Purpose after archive.
## Requirements
### Requirement: Command Line Interface Entrypoint
The system SHALL provide a CLI command `visiflow` with subcommands `server`, `ui`, and `match`.

#### Scenario: Launch daemon server via CLI
- **WHEN** user executes `visiflow server`
- **THEN** it SHALL start the HTTP daemon server on port 8000

