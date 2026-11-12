"""Run the frozen Smart Todo validation checks and preserve their evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "validation-artifacts"
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
EXPECTED_TOOL_VERSIONS = {
    "pytest": "9.2.0",
    "ruff": "0.17.4",
    "bandit": "1.9.4",
}
MINIMUM_PYTHON = (3, 11)
COMMAND_TIMEOUT_SECONDS = 600
FIXED_ENVIRONMENT = {
    "NO_COLOR": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "PYTHONIOENCODING": "utf-8",
    "PYTEST_ADDOPTS": "",
}
REMOVED_ENVIRONMENT_KEYS = (
    "PYTHONPATH",
    "PYTEST_PLUGINS",
)
SNAPSHOT_PATHS = (
    Path("smart_todo"),
    Path("tests"),
    Path("scripts"),
    Path("specs/001-smart-todo-cli"),
    Path(".specify/memory/constitution.md"),
    Path(".gitignore"),
    Path("pyproject.toml"),
    Path("requirements-dev.txt"),
)
SNAPSHOT_IGNORE_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".nox",
    ".tox",
    ".venv",
    "venv",
    "validation-artifacts",
    "tasks.json",
}
CHECK_TEMPLATES = [
    {
        "name": "python_compileall",
        "argv": [
            "<python>",
            "-m",
            "compileall",
            "-q",
            "smart_todo",
            "tests",
        ],
        "expected": {"exit_code": 0},
    },
    {
        "name": "ruff_lint",
        "argv": ["<ruff>", "check", "--output-format", "json", "smart_todo", "tests"],
        "expected": {"exit_code": 0, "findings": 0},
        "json_report": "ruff.json",
    },
    {
        "name": "bandit_security",
        "argv": ["<bandit>", "-r", "smart_todo", "--format", "json"],
        "expected": {"exit_code": 0, "findings": 0},
        "json_report": "bandit.json",
    },
    {
        "name": "pytest_unit",
        "argv": [
            "<python>",
            "-m",
            "pytest",
            "-q",
            "tests/unit",
            "--junitxml=<RUN_DIR>/pytest-unit.xml",
        ],
        "expected": {
            "exit_code": 0,
            "tests_collected": ">0",
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "xfails": 0,
        },
        "junit_report": "pytest-unit.xml",
    },
    {
        "name": "pytest_cli_contract",
        "argv": [
            "<python>",
            "-m",
            "pytest",
            "-q",
            "tests/cli",
            "tests/contract",
            "--junitxml=<RUN_DIR>/pytest-cli-contract.xml",
        ],
        "expected": {
            "exit_code": 0,
            "tests_collected": ">0",
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "xfails": 0,
        },
        "junit_report": "pytest-cli-contract.xml",
    },
]


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _write_new(path: Path, contents: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output_file:
        output_file.write(contents)


def _write_json_new(path: Path, value: object) -> None:
    _write_new(path, _json_text(value).encode("utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_value(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _snapshot_ignore(_: str, names: list[str]) -> set[str]:
    ignored = {
        name
        for name in names
        if name in SNAPSHOT_IGNORE_NAMES
        or name.endswith((".pyc", ".pyo"))
    }
    return ignored


def _inventory_files(paths: tuple[Path, ...]) -> dict[str, dict[str, object]]:
    inventory: dict[str, dict[str, object]] = {}
    for relative_path in paths:
        source = PROJECT_ROOT / relative_path
        if not source.exists():
            raise FileNotFoundError(f"Required project input is missing: {relative_path}")
        if source.is_file():
            sources = [source]
        else:
            sources = sorted(
                item
                for item in source.rglob("*")
                if item.is_file()
                and not any(part in SNAPSHOT_IGNORE_NAMES for part in item.parts)
                and item.suffix not in {".pyc", ".pyo"}
            )
        for file_path in sources:
            relative = file_path.relative_to(PROJECT_ROOT).as_posix()
            inventory[relative] = {
                "sha256": _sha256_file(file_path),
                "size_bytes": file_path.stat().st_size,
            }
    return dict(sorted(inventory.items()))


def _test_file_hashes() -> dict[str, str]:
    test_inventory = _inventory_files((Path("tests"),))
    return {
        name: str(details["sha256"])
        for name, details in test_inventory.items()
    }


def _parse_requirement_pins() -> dict[str, str]:
    requirements_file = PROJECT_ROOT / "requirements-dev.txt"
    pins: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        requirements_file.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)", line)
        if match is None:
            raise ValueError(
                f"Unpinned or unsupported requirement on line {line_number}."
            )
        pins[match.group(1).lower().replace("_", "-")] = match.group(2)
    return pins


def _resolve_executable(name: str) -> str | None:
    executable_names = (f"{name}.exe", name) if os.name == "nt" else (name,)
    executable_directory = Path(sys.executable).resolve().parent
    for executable_name in executable_names:
        candidate = executable_directory / executable_name
        if candidate.is_file():
            return str(candidate)
    return shutil.which(name)


def _command_templates() -> list[dict[str, object]]:
    return [
        {
            "name": check["name"],
            "argv": check["argv"],
            "expected": check["expected"],
        }
        for check in CHECK_TEMPLATES
    ]


def _build_configuration(
    resolved_tools: dict[str, str | None],
) -> dict[str, object]:
    policy_paths = (
        Path(".gitignore"),
        Path("pyproject.toml"),
        Path("requirements-dev.txt"),
        Path("specs/001-smart-todo-cli/spec.md"),
        Path("specs/001-smart-todo-cli/plan.md"),
        Path("specs/001-smart-todo-cli/tasks.md"),
        Path("specs/001-smart-todo-cli/quickstart.md"),
        Path(".specify/memory/constitution.md"),
    )
    policy_inventory = _inventory_files(policy_paths)
    try:
        requirement_pins = _parse_requirement_pins()
        requirement_pin_error = None
    except (OSError, ValueError) as exc:
        requirement_pins = {}
        requirement_pin_error = f"{type(exc).__name__}: {exc}"

    configuration: dict[str, object] = {
        "project_root": str(PROJECT_ROOT),
        "working_directory": str(PROJECT_ROOT),
        "python": {
            "executable": str(Path(sys.executable).resolve()),
            "observed_version": platform.python_version(),
            "minimum_version": "3.11",
        },
        "expected_tool_versions": {
            "pytest": EXPECTED_TOOL_VERSIONS["pytest"],
            "ruff": EXPECTED_TOOL_VERSIONS["ruff"],
            "bandit": EXPECTED_TOOL_VERSIONS["bandit"],
        },
        "resolved_tool_executables": resolved_tools,
        "requirements_dev_pins": requirement_pins,
        "requirements_pin_error": requirement_pin_error,
        "policy_file_hashes": policy_inventory,
        "test_file_hashes": _test_file_hashes(),
        "test_data_policy": (
            "Pytest fixtures use temporary directories; terminal contract tests "
            "use isolated temporary project copies; the harness supplies no "
            "task data and excludes the project-root tasks.json from snapshots."
        ),
        "environment": {
            "overrides": FIXED_ENVIRONMENT,
            "removed_keys": list(REMOVED_ENVIRONMENT_KEYS),
        },
        "command_timeout_seconds": COMMAND_TIMEOUT_SECONDS,
        "check_templates": _command_templates(),
    }
    fingerprint_fields = {
        key: value
        for key, value in configuration.items()
        if key not in {"resolved_tool_executables"}
    }
    configuration["check_configuration_sha256"] = _sha256_value(
        fingerprint_fields
    )
    configuration["validator_sha256"] = _sha256_file(Path(__file__).resolve())
    return configuration


def _copy_snapshot_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=_snapshot_ignore,
        copy_function=shutil.copy2,
    )


def _create_initial_snapshot(
    initial_directory: Path,
    configuration: dict[str, object],
) -> dict[str, object]:
    if initial_directory.exists():
        raise FileExistsError(f"Initial snapshot already exists: {initial_directory}")
    initial_directory.mkdir(parents=True)

    for relative_path in SNAPSHOT_PATHS:
        source = PROJECT_ROOT / relative_path
        destination = initial_directory / relative_path
        if not source.exists():
            raise FileNotFoundError(f"Required snapshot input is missing: {relative_path}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            _copy_snapshot_tree(source, destination)
        else:
            shutil.copy2(source, destination)

    validation_config_path = initial_directory / "validation-config.json"
    _write_json_new(validation_config_path, configuration)
    file_inventory = _inventory_snapshot(initial_directory)
    manifest: dict[str, object] = {
        "run_id": initial_directory.parent.name,
        "created_at_utc": _utc_timestamp(),
        "hash_algorithm": "SHA-256",
        "excluded_names": sorted(SNAPSHOT_IGNORE_NAMES),
        "files": file_inventory,
    }
    _write_json_new(initial_directory / "sha256-manifest.json", manifest)
    return manifest


def _inventory_snapshot(initial_directory: Path) -> dict[str, dict[str, object]]:
    inventory: dict[str, dict[str, object]] = {}
    for path in sorted(initial_directory.rglob("*")):
        if not path.is_file() or path.name == "sha256-manifest.json":
            continue
        relative = path.relative_to(initial_directory).as_posix()
        inventory[relative] = {
            "sha256": _sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
    return inventory


def _verify_initial_snapshot(initial_directory: Path) -> dict[str, object]:
    manifest_path = initial_directory / "sha256-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_files = manifest["files"]
    actual_files = _inventory_snapshot(initial_directory)
    differences = []
    for relative_path, expected in expected_files.items():
        observed = actual_files.get(relative_path)
        if observed != expected:
            differences.append(relative_path)
    for relative_path in actual_files.keys() - expected_files.keys():
        differences.append(relative_path)
    return {
        "valid": not differences,
        "changed_or_missing_files": sorted(differences),
        "manifest_path": str(manifest_path),
    }


def _fixed_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in REMOVED_ENVIRONMENT_KEYS:
        environment.pop(key, None)
    environment.update(FIXED_ENVIRONMENT)
    return environment


def _format_command(argv: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(argv)
    return shlex.join(argv)


def _invoke(argv: list[str]) -> dict[str, object]:
    try:
        completed = subprocess.run(
            argv,
            cwd=PROJECT_ROOT,
            env=_fixed_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        if isinstance(stdout, str):
            stdout = stdout.encode("utf-8", errors="replace")
        if isinstance(stderr, str):
            stderr = stderr.encode("utf-8", errors="replace")
        return {
            "exit_code": None,
            "stdout": stdout,
            "stderr": stderr,
            "error": f"Timed out after {COMMAND_TIMEOUT_SECONDS} seconds.",
        }
    except OSError as exc:
        return {
            "exit_code": None,
            "stdout": b"",
            "stderr": str(exc).encode("utf-8", errors="replace"),
            "error": f"{type(exc).__name__}: {exc}",
        }

    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "error": None,
    }


def _write_process_output(
    evidence_directory: Path,
    basename: str,
    stdout: bytes,
    stderr: bytes,
) -> dict[str, str]:
    stdout_binary = evidence_directory / f"{basename}.stdout.bin"
    stderr_binary = evidence_directory / f"{basename}.stderr.bin"
    stdout_text = evidence_directory / f"{basename}.stdout.txt"
    stderr_text = evidence_directory / f"{basename}.stderr.txt"
    _write_new(stdout_binary, stdout)
    _write_new(stderr_binary, stderr)
    _write_new(
        stdout_text,
        stdout.decode("utf-8", errors="replace").encode("utf-8"),
    )
    _write_new(
        stderr_text,
        stderr.decode("utf-8", errors="replace").encode("utf-8"),
    )
    return {
        "stdout_binary": stdout_binary.name,
        "stderr_binary": stderr_binary.name,
        "stdout_text": stdout_text.name,
        "stderr_text": stderr_text.name,
    }


def _extract_version(output: bytes) -> str | None:
    decoded = output.decode("utf-8", errors="replace")
    match = re.search(r"(?<!\d)(\d+\.\d+\.\d+)(?!\d)", decoded)
    return match.group(1) if match else None


def _run_version_checks(
    evidence_directory: Path,
    resolved_tools: dict[str, str | None],
    requirements_pins: dict[str, str],
    requirement_pin_error: object,
) -> dict[str, object]:
    commands: dict[str, list[str]] = {
        "python": [str(Path(sys.executable).resolve()), "--version"],
        "pytest": [
            str(Path(sys.executable).resolve()),
            "-m",
            "pytest",
            "--version",
        ],
        "ruff": [resolved_tools["ruff"] or "ruff", "--version"],
        "bandit": [resolved_tools["bandit"] or "bandit", "--version"],
    }
    results: dict[str, object] = {}
    for name, argv in commands.items():
        process = _invoke(argv)
        output_paths = _write_process_output(
            evidence_directory,
            f"version-{name}",
            process["stdout"],
            process["stderr"],
        )
        observed = _extract_version(process["stdout"]) or _extract_version(
            process["stderr"]
        )
        if name == "python":
            version_ok = (
                process["exit_code"] == 0
                and sys.version_info[:2] >= MINIMUM_PYTHON
            )
            expected: object = ">=3.11"
        else:
            expected = EXPECTED_TOOL_VERSIONS[name]
            version_ok = process["exit_code"] == 0 and observed == expected

        results[name] = {
            "command": _format_command(argv),
            "argv": argv,
            "working_directory": str(PROJECT_ROOT),
            "exit_code": process["exit_code"],
            "expected_version": expected,
            "observed_version": observed,
            "passed": version_ok,
            "error": process["error"],
            "output_files": output_paths,
        }

    expected_pins = {
        "pytest": EXPECTED_TOOL_VERSIONS["pytest"],
        "ruff": EXPECTED_TOOL_VERSIONS["ruff"],
        "bandit": EXPECTED_TOOL_VERSIONS["bandit"],
    }
    normalized_pins = {
        key.replace("_", "-"): value for key, value in requirements_pins.items()
    }
    pins_match = normalized_pins == expected_pins and requirement_pin_error is None
    results["requirements_pins"] = {
        "expected": expected_pins,
        "observed": normalized_pins,
        "passed": pins_match,
        "error": requirement_pin_error,
    }
    return results


def _materialize_checks(
    run_directory: Path,
    resolved_tools: dict[str, str | None],
) -> list[dict[str, object]]:
    substitutions = {
        "<python>": str(Path(sys.executable).resolve()),
        "<ruff>": resolved_tools["ruff"] or "ruff",
        "<bandit>": resolved_tools["bandit"] or "bandit",
        "<RUN_DIR>": str(run_directory),
    }
    checks: list[dict[str, object]] = []
    for template in CHECK_TEMPLATES:
        argv = []
        for argument in template["argv"]:
            substituted = argument
            for placeholder, value in substitutions.items():
                substituted = substituted.replace(placeholder, value)
            argv.append(substituted)
        checks.append(
            {
                "name": template["name"],
                "argv": argv,
                "expected": template["expected"],
                "tool_version": (
                    "python"
                    if template["name"] in {"python_compileall", "pytest_unit", "pytest_cli_contract"}
                    else template["name"].split("_")[0]
                ),
                "json_report": template.get("json_report"),
                "junit_report": template.get("junit_report"),
            }
        )
    return checks


def _relative_evidence_path(run_root: Path, path: Path) -> str:
    return path.relative_to(run_root).as_posix()


def _parse_junit_report(report_path: Path) -> dict[str, int]:
    root = ET.parse(report_path).getroot()
    test_cases = list(root.iter("testcase"))
    failures = len(list(root.iter("failure")))
    errors = len(list(root.iter("error")))
    skipped_nodes = list(root.iter("skipped"))
    xfails = sum(
        1
        for node in skipped_nodes
        if "xfail"
        in f"{node.get('type', '')} {node.get('message', '')}".casefold()
    )
    return {
        "tests_collected": len(test_cases),
        "failures": failures,
        "errors": errors,
        "skipped": len(skipped_nodes) - xfails,
        "xfails": xfails,
    }


def _run_check(
    check: dict[str, object],
    run_directory: Path,
    run_root: Path,
    tool_versions: dict[str, object],
) -> dict[str, object]:
    name = str(check["name"])
    argv = check["argv"]
    process = _invoke(argv)
    output_paths = _write_process_output(
        run_directory,
        name,
        process["stdout"],
        process["stderr"],
    )
    observed: dict[str, object] = {
        "exit_code": process["exit_code"],
        "error": process["error"],
    }
    report_paths: dict[str, str] = {
        "stdout_binary": _relative_evidence_path(
            run_root, run_directory / output_paths["stdout_binary"]
        ),
        "stderr_binary": _relative_evidence_path(
            run_root, run_directory / output_paths["stderr_binary"]
        ),
        "stdout_text": _relative_evidence_path(
            run_root, run_directory / output_paths["stdout_text"]
        ),
        "stderr_text": _relative_evidence_path(
            run_root, run_directory / output_paths["stderr_text"]
        ),
    }
    report_present = True
    report_error = None

    json_report = check["json_report"]
    if json_report is not None:
        report_path = run_directory / str(json_report)
        _write_new(report_path, process["stdout"])
        report_paths["json_report"] = _relative_evidence_path(run_root, report_path)
        try:
            parsed_report = json.loads(process["stdout"].decode("utf-8-sig"))
            if name == "ruff_lint":
                findings = len(parsed_report)
            else:
                findings = len(parsed_report["results"])
            observed["findings"] = findings
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            report_present = False
            report_error = f"Could not parse {json_report}: {type(exc).__name__}: {exc}"

    junit_report = check["junit_report"]
    if junit_report is not None:
        report_path = run_directory / str(junit_report)
        if report_path.is_file():
            report_paths["junit_report"] = _relative_evidence_path(
                run_root, report_path
            )
            try:
                observed.update(_parse_junit_report(report_path))
            except (ET.ParseError, OSError) as exc:
                report_present = False
                report_error = (
                    f"Could not parse {junit_report}: {type(exc).__name__}: {exc}"
                )
        else:
            report_present = False
            report_error = f"Required JUnit report was not created: {junit_report}"

    observed["required_report_present"] = report_present
    if report_error is not None:
        observed["report_error"] = report_error

    expected = check["expected"]
    passed = process["exit_code"] == expected["exit_code"] and report_present
    if "findings" in expected:
        passed = passed and observed.get("findings") == expected["findings"]
    if "tests_collected" in expected:
        passed = passed and int(observed.get("tests_collected", 0)) > 0
        for count_name in ("failures", "errors", "skipped", "xfails"):
            passed = passed and observed.get(count_name) == expected[count_name]

    tool_version_name = str(check["tool_version"])
    version_record = tool_versions.get(tool_version_name, {})
    return {
        "name": name,
        "command": _format_command(argv),
        "argv": argv,
        "working_directory": str(PROJECT_ROOT),
        "tool_version": version_record.get("observed_version"),
        "expected": expected,
        "observed": observed,
        "passed": bool(passed),
        "output_artifacts": report_paths,
    }


def _snapshot_comparison(
    initial_directory: Path,
    configuration: dict[str, object],
) -> dict[str, object]:
    initial_manifest_path = initial_directory / "sha256-manifest.json"
    initial_manifest = json.loads(
        initial_manifest_path.read_text(encoding="utf-8")
    )
    original_files = initial_manifest["files"]
    current_files = _inventory_files(SNAPSHOT_PATHS)
    original_hashes = {
        path: str(details["sha256"]) for path, details in original_files.items()
    }
    current_hashes = {
        path: str(details["sha256"]) for path, details in current_files.items()
    }

    original_tests = {
        path: digest
        for path, digest in original_hashes.items()
        if path.startswith("tests/")
    }
    current_tests = {
        path: digest
        for path, digest in current_hashes.items()
        if path.startswith("tests/")
    }
    test_set_unchanged = original_tests == current_tests

    unchanged_policy_paths = (
        ".gitignore",
        "pyproject.toml",
        "requirements-dev.txt",
        "specs/001-smart-todo-cli/spec.md",
        "specs/001-smart-todo-cli/plan.md",
        "specs/001-smart-todo-cli/tasks.md",
        "specs/001-smart-todo-cli/quickstart.md",
        ".specify/memory/constitution.md",
    )
    policy_unchanged = all(
        original_hashes.get(path) == current_hashes.get(path)
        for path in unchanged_policy_paths
    )
    app_paths = {
        path
        for path in original_hashes.keys() | current_hashes.keys()
        if path.startswith("smart_todo/")
    }
    changed_app_files = sorted(
        path
        for path in app_paths
        if original_hashes.get(path) != current_hashes.get(path)
    )
    return {
        "initial_snapshot_valid": _verify_initial_snapshot(initial_directory),
        "test_set_unchanged": test_set_unchanged,
        "policy_and_configuration_unchanged": policy_unchanged,
        "changed_application_files": changed_app_files,
        "check_configuration_sha256": configuration[
            "check_configuration_sha256"
        ],
    }


def _format_check_summary(check: dict[str, object]) -> str:
    observed = check["observed"]
    exit_code = observed.get("exit_code")
    details = []
    if "findings" in observed:
        details.append(f"findings={observed['findings']}")
    if "tests_collected" in observed:
        details.extend(
            f"{key}={observed[key]}"
            for key in (
                "tests_collected",
                "failures",
                "errors",
                "skipped",
                "xfails",
            )
        )
    detail_text = ", ".join(details) if details else "no report counts"
    label = "PASS" if check["passed"] else "FAIL"
    return f"| {check['name']} | {label} | {exit_code} | {detail_text} |"


def _write_run_summary(run_directory: Path, run: dict[str, object]) -> None:
    lines = [
        f"# Validation run: {run['run_id']} ({run['phase']})",
        "",
        f"- **Overall:** {run['overall']}",
        f"- **Working directory:** `{run['working_directory']}`",
        f"- **Recorded:** {run['created_at_utc']}",
        f"- **Repair status:** {run['repair_status']}",
        "",
        "## Tool versions",
        "",
        "| Tool | Expected | Observed | Result |",
        "|---|---|---|---|",
    ]
    for name in ("python", "pytest", "ruff", "bandit", "requirements_pins"):
        result = run["tool_versions"][name]
        expected = result.get("expected_version", result.get("expected"))
        observed = result.get("observed_version", result.get("observed"))
        label = "PASS" if result["passed"] else "FAIL"
        lines.append(f"| {name} | {expected} | {observed} | {label} |")
    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| Check | Result | Exit code | Observed details |",
            "|---|---|---:|---|",
        ]
    )
    lines.extend(_format_check_summary(check) for check in run["checks"])
    if run["integrity_gates"]:
        lines.extend(
            [
                "",
                "## Evidence integrity gates",
                "",
                "| Gate | Result |",
                "|---|---|",
            ]
        )
        lines.extend(
            f"| {name} | {'PASS' if passed else 'FAIL'} |"
            for name, passed in run["integrity_gates"].items()
        )
    lines.extend(
        [
            "",
            "Expected outcomes are fixed in the snapshot's `validation-config.json`.",
            "Raw stdout/stderr and JSON/JUnit reports are referenced in `run.json`.",
            "",
        ]
    )
    _write_new(
        run_directory / "summary.md",
        "\n".join(lines).encode("utf-8"),
    )


def _run_validation(
    run_id: str,
    phase: str,
    run_root: Path,
    run_directory: Path,
    configuration: dict[str, object],
    resolved_tools: dict[str, str | None],
    repair_status: str,
    integrity_gates: dict[str, bool] | None = None,
) -> dict[str, object]:
    run_directory.mkdir(parents=True, exist_ok=False)
    version_directory = run_directory / "versions"
    version_directory.mkdir()
    checks_directory = run_directory / "checks"
    checks_directory.mkdir()
    tool_versions = _run_version_checks(
        version_directory,
        resolved_tools,
        configuration["requirements_dev_pins"],
        configuration["requirements_pin_error"],
    )
    checks = _materialize_checks(checks_directory, resolved_tools)
    check_results = [
        _run_check(check, checks_directory, run_root, tool_versions)
        for check in checks
    ]
    preflight_passed = all(
        record["passed"] for record in tool_versions.values()
    )
    run_integrity_gates = integrity_gates or {}
    overall_passed = (
        preflight_passed
        and all(result["passed"] for result in check_results)
        and all(run_integrity_gates.values())
    )
    run: dict[str, object] = {
        "run_id": run_id,
        "phase": phase,
        "created_at_utc": _utc_timestamp(),
        "project_root": str(PROJECT_ROOT),
        "working_directory": str(PROJECT_ROOT),
        "python_executable": str(Path(sys.executable).resolve()),
        "configuration_sha256": configuration["check_configuration_sha256"],
        "validator_sha256": configuration["validator_sha256"],
        "repair_status": repair_status,
        "tool_versions": tool_versions,
        "preflight_passed": preflight_passed,
        "checks": check_results,
        "integrity_gates": run_integrity_gates,
        "overall": "PASS" if overall_passed else "FAIL",
    }
    _write_json_new(run_directory / "run.json", run)
    _write_run_summary(run_directory, run)
    return run


def _comparison_document(
    initial_run: dict[str, object],
    final_run: dict[str, object],
    snapshot_comparison: dict[str, object],
    configuration_matches: bool,
) -> dict[str, object]:
    initial_checks = {
        check["name"]: check for check in initial_run["checks"]
    }
    final_checks = {
        check["name"]: check for check in final_run["checks"]
    }
    comparisons = []
    for name in initial_checks.keys() | final_checks.keys():
        initial = initial_checks.get(name)
        final = final_checks.get(name)
        comparisons.append(
            {
                "name": name,
                "initial": (
                    {
                        "passed": initial["passed"],
                        "exit_code": initial["observed"]["exit_code"],
                        "observed": initial["observed"],
                    }
                    if initial is not None
                    else None
                ),
                "final": (
                    {
                        "passed": final["passed"],
                        "exit_code": final["observed"]["exit_code"],
                        "observed": final["observed"],
                    }
                    if final is not None
                    else None
                ),
                "same_outcome": (
                    initial is not None
                    and final is not None
                    and initial["passed"] == final["passed"]
                    and initial["observed"] == final["observed"]
                ),
            }
        )

    initial_versions = initial_run["tool_versions"]
    final_versions = final_run["tool_versions"]
    same_versions = all(
        initial_versions[name].get("observed_version")
        == final_versions[name].get("observed_version")
        and initial_versions[name]["passed"] == final_versions[name]["passed"]
        for name in ("python", "pytest", "ruff", "bandit")
    )
    same_check_set = set(initial_checks) == set(final_checks)
    checks_match = same_check_set and all(
        item["same_outcome"] for item in comparisons
    )
    comparison_passed = (
        initial_run["overall"] == "PASS"
        and final_run["overall"] == "PASS"
        and same_versions
        and checks_match
        and configuration_matches
        and snapshot_comparison["initial_snapshot_valid"]["valid"]
        and snapshot_comparison["test_set_unchanged"]
        and snapshot_comparison["policy_and_configuration_unchanged"]
    )
    return {
        "run_id": final_run["run_id"],
        "created_at_utc": _utc_timestamp(),
        "repair_status": final_run["repair_status"],
        "initial_overall": initial_run["overall"],
        "final_overall": final_run["overall"],
        "same_tool_versions": same_versions,
        "same_check_set": same_check_set,
        "check_configuration_matches": configuration_matches,
        "snapshot_and_test_integrity": snapshot_comparison,
        "checks": sorted(comparisons, key=lambda item: item["name"]),
        "overall_comparison": "PASS" if comparison_passed else "FAIL",
        "human_acceptance": "PENDING",
    }


def _write_comparison(run_root: Path, comparison: dict[str, object]) -> None:
    json_path = run_root / "comparison.json"
    markdown_path = run_root / "comparison.md"
    if json_path.exists() or markdown_path.exists():
        raise FileExistsError("Comparison evidence already exists; refusing to overwrite.")
    _write_json_new(json_path, comparison)
    lines = [
        f"# Initial/final comparison: {comparison['run_id']}",
        "",
        f"- **Initial validation:** {comparison['initial_overall']}",
        f"- **Final confirmation:** {comparison['final_overall']}",
        f"- **Tool versions unchanged:** {comparison['same_tool_versions']}",
        f"- **Check set unchanged:** {comparison['same_check_set']}",
        f"- **Check configuration matches:** {comparison['check_configuration_matches']}",
        f"- **Comparison result:** {comparison['overall_comparison']}",
        "- **Human acceptance:** PENDING",
        "",
        "| Check | Initial | Final | Initial exit | Final exit | Same observed outcome |",
        "|---|---|---|---:|---:|---|",
    ]
    for item in comparison["checks"]:
        initial = item["initial"]
        final = item["final"]
        lines.append(
            "| {name} | {initial_pass} | {final_pass} | {initial_exit} | "
            "{final_exit} | {same} |".format(
                name=item["name"],
                initial_pass=initial["passed"] if initial else "MISSING",
                final_pass=final["passed"] if final else "MISSING",
                initial_exit=initial["exit_code"] if initial else "MISSING",
                final_exit=final["exit_code"] if final else "MISSING",
                same=item["same_outcome"],
            )
        )
    lines.extend(
        [
            "",
            "The complete observed counts and report references are preserved in "
            "`before-repair/run.json` and `after-repair/run.json`.",
            "No human ACCEPT/REJECT decision is made by this harness.",
            "",
        ]
    )
    _write_new(markdown_path, "\n".join(lines).encode("utf-8"))


def _initial_repair_status(initial_run: dict[str, object]) -> str:
    if initial_run["overall"] == "PASS":
        return "No repair needed; final confirmation run."
    return "Post-repair validation run; inspect changed-file hashes and evidence."


def _run_initial(run_id: str, run_root: Path, configuration: dict[str, object],
                 resolved_tools: dict[str, str | None]) -> int:
    if run_root.exists():
        raise FileExistsError(f"Run directory already exists: {run_root}")
    run_root.mkdir(parents=True)
    _create_initial_snapshot(run_root / "initial", configuration)
    run = _run_validation(
        run_id,
        "initial",
        run_root,
        run_root / "before-repair",
        configuration,
        resolved_tools,
        "Initial validation; no repair attempted.",
    )
    print(f"Validation {run_id} initial: {run['overall']}")
    print(f"Evidence: {(run_root / 'before-repair' / 'summary.md').relative_to(PROJECT_ROOT)}")
    for check in run["checks"]:
        print(
            f"{'PASS' if check['passed'] else 'FAIL'} "
            f"{check['name']}: exit={check['observed']['exit_code']}"
        )
    return 0 if run["overall"] == "PASS" else 1


def _run_after_repair(
    run_id: str,
    run_root: Path,
    configuration: dict[str, object],
    resolved_tools: dict[str, str | None],
) -> int:
    initial_directory = run_root / "initial"
    initial_evidence_path = run_root / "before-repair" / "run.json"
    initial_config_path = initial_directory / "validation-config.json"
    after_directory = run_root / "after-repair"
    if not initial_directory.is_dir() or not initial_evidence_path.is_file():
        raise FileNotFoundError(
            "Initial snapshot and before-repair results are required before revalidation."
        )
    if not initial_config_path.is_file():
        raise FileNotFoundError("Initial frozen validation configuration is missing.")
    if after_directory.exists():
        raise FileExistsError(f"After-repair evidence already exists: {after_directory}")

    initial_run = json.loads(initial_evidence_path.read_text(encoding="utf-8"))
    initial_config = json.loads(initial_config_path.read_text(encoding="utf-8"))
    configuration_matches = (
        configuration["check_configuration_sha256"]
        == initial_config["check_configuration_sha256"]
    )
    snapshot_comparison = _snapshot_comparison(initial_directory, configuration)
    repair_status = _initial_repair_status(initial_run)
    integrity_gates = {
        "initial_snapshot_valid": snapshot_comparison[
            "initial_snapshot_valid"
        ]["valid"],
        "test_set_unchanged": snapshot_comparison["test_set_unchanged"],
        "policy_and_configuration_unchanged": snapshot_comparison[
            "policy_and_configuration_unchanged"
        ],
        "check_configuration_matches_initial": configuration_matches,
    }
    final_run = _run_validation(
        run_id,
        "after-repair",
        run_root,
        after_directory,
        configuration,
        resolved_tools,
        repair_status,
        integrity_gates,
    )

    comparison = _comparison_document(
        initial_run,
        final_run,
        snapshot_comparison,
        configuration_matches,
    )
    _write_comparison(run_root, comparison)
    print(f"Validation {run_id} after-repair: {final_run['overall']}")
    print(f"Comparison: {(run_root / 'comparison.md').relative_to(PROJECT_ROOT)}")
    for check in final_run["checks"]:
        print(
            f"{'PASS' if check['passed'] else 'FAIL'} "
            f"{check['name']}: exit={check['observed']['exit_code']}"
        )
    return 0 if comparison["overall_comparison"] == "PASS" else 1


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Smart Todo's fixed validation gates and preserve evidence."
    )
    parser.add_argument("--run-id", required=True, help="Unique, path-safe evidence run ID.")
    parser.add_argument(
        "--phase",
        choices=("initial", "after-repair"),
        required=True,
        help="Initial snapshot/validation or final confirmation.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = _parse_arguments()
    run_id = arguments.run_id
    if RUN_ID_PATTERN.fullmatch(run_id) is None or run_id in {".", ".."}:
        print("Validation harness error: run ID must be a safe path component.", file=sys.stderr)
        return 2
    if PROJECT_ROOT.resolve() != Path.cwd().resolve():
        print(
            "Validation harness error: run the script with the project root as the working directory.",
            file=sys.stderr,
        )
        return 2

    resolved_tools = {
        "ruff": _resolve_executable("ruff"),
        "bandit": _resolve_executable("bandit"),
    }
    try:
        configuration = _build_configuration(resolved_tools)
        ARTIFACT_ROOT.mkdir(exist_ok=True)
        run_root = ARTIFACT_ROOT / run_id
        if arguments.phase == "initial":
            return _run_initial(run_id, run_root, configuration, resolved_tools)
        return _run_after_repair(
            run_id, run_root, configuration, resolved_tools
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError, ET.ParseError) as exc:
        print(
            f"Validation harness error: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
