# Research: Smart Todo CLI

**Date**: 2026-11-11
**Scope**: Select and document a small, testable design for a local Python terminal application. Phase 2 models, validation, and storage are implemented; service and CLI work has not started.

## Decisions and Rationale

### Use Python's standard library for application runtime

- **Decision**: Use standard-library modules for JSON, paths/files, temporary files, and IDs. Use pytest, Ruff, and Bandit as pinned development tools.
- **Rationale**: The application is a local CLI with no network or third-party integration. Avoiding dependencies reduces setup burden for a beginner.
- **Alternatives considered**: A CLI framework is not required by the approved feature scope. Pytest, Ruff, and Bandit are explicit project validation requirements, not runtime dependencies.

### Separate CLI, task operations, validation, model, and storage

- **Decision**: Keep prompts/rendering in the CLI; task rules in a service; validation and the task model in focused modules; JSON file access in a store.
- **Rationale**: Each boundary has a clear responsibility and can be tested independently without introducing a generic framework.
- **Alternatives considered**: One script containing all behavior (simpler initially but harder to test and maintain); a layered repository/domain framework (unnecessary for one local JSON file).

### Validate JSON records separately from JSON syntax

- **Decision**: Treat parsing and task-shape validation as separate steps. JSON that parses but does not match the supported task schema is an error.
- **Rationale**: The standard `json` module converts JSON values; it does not enforce this application's required task fields or allowed values. This prevents invalid data from being mistaken for a valid empty task list.
- **Alternatives considered**: Accept missing or invalid fields by filling defaults. Rejected because it can conceal data damage and alter saved tasks.

### Use a replace-after-success persistence strategy

- **Decision**: Write a complete snapshot to a temporary file beside `tasks.json`, close it successfully, then replace the target. On failure, keep the old target and do not report the mutation as committed.
- **Rationale**: A same-directory temporary file avoids a cross-volume move and reduces the chance of truncating the only valid file during a failed save. `tempfile` provides managed temporary-file creation; `os.replace` provides a portable replacement API, subject to operating-system errors that must still be handled.
- **Alternatives considered**: Write directly over `tasks.json` (simpler but may leave a partial file); database storage (outside scope and less beginner-friendly).

### Use independent pytest suites

- **Decision**: Use pytest for separate unit and CLI/contract test runs, with fixed expected values and isolated `tmp_path` data.
- **Rationale**: The project requires independent automated validation; pytest supports fixtures and JUnit XML reports, while temporary paths prevent tests from touching real task data.
- **Alternatives considered**: `unittest` is built into Python but is not the selected project test framework; manual testing alone does not meet the constitution's automated-validation principle.

### Use a deterministic multi-check harness

- **Decision**: Run compilation, Ruff, Bandit, pytest unit, and pytest CLI/contract checks in a fixed order. Capture actual stdout, stderr, exit codes, and machine-readable reports for each run.
- **Rationale**: A per-check expected-versus-observed record makes results reproducible and gives a coding agent real evidence for repair rather than a paraphrase or invented failure.
- **Alternatives considered**: Ad hoc manual commands make it easier to omit a check or lose output; they are not the required validation process.

## Confirmed Technical Decisions

- Minimum runtime: Python 3.11 or newer.
- Test framework: pytest.
- Persisted data: versioned JSON object with `schema_version`, `next_id`, and `tasks`; sequential positive integer IDs are not reused after deletion.
- Concurrency: one application instance at a time; no file locking.
- Data location: project-root `tasks.json`, resolved from the package location rather than the current working directory. Tests use temporary directories or isolated project copies.
- Git hygiene: project-root `.gitignore` excludes `/tasks.json`.

## Pinned Development Tools

Selected exact versions from the current PyPI release metadata on 2026-11-11:

| Tool | Pinned version | Published `Requires-Python` | Compatibility |
|---|---:|---|---|
| pytest | 9.2.0 | `>=3.10` | Supports the project minimum of Python 3.11. |
| Ruff | 0.17.4 | `>=3.7` | Supports the project minimum of Python 3.11. |
| Bandit | 1.9.4 | `>=3.10` | Supports the project minimum of Python 3.11. |

These are development-only tools; application runtime dependencies remain standard-library only. The exact pins are recorded in `requirements-dev.txt`. Installation was verified in the configured Python 3.13.2 environment; the observed pytest, Ruff, and Bandit versions match the pins above.

## References

- [pytest 9.2.0 on PyPI](https://pypi.org/project/pytest/9.2.0/); [Ruff 0.17.4 on PyPI](https://pypi.org/project/ruff/0.17.4/); [Bandit 1.9.4 on PyPI](https://pypi.org/project/bandit/1.9.4/)
- [Python `json` module](https://docs.python.org/3/library/json.html)
- [Python `tempfile` module](https://docs.python.org/3/library/tempfile.html)
- [Python `os.replace`](https://docs.python.org/3/library/os.html#os.replace)
- [Python `unittest` module](https://docs.python.org/3/library/unittest.html)
- [Python `compileall` module](https://docs.python.org/3/library/compileall.html)
- [pytest output and JUnit reporting](https://docs.pytest.org/en/stable/how-to/output.html)
- [pytest temporary paths](https://docs.pytest.org/en/stable/how-to/tmp_path.html)
- [Ruff configuration](https://docs.astral.sh/ruff/configuration/)
- [Bandit command-line options](https://bandit.readthedocs.io/en/latest/man/bandit.html)
