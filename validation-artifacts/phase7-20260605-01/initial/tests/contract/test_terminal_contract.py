import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def test_module_launches_crud_menu_from_an_isolated_project_copy(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    source_package = project_root / "smart_todo"
    copied_package = tmp_path / "smart_todo"
    shutil.copytree(
        source_package,
        copied_package,
        ignore=shutil.ignore_patterns("__pycache__"),
    )

    result = subprocess.run(
        [sys.executable, "-m", "smart_todo"],
        cwd=tmp_path,
        input="0\n",
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "1. Add task" in result.stdout
    assert "2. View all tasks" in result.stdout
    assert "3. Update task" in result.stdout
    assert "4. Delete task" in result.stdout
    assert "5. Filter by tag" in result.stdout
    assert "6. Sort by priority" in result.stdout
    assert not (tmp_path / "tasks.json").exists()


def test_module_filter_and_sort_preserve_the_task_file_order(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    source_package = project_root / "smart_todo"
    copied_package = tmp_path / "smart_todo"
    shutil.copytree(
        source_package,
        copied_package,
        ignore=shutil.ignore_patterns("__pycache__"),
    )

    initial_data = {
        "schema_version": 1,
        "next_id": 5,
        "tasks": [
            {
                "id": 1,
                "title": "Low home",
                "priority": "Low",
                "status": "Pending",
                "tags": ["Home"],
            },
            {
                "id": 2,
                "title": "High office",
                "priority": "High",
                "status": "Pending",
                "tags": ["Office"],
            },
            {
                "id": 3,
                "title": "Medium home office",
                "priority": "Medium",
                "status": "Pending",
                "tags": ["Home office"],
            },
            {
                "id": 4,
                "title": "High home",
                "priority": "High",
                "status": "Pending",
                "tags": ["home"],
            },
        ],
    }
    task_file = tmp_path / "tasks.json"
    original_contents = json.dumps(initial_data, ensure_ascii=False, indent=2) + "\n"
    task_file.write_text(original_contents, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "smart_todo"],
        cwd=tmp_path,
        input="5\nHOME\n5\nmissing\n6\n0\n",
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "No tasks match tag 'missing'." in result.stdout
    displayed_ids = [
        f"ID: {task_id}" for task_id in re.findall(r"ID: (\d+) \|", result.stdout)
    ]
    assert displayed_ids == ["ID: 1", "ID: 4", "ID: 2", "ID: 4", "ID: 3", "ID: 1"]
    assert task_file.read_text(encoding="utf-8") == original_contents


def test_module_reports_invalid_task_data_without_overwriting_it(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    source_package = project_root / "smart_todo"
    copied_package = tmp_path / "smart_todo"
    shutil.copytree(
        source_package,
        copied_package,
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    task_file = tmp_path / "tasks.json"
    original_contents = '{"this is": "not the task schema"}\n'
    task_file.write_text(original_contents, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "smart_todo"],
        cwd=tmp_path,
        input="0\n",
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 1
    assert "Error: Task data file has an invalid envelope." in result.stderr
    assert "Traceback" not in result.stderr
    assert str(tmp_path) not in result.stderr
    assert task_file.read_text(encoding="utf-8") == original_contents
