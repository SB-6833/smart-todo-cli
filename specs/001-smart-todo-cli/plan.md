# Implementation Plan: Smart Todo CLI

**Branch**: `001-smart-todo-cli` (feature identifier; no Git branch exists) | **Date**: 2026-11-11 | **Spec**: [spec.md](./spec.md)

**Input**: Approved requirements in [spec.md](./spec.md) and project principles in [constitution.md](../../.specify/memory/constitution.md)

## Summary

Build a single-user Python 3.11+ terminal application with a small set of focused modules:
the CLI handles prompts and display, a task service validates and performs operations,
and a JSON store owns loading and saving `tasks.json` at a stable project-level location.
The runtime uses the standard library; pytest, Ruff, and Bandit are development tools.
Mutations are validated and saved before success is reported; file errors must never be
treated as an empty task list or silently replace existing data.

The plan follows the agreed requirements without changing them. The confirmed
technical decisions are recorded in [research.md](./research.md); exact development
tool versions must be pinned before the first harness run.

## Technical Context

**Language/Version**: Python 3.11 or newer.

**Primary Dependencies**: Runtime: Python standard library. Development: pytest, Ruff, and Bandit; exact versions will be pinned before baseline validation.

**Storage**: Versioned JSON object in `tasks.json` at the application project root, resolved from the package location rather than the current working directory.

**Testing**: Independent pytest unit, CLI, and contract suites using temporary directories; Python compilation, Ruff linting, and Bandit scanning.

**Target Platform**: Interactive terminal; develop first on Windows while keeping file and console behavior portable.

**Project Type**: Single Python command-line application.

**Performance Goals**: No response-time or maximum-task-count target is defined in the specification; optimize for a personal task list rather than adding premature performance machinery.

**Constraints**: No network services; validate user input and loaded records; preserve valid saved data; do not expose secrets or task contents in diagnostics; exclude `/tasks.json` from Git; support one application instance at a time without file locking; report operation outcomes in plain language.

**Scale/Scope**: One local task list for one user. Accounts, collaboration, due dates, reminders, and automated recommendations are out of scope.

## Constitution Check

### Before Phase 0

- **Simplicity and modularity — PASS**: One package with clear responsibilities; no framework or plugin architecture.
- **Python and JSON persistence — PASS**: Python application and local `tasks.json` are the proposed design.
- **Readable and maintainable practices — PASS**: Small, named modules and documented choices are part of the design.
- **Validation and error handling — PASS**: Inputs and persisted records are validated; expected errors are surfaced without success-shaped fallbacks.
- **Privacy — PASS**: No external services; task data is local, and errors/logging must not expose sensitive content.
- **Acceptance integrity and testing — PASS**: Independent tests cover approved behavior; criteria and tests are not weakened to make checks pass.
- **Data preservation — PASS**: Missing files and invalid existing files have distinct handling; writes use a replace-after-success strategy.
- **Documentation and human review — PASS**: Decisions are recorded here and in the design artifacts; final acceptance remains a human decision.

No constitution violations require an exception.

## Proposed Architecture and Responsibilities

### Application flow

1. `python -m smart_todo` starts the CLI and resolves `tasks.json` from the package/project location, independent of the terminal's current working directory. With the proposed package layout, derive it as `Path(__file__).resolve().parents[1] / "tasks.json"`.
2. The store loads and validates the JSON file. A missing file means an empty task list; an existing unreadable or invalid file produces a clear error and is not overwritten.
3. The CLI presents the numbered menu and gathers user choices.
4. The service validates and applies task operations, using the model and validation helpers.
5. For a mutation, the store writes the candidate state safely. The service publishes the new in-memory state and the CLI reports success only after persistence succeeds.
6. Read-only operations display results without changing the saved task order or contents.

### Modules

- `smart_todo/__main__.py`: Small launch point that calls the CLI entry function.
- `smart_todo/cli.py`: Numbered menu, prompts, confirmation, filtering/sorting selection, display formatting, and user-safe outcome messages. It does not read or write JSON directly.
- `smart_todo/models.py`: `Task`, priority and status value definitions, and conversion between a task and its JSON-compatible fields.
- `smart_todo/validation.py`: Reusable normalization and validation for titles, tags, priorities, statuses, IDs, and loaded record shapes.
- `smart_todo/service.py`: Add, view, update, delete, filter, and sort behavior; coordinates validation and persistence without presentation logic.
- `smart_todo/storage.py`: Resolves/accepts the stable project-level task file path, loads the versioned JSON object, validates its schema, and safely saves a complete task snapshot.

Keep the modules directly connected; do not add a generic repository framework or extra layers unless later evidence justifies them. Allow the store path and CLI I/O to be supplied by tests so tests can use isolated temporary files and deterministic input/output.

Only one Smart Todo application instance may run at a time. Launching a second instance is unsupported; v1 does not implement file locking or concurrent-writer merge behavior. Document this limitation for users.

## Task Operations

- **Add**: Trim and reject an empty title; normalize and deduplicate tags; assign an ID; default priority to Medium and status to Pending; persist before reporting success.
- **View**: Display ID, title, priority, tags, and status. Explain clearly when there are no tasks.
- **Update**: Select by ID, choose a field to edit, validate the proposed value, preserve the ID, and persist the updated task before reporting success.
- **Delete**: Select by ID, ask for confirmation, and persist removal only after confirmation. A cancellation leaves both memory and disk unchanged.
- **Filter**: Match one exact tag while ignoring case; show a clear empty-result message.
- **Sort**: Display High, Medium, then Low; preserve relative order for tasks with equal priority. Sorting is a view operation and does not reorder saved data.
- **Status changes**: Offer Pending, In Progress, and Completed; any status may transition to any other status.
- **Feedback**: Every completed, failed, or cancelled menu operation receives a plain-language message. Invalid input does not mutate task state.

## Validation and Error Handling

- Validate at the input boundary and again when loading persisted records; do not assume valid JSON necessarily contains valid task values.
- Normalize titles and tags by trimming surrounding whitespace. Reject blank titles; deduplicate tags case-insensitively as stated in the specification assumptions.
- Accept only the specified priority and status values. Present choices as numbered options and report invalid selections clearly.
- Use specific expected errors for invalid input, missing task IDs, malformed task data, and file access/save failures. The CLI handles those errors with concise messages; do not broadly swallow unexpected exceptions.
- A failed read must not initialize an empty list over an existing file. A failed write must not be reported as success or replace the last valid file.
- Do not print or log task contents, secrets, or sensitive details as part of error handling.

## Persistence and Data Preservation

- Resolve `tasks.json` from the application project root, never from the process current working directory. With the proposed package layout, derive it as `Path(__file__).resolve().parents[1] / "tasks.json"`.
- Treat a missing file as a first run. Treat malformed JSON, an invalid schema, and access errors as explicit failures; leave the original file untouched.
- Serialize a complete candidate snapshot using the approved version-1 JSON envelope (`schema_version`, `next_id`, `tasks`) to a temporary file in the same directory, close it successfully, then replace the target. Clean up the temporary file on failure. `next_id` advances only after a successful add and is never decremented, so deleted IDs are not reused.
- Save every successful add, update, and delete before presenting success. If saving fails, preserve the prior on-disk state and do not publish the mutation as committed in the running service.
- The project-root `.gitignore` excludes `/tasks.json`; do not add telemetry or external synchronization.
- Tests receive a temporary storage path and synthetic task data. CLI and restart tests must use an isolated temporary project/data directory; they must never read or write the user's real `tasks.json`.
- Run one application instance at a time. No file lock is proposed; simultaneous instances are unsupported and must be documented.

## Deterministic Harness Validation Strategy

The harness is planned as `scripts/validate.py` and runs a fixed sequence from the project root using the pinned Python and development-tool versions. It captures each command's exact arguments, working directory, start/end status, stdout, stderr, exit code, and report files. It writes one machine-readable run manifest and a human-readable comparison report under a unique `validation-artifacts/<run-id>/` directory. A run must fail explicitly if a tool is missing, a report cannot be written, or a check does not execute.

### Fixed Validation Checks

The commands below are the required check set. `RUN_DIR` is a unique output directory for the current phase; only report destinations vary between the initial and repaired phases. The check selection, tool versions, configuration, working directory, and synthetic test inputs remain the same.

| Check | Command | Expected result (fixed before run) | Observed result |
|---|---|---|---|
| Python syntax/compilation | `python -m compileall -q smart_todo tests` | Exit 0; no syntax/compile errors. | Captured verbatim per phase; no results exist yet. |
| Ruff lint | `ruff check --output-format json smart_todo tests` | Exit 0; no lint findings. | Captured stdout/stderr and JSON output per phase; no results exist yet. |
| Bandit security scan | `bandit -r smart_todo --format json` | Exit 0; no findings. Do not use `--exit-zero` or suppress findings to pass. | Captured stdout/stderr, exit code, and JSON report per phase; no results exist yet. |
| Independent pytest unit suite | `python -m pytest -q tests/unit --junitxml=RUN_DIR/pytest-unit.xml` | Exit 0; tests collected; zero failures, errors, skips, or xfails. | Captured output, exit code, collection/pass/fail counts, and JUnit report per phase; no results exist yet. |
| Independent pytest CLI/contract suites | `python -m pytest -q tests/cli tests/contract --junitxml=RUN_DIR/pytest-cli-contract.xml` | Exit 0; tests collected; zero failures, errors, skips, or xfails. | Captured output, exit code, collection/pass/fail counts, and JUnit report per phase; no results exist yet. |

For every check, the report records the expected result beside the observed exit code, stdout/stderr artifact references, findings or test counts, and pass/fail decision. Pytest's JUnit XML and the full process output are retained. The plan phase has not run these checks; no test results or failure evidence are being asserted here.

### Test Independence and Data Isolation

- Keep the acceptance test suite separate from the application code under repair. Use fixed expected values and assert user-visible behavior; tests must not call production helpers to calculate expected results.
- Use pytest's `tmp_path` or equivalent temporary directories for storage tests. Inject the temporary file path into the store/service.
- CLI/contract and restart tests use a temporary project copy or injected temporary store. Assert that tests do not touch the real project-root `tasks.json`.
- The initial approved acceptance tests and check commands are read-only during self-healing. Any proposed test correction requires human approval and preserves the previous test and its evidence. Never delete, skip, xfail, weaken, or bypass a failing acceptance test/check.

### Baseline, Self-Healing, and Comparison Protocol

1. Resolve and record Python, pytest, Ruff, and Bandit versions and the approved test/configuration set. Do not record the full environment or secrets.
2. Before any repair, preserve the first generated implementation, tests, and validation configuration in a unique `validation-artifacts/<run-id>/initial/` snapshot. Write a SHA-256 manifest for each preserved file. Never overwrite this snapshot; fail if the target already exists.
3. Run the fixed check set against that initial snapshot and save each check's stdout, stderr, exit code, JSON/JUnit report, and expected-versus-observed status in a `before-repair/` report directory.
4. If checks fail, provide the coding agent with the actual failure evidence: exact command, tool versions, exit code, captured stdout/stderr, pytest report/failing test IDs, Ruff or Bandit report, and baseline file hashes. Do not create, paraphrase as actual, or invent failure evidence.
5. Allow self-healing against the implementation while keeping the approved specification, acceptance tests, expected outcomes, tool configuration, and check set unchanged. Preserve all original evidence.
6. Run the exact same check set after repair, using the same versions, configuration, test paths, working directory, and synthetic data. Only the phase-specific report output directory differs. Save results in `after-repair/`.
7. Compare each before/after result side by side: expected result, observed exit code, findings, test collection/pass/fail/skip counts, and report references. Identify resolved and remaining failures without treating an initial failure as a pass.
8. A human makes the final **ACCEPT** or **REJECT** decision from the preserved baseline, actual reports, comparison, unchanged acceptance criteria, and final change review. Acceptance requires every expected gate to pass, no checks to be bypassed, all acceptance tests retained, and data-preservation behavior demonstrated. Automated success alone is not final acceptance.

## Acceptance Criteria Coverage

| Specification coverage | Planned modules/design | Independent validation |
|---|---|---|
| US1; FR-001–009; SC-001 | `cli.py`, `service.py`, `models.py`, `validation.py` | CRUD, defaults, ID stability, all status transitions, confirmation/cancellation, and visible task fields |
| US2; FR-010–011; SC-002 | `service.py`, `validation.py`, `cli.py` | Exact case-insensitive tag filter, no-match output, priority order, and stable equal-priority order |
| US3; FR-012–013; SC-003 | `storage.py`, `service.py` | Round-trip and fresh-process/reloaded-service checks; missing, malformed, unreadable, and failed-save cases |
| US4; FR-014–015; SC-004–005 | `cli.py`, `validation.py`, `service.py` | Success/error/cancellation messages; invalid input leaves task state and saved data unchanged; all actions reachable from menu |

No acceptance criterion is removed or weakened. The full criterion text remains in [spec.md](./spec.md).

## Remaining Harness Decision

The four technical decisions in the latest user direction are now fixed: Python 3.11+, pytest, the versioned JSON object with non-reused sequential positive integer IDs, and single-instance operation without file locking. The remaining setup item is to select and pin exact versions for pytest, Ruff, and Bandit before the baseline run. No validation has been run yet, so there are no observed results or failure artifacts to report.

## Constitution Check (After Phase 1 Design)

- **PASS**: The proposed package is small and beginner-oriented.
- **PASS**: It uses Python and JSON file persistence only.
- **PASS**: Validation and user-safe error handling are explicit.
- **PASS**: Candidate writes and read failures preserve existing valid data.
- **PASS**: Independent automated tests are mapped to every user story and functional requirement group.
- **PASS**: Security, design documentation, and human review are included.

No violations or complexity exceptions are proposed.

## Project Structure

### Documentation

```text
specs/001-smart-todo-cli/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── terminal-interface.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # Created later by /speckit-tasks
```

### Proposed application files

```text
smart-todo/
├── smart_todo/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── models.py
│   ├── validation.py
│   ├── service.py
│   └── storage.py
├── tests/
│   ├── unit/
│   │   ├── test_validation.py
│   │   ├── test_service.py
│   │   └── test_storage.py
│   ├── cli/
│   │   └── test_cli.py
│   └── contract/
│       ├── test_terminal_contract.py
│       └── test_task_file_contract.py
├── scripts/
│   └── validate.py           # Deterministic validation and evidence harness
├── requirements-dev.txt      # Pinned pytest, Ruff, and Bandit versions
├── pyproject.toml            # Ruff/pytest configuration
├── .gitignore                # Excludes local task data
└── tasks.json               # Local runtime data; do not commit
```

**Structure Decision**: Use one top-level `smart_todo` package and one `tests` directory. This avoids separate frontend/backend projects, packaging layers, and unnecessary dependencies while keeping CLI, business rules, validation, and persistence independently testable.

## Complexity Tracking

No constitution violations or extra architectural projects are proposed; no complexity exception is required.
