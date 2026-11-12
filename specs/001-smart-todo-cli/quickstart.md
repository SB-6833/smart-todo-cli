# Smart Todo Validation Quickstart

**Status**: CRUD, tag filtering, priority sorting, and deterministic validation are implemented. The final acceptance decision remains pending human review.

## Prerequisites

- Python 3.11 or newer.
- The pinned development tools: pytest, Ruff, and Bandit, installed from the planned `requirements-dev.txt`.
- Run module/test commands from the `smart-todo` project directory for Python module discovery. The task-data path remains project-root-based even when the process working directory differs.
- Application runtime dependencies remain standard-library only.

## Run the Application

Launch the numbered terminal menu with:

```text
python -m smart_todo
```

The application resolves `tasks.json` from its stable project-level location, not the terminal's current working directory. Task data stays local; v1 does not sync it to a remote service. Run only one application instance at a time: simultaneous instances are unsupported, and no file locking is used. Do not use real or sensitive task content for validation. The root `.gitignore` excludes `/tasks.json`.

## Run the Deterministic Validation Checks

The harness runs these approved checks for the initial implementation and final confirmation. Each check records its command, stdout, stderr, exit code, and report. `RUN_DIR` is a unique output directory for the phase.

```text
python -m compileall -q smart_todo tests
ruff check --output-format json smart_todo tests
bandit -r smart_todo --format json
python -m pytest -q tests/unit --junitxml=RUN_DIR/pytest-unit.xml
python -m pytest -q tests/cli tests/contract --junitxml=RUN_DIR/pytest-cli-contract.xml
```

Expected: every command exits successfully, compilation and lint have no errors/findings, Bandit has no findings, and both pytest runs collect tests with no failures, errors, skips, or xfails. The harness records actual observed results for each run. Do not weaken acceptance criteria or delete/bypass tests to make checks pass.

Run the harness from the project directory with a new, path-safe run ID:

```text
python scripts/validate.py --run-id <UNIQUE_RUN_ID> --phase initial
python scripts/validate.py --run-id <UNIQUE_RUN_ID> --phase after-repair
```

The initial phase preserves a snapshot and hash manifest of the generated implementation, tests, and validation configuration before any repair. The run ID must not already exist. A failed run's actual command output, reports, and baseline hashes are preserved for evidence-based repair; do not repair from guessed or fabricated failures. The after-repair phase re-runs the same checks with the same tool versions, configuration, working directory, and test inputs. It produces a side-by-side comparison. Evidence is stored under `validation-artifacts/<UNIQUE_RUN_ID>/`; the harness does not overwrite existing evidence or make the human ACCEPT/REJECT decision.

## Full Acceptance Walkthrough

1. Start with no `tasks.json`; confirm the menu opens and the empty list is described clearly.
2. Add a task with a title, High priority, and a tag. Confirm it receives an ID and Pending status.
3. Add a second task with the same tag but a different case and a lower priority.
4. View all tasks; confirm ID, title, priority, tags, and status are visible.
5. Update the first task's status to In Progress, then Completed; confirm both changes. Update it again to Pending to verify transitions are not one-way.
6. Filter by the tag using different letter case; confirm both matching tasks appear. Use a missing tag and confirm a clear no-match message.
7. Sort by priority; confirm High precedes lower priorities and equal-priority tasks retain their previous relative order.
8. Attempt a blank title, an invalid menu choice, and a nonexistent ID; confirm clear errors and unchanged task data.
9. Begin deleting a task and cancel; confirm it remains. Confirm deletion in a separate attempt and confirm it is removed.
10. Exit and start a fresh application instance; confirm all successful additions/updates/deletions and all remaining task fields persist.
11. In pytest temporary directories, verify malformed JSON and simulated read/write failures are reported without replacing existing data. Confirm test execution does not modify the real project-root `tasks.json`.
12. Start the app from a working directory other than the project root (using an isolated temporary project copy); confirm its data file remains at that copy's project root.
13. Confirm that starting a second instance is documented as unsupported; no lock-file or concurrent-writer behavior is expected in v1.

## Expected Outcome

Every step produces the expected visible result. Successful mutations survive restart; invalid and cancelled operations leave saved data unchanged. Independent pytest unit and CLI/contract suites cover these outcomes. A human makes the final acceptance decision from the preserved baseline and actual validation evidence.
