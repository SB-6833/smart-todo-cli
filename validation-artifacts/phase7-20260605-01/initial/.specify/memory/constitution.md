<!--
Sync Impact Report
Version change: unratified scaffold -> 1.0.0 (initial ratification)
Modified principles:
- Principle 1 placeholder -> I. Simplicity, Modularity, and Learning
- Principle 2 placeholder -> II. Python and JSON Persistence
- Principle 3 placeholder -> III. Readable, Maintainable Practices
- Principle 4 placeholder -> IV. Validated Inputs and Graceful Errors
- Principle 5 placeholder -> V. Privacy and Secret Protection
- Added VI. Acceptance Integrity
- Added VII. Independent Automated Validation
- Added VIII. Existing Data Preservation
- Added IX. Documented Design Decisions
- Added X. Human Review
Added sections: Project Constraints; Development Workflow
Removed sections: Template examples and unresolved placeholder text
Follow-up TODOs: None
-->
# Smart Todo Constitution

## Core Principles

### I. Simplicity, Modularity, and Learning
The application MUST remain simple, modular, and beginner-friendly. Use the smallest clear design that satisfies the accepted requirements and avoid unnecessary complexity.

### II. Python and JSON Persistence
The application MUST use Python and persist task data in a local JSON file. A successful change MUST remain available after restart.

### III. Readable, Maintainable Practices
Code MUST use clear names, focused units of behavior, and consistent formatting. Non-obvious design decisions MUST be documented in project documentation.

### IV. Validated Inputs and Graceful Errors
All user input and persisted task data MUST be validated. Errors MUST be reported clearly; failures MUST NOT be silently ignored or presented as success.

### V. Privacy and Secret Protection
Secrets and sensitive information MUST NOT be exposed in source control, logs, or user-facing error messages. Task data MUST remain local and MUST NOT be sent to external services.

### VI. Acceptance Integrity
Acceptance criteria MUST NOT be weakened, bypassed, or removed to make validation pass. Tests MUST NOT be deleted or disabled for that purpose.

### VII. Independent Automated Validation
Every application change MUST be validated by independent automated tests that check observable behavior against the accepted requirements. Passing tests do not replace human review.

### VIII. Existing Data Preservation
Application updates MUST preserve existing valid task data. Read, validation, or write failures MUST NOT silently replace saved data with empty or default data.

### IX. Documented Design Decisions
Important design decisions and their rationale MUST be recorded in the relevant specification or project documentation before they are treated as settled.

### X. Human Review
A human MUST review the requirements, changes, and validation results before final acceptance. Automated checks alone are not approval.

## Project Constraints

- Task persistence is local and file-based in JSON; adding a database, remote service, or network sync requires an approved specification change.
- Error handling and user feedback must be understandable to a beginner and must not expose sensitive details.
- New behavior must stay within the approved feature scope unless the requirements are revised and reviewed.

## Development Workflow

- Before implementation, confirm the applicable specification and acceptance criteria.
- For each application change, add or update independent automated tests for the behavior and run the relevant validation.
- Report validation failures honestly; do not make results pass by changing expected outcomes or removing tests.
- Record significant design decisions in the specification or project documentation.
- Request human review of the completed changes and test results before final acceptance.

## Governance

This constitution governs Smart Todo requirements, plans, implementation, and review. Every change MUST comply with these principles. A proposed exception or amendment requires a documented rationale and human review before it is applied. Reviewers MUST check both principle compliance and test evidence. The constitution uses semantic versioning: MAJOR for incompatible principle or governance changes, MINOR for new principles or material expansions, and PATCH for clarifications that do not alter intent.

**Version**: 1.0.0 | **Ratified**: 2026-11-11 | **Last Amended**: 2026-11-11
