# Validation run: phase7-20260605-01 (after-repair)

- **Overall:** PASS
- **Working directory:** `C:\Users\Sindhura Botla\Documents\Mtech\AISDLC\smart-todo`
- **Recorded:** 2026-11-11T19:19:52+00:00
- **Repair status:** Post-repair validation run; inspect changed-file hashes and evidence.

## Tool versions

| Tool | Expected | Observed | Result |
|---|---|---|---|
| python | >=3.11 | 3.13.2 | PASS |
| pytest | 9.2.0 | 9.2.0 | PASS |
| ruff | 0.17.4 | 0.17.4 | PASS |
| bandit | 1.9.4 | 1.9.4 | PASS |
| requirements_pins | {'pytest': '9.2.0', 'ruff': '0.17.4', 'bandit': '1.9.4'} | {'pytest': '9.2.0', 'ruff': '0.17.4', 'bandit': '1.9.4'} | PASS |

## Checks

| Check | Result | Exit code | Observed details |
|---|---|---:|---|
| python_compileall | PASS | 0 | no report counts |
| ruff_lint | PASS | 0 | findings=0 |
| bandit_security | PASS | 0 | findings=0 |
| pytest_unit | PASS | 0 | tests_collected=84, failures=0, errors=0, skipped=0, xfails=0 |
| pytest_cli_contract | PASS | 0 | tests_collected=26, failures=0, errors=0, skipped=0, xfails=0 |

## Evidence integrity gates

| Gate | Result |
|---|---|
| initial_snapshot_valid | PASS |
| policy_and_configuration_unchanged | PASS |
| check_configuration_matches_initial | PASS |

Expected outcomes are fixed in the snapshot's `validation-config.json`.
Raw stdout/stderr and JSON/JUnit reports are referenced in `run.json`.
