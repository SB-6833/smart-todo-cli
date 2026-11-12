# Smart Todo CLI Implementation Tasks

**Status**: Phases 1–3 (T001–T015) complete; later phases have not started. Persistence tests and documentation are in place; service and CLI features remain unimplemented.
**Source of truth**: [spec.md](./spec.md), the project [constitution](../../.specify/memory/constitution.md), and [plan.md](./plan.md).

## Conventions

- Complete tasks in phase order unless the dependency line explicitly allows parallel work.
- `[P]` marks tasks that can be worked on in parallel with other `[P]` tasks in the same phase, provided their listed dependencies are complete.
- `[US1]` through `[US4]` identify the specification user story addressed. A task may support more than one story.
- Tests listed here are future work items. They must be independent pytest tests of observable behavior, use fixed expected values, and use temporary data rather than the real `tasks.json`.
- Do not change the specification's acceptance criteria, disable or delete tests, or bypass a validation gate to make a run pass.

## Phase 1: Project Setup

**Goal**: Establish a reproducible Python 3.11+ project and development environment before application implementation.

- [x] T001 Select compatible exact versions of pytest, Ruff, and Bandit; record the decision in `research.md` and pin those versions in `requirements-dev.txt`. Keep runtime dependencies standard-library only.
  - Depends on: None.
- [x] T002 [P] Create the planned package and directory structure: `smart_todo/`, `tests/unit/`, `tests/cli/`, `tests/contract/`, and `scripts/`.
  - Depends on: T001.
- [x] T003 [P] Create `pyproject.toml` with Python 3.11 target/configuration and the agreed pytest and Ruff settings. Keep validation commands non-mutating; do not use Ruff autofix in the harness.
  - Depends on: T001.
- [x] T004 [P] Verify the project-root `.gitignore` excludes `/tasks.json` and the planned Python/test/tool caches. Add only missing entries; do not create or commit real task data.
  - Depends on: T001.
- [x] T005 Install the pinned development tools and verify Python is 3.11 or newer and pytest, Ruff, and Bandit are available at the recorded versions.
  - Depends on: T001–T004.

## Phase 2: Models, Validation, and JSON Storage

**Goal**: Establish validated task data and safe persistence before building user operations.

- [x] T006 [P] Specify and write `tests/unit/test_validation.py` cases for whitespace-only titles, title trimming, tag trimming and case-insensitive deduplication, allowed priorities/statuses, and invalid values. Expected results must be literal test expectations, not calculated with production helpers.
  - Depends on: T005.
- [x] T007 Implement `Task` and priority/status representations in `smart_todo/models.py`, plus focused reusable input and record validation in `smart_todo/validation.py`.
  - Depends on: T006.
- [x] T008 [P] Specify and write `tests/unit/test_storage.py` and `tests/contract/test_task_file_contract.py` cases for the JSON envelope, round trips, missing files, unsupported schema or malformed records, duplicate/invalid IDs, read/write failures, and preservation of the prior file on failure.
  - Depends on: T005.
- [x] T009 Implement `smart_todo/storage.py`: resolve the project-level `tasks.json` independently of the current working directory; handle a missing file as an empty first run; validate the version-1 object with `schema_version`, `next_id`, and `tasks`; and report malformed, unsupported, or unreadable existing data without replacing it.
  - Depends on: T007, T008.
- [x] T010 Implement safe complete-snapshot persistence using a temporary file beside `tasks.json` and replace-after-success behavior. Preserve the previous valid file on write failure, expose the failure, and allow tests to inject a temporary path.
  - Depends on: T009.
- [x] T011 Run the focused validation and storage pytest cases using temporary directories; resolve implementation failures without weakening the tests or requirements.
  - Depends on: T006–T010.

## Phase 3: User Story 3 — Continue After Restart (P1)

**Goal**: Prove persistence and data-preservation behavior independently of interactive CLI testing.

- [x] T012 [US3] Extend unit and contract coverage for successful add/update/delete persistence, task ID/detail round trips after reload, missing-file startup, and project-root data location when launched from another working directory.
  - Depends on: T011.
- [x] T013 [US3] Add isolated failure tests for unreadable/malformed existing data and simulated save failures. Assert explicit errors and unchanged original data; verify the tests never access the real project `tasks.json`.
  - Depends on: T011.
- [x] T014 [US3] Review and update applicable usage/design documentation to state the stable data-file location, local-only persistence, and one-running-instance limitation without implying file locking.
  - Depends on: T009, T010.
- [x] T015 [US3] Run the storage-only unit and task-file contract cases available at this phase using temporary directories; defer service/restart execution until the service and CLI tasks are complete.
  - Depends on: T012–T014.

## Phase 4: User Story 1 — Manage Tasks (P1)

**Goal**: Implement and independently test add, view, update, and delete behavior.

- [x] T016 [P] [US1] Specify and write `tests/unit/test_service.py` coverage for adding tasks with unique positive IDs, Medium/Pending defaults, viewing all task fields, updating title/priority/tags/status without changing ID, deleting by ID, rejecting invalid values/IDs, and not committing state when persistence fails.
  - Depends on: T015.
- [x] T017 [P] [US1, US4] Specify and write `tests/cli/test_cli.py` coverage for a numbered menu, visible task fields, add/view/update/delete prompts, delete confirmation and cancellation, invalid menu choices/IDs/values, and plain-language outcomes.
  - Depends on: T015.
- [x] T018 [US1] Implement `smart_todo/service.py` CRUD operations. Validate before mutation, preserve IDs on update, allocate sequential IDs from `next_id` without reuse after deletion, and publish a mutation only after storage succeeds.
  - Depends on: T016.
- [x] T019 [US1, US4] Implement the numbered menu, deterministic input/output boundary, prompts, confirmation, and user-facing messages in `smart_todo/cli.py`. Keep JSON access out of the CLI.
  - Depends on: T017, T018.
- [x] T020 [US1] Implement `smart_todo/__main__.py` as the module launch point and add contract coverage for `python -m smart_todo` startup and menu reachability.
  - Depends on: T019.
- [x] T021 [US1, US3, US4] Run independent unit, CLI, and contract pytest suites. Confirm a successful mutation is saved before success is reported and cancellation/invalid input leave task data unchanged.
  - Depends on: T020.

## Phase 5: User Story 2 — Find and Prioritize Tasks (P2)

**Goal**: Add exact tag filtering and stable priority sorting without changing saved task order.

- [x] T022 [P] [US2] Add independent service tests for one-tag exact matching with case-insensitive comparison, no-match results, High/Medium/Low ordering, and stable ordering among equal-priority tasks.
  - Depends on: T021.
- [x] T023 [P] [US2, US4] Add CLI/contract tests for filter and sort choices, displayed results, no-match feedback, invalid selections, and unchanged saved ordering.
  - Depends on: T021.
- [x] T024 [US2] Implement filtering and stable sorting in `smart_todo/service.py`. Treat both as read-only views that do not mutate persisted task order.
  - Depends on: T022.
- [x] T025 [US2, US4] Add the filter/sort menu flows and clear empty-result feedback in `smart_todo/cli.py`.
  - Depends on: T023, T024.
- [x] T026 [US2] Run the focused filter/sort tests and verify exact case-insensitive tag behavior and stable priority ties.
  - Depends on: T025.

## Phase 6: User Story 4 — Receive Clear Feedback (P1)

**Goal**: Verify plain-language success, error, and cancellation results across all supported operations.

- [x] T027 [US4] Complete independent CLI/contract tests for feedback after every operation, including invalid priorities/statuses, nonexistent IDs, empty lists, no matching tags, failed reads/writes, and cancelled deletion. Assert failed/cancelled operations do not alter task state or saved data.
  - Depends on: T021, T026.
- [x] T028 [US4] Refine CLI error mapping and messages so expected user/data/file errors are clear, unexpected errors are not silently swallowed, and diagnostic output does not disclose task contents or sensitive data.
  - Depends on: T027.
- [x] T029 [US1, US2, US3, US4] Audit independent pytest coverage against every FR, edge case, and SC in `spec.md`. Correct missing coverage without changing acceptance criteria or using production helpers to calculate expected outcomes.
  - Depends on: T028.
- [x] T030 [US1, US2, US3, US4] Run independent unit and CLI/contract pytest suites using temporary directories; confirm all supported operations are reachable from the visible menu and all accepted behavior is covered.
  - Depends on: T029.

## Phase 7: Deterministic Validation, Repair, and Human Review

**Goal**: Preserve initial evidence, run every required gate, repair only from actual failures, and leave final acceptance to a human.

- [ ] T031 Freeze the accepted test set, Python/tool versions, configuration, working directory, synthetic inputs, commands, and fixed expected outcomes before baseline validation. Record the expected result for each gate.
  - Depends on: T001, T030.
- [ ] T032 Implement `scripts/validate.py` to run the fixed checks and capture exact arguments, working directory, stdout, stderr, exit codes, and JSON/JUnit reports. It must fail explicitly when a tool/check/report is missing or cannot run, and must write expected-versus-observed results for every check.
  - Depends on: T031.
- [ ] T033 Implement and verify the harness's initial snapshot behavior: before any repair, preserve the generated implementation, tests, and validation configuration under a unique `validation-artifacts/<run-id>/initial/` path and create a SHA-256 manifest. Never overwrite an existing snapshot.
  - Depends on: T032.
- [ ] T034 Run initial validation and preserve the `before-repair/` evidence for each fixed gate:
  - `python -m compileall -q smart_todo tests`
  - `ruff check --output-format json smart_todo tests`
  - `bandit -r smart_todo --format json`
  - `python -m pytest -q tests/unit --junitxml=RUN_DIR/pytest-unit.xml`
  - `python -m pytest -q tests/cli tests/contract --junitxml=RUN_DIR/pytest-cli-contract.xml`
  - Record the observed results from the actual run; do not predetermine or invent them.
  - Depends on: T033.
- [ ] T035 If and only if a gate fails, give the coding agent the actual command, tool versions, exit code, captured output, failing test IDs/reports, and initial file hashes; repair the implementation from that evidence. Keep tests, expected outcomes, configuration, and check set unchanged. If no gate fails, record that no repair was needed rather than inventing failure evidence.
  - Depends on: T034.
- [ ] T036 After repair, rerun the exact same checks with the same versions, configuration, test paths, working directory, and synthetic inputs; only the phase-specific output directory may differ. Save reports in `after-repair/`. If no repair was needed, perform the planned final confirmation run and label the repair phase accordingly.
  - Depends on: T035.
- [ ] T037 Compare initial and final expected-versus-observed results side by side, including exit codes, lint/security findings, pytest collection/pass/fail/skip counts, and report references. Identify unresolved failures without marking them as passed or weakening any gate.
  - Depends on: T036.
- [ ] T038 Perform the manual acceptance walkthrough from `quickstart.md`, review preserved evidence and the final changes, then record a human **ACCEPT** or **REJECT** decision. Automated success alone is not final acceptance.
  - Depends on: T037.

## Dependencies and Parallel Work

- Setup: T002, T003, and T004 may proceed in parallel after T001; T005 waits for all three.
- Foundations: T006 and T008 may be prepared in parallel after T005. T007 follows T006; storage implementation T009–T010 follows both validation/model work and storage tests.
- US1: service tests T016 and CLI tests T017 may be prepared in parallel after persistence is validated. The service implementation precedes CLI integration.
- US2: service tests T022 and CLI/contract tests T023 may be prepared in parallel after US1. Implement service filtering/sorting before wiring its CLI flow.
- Validation and review are sequential: preserve snapshot before the initial run, use actual failures for conditional repair, rerun the identical check set, compare evidence, and obtain human review last.

## Acceptance-Criteria Traceability

| Story / criteria | Planned implementation tasks | Independent test / validation tasks |
|---|---|---|
| US1; FR-001 through FR-009; SC-001 | T018–T020 | T016–T017, T020–T021, T029–T030, T038 |
| US2; FR-010 and FR-011; SC-002 | T024–T025 | T022–T023, T026, T029–T030, T038 |
| US3; FR-012 and FR-013; SC-003 | T009–T010, T014 | T008, T012–T015, T021, T029–T030, T038 |
| US4; FR-014 and FR-015; SC-004 and SC-005 | T019, T025, T028 | T017, T023, T027, T029–T030, T034–T038 |
| Edge cases: blank titles, invalid IDs/menu/priority/status, empty list, no-match tag, tag normalization, stable ties, missing/malformed/unreadable/unsavable file | T007, T009–T010, T018–T019, T024–T025, T028 | T006, T008, T016–T017, T022–T023, T027, T029–T030 |
