import json
from pathlib import Path

import pytest

from smart_todo.models import Priority, Status, Task
from smart_todo.storage import JsonTaskStore, default_task_file_path


def test_default_task_file_is_anchored_to_the_project_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = Path(__file__).resolve().parents[2] / "tasks.json"
    monkeypatch.chdir(tmp_path)

    assert default_task_file_path() == expected


def test_saved_file_uses_the_versioned_json_contract(tmp_path: Path) -> None:
    task_file = tmp_path / "tasks.json"
    task = Task(
        id=1,
        title="Read a book",
        priority=Priority.MEDIUM,
        status=Status.PENDING,
        tags=("Home",),
    )

    JsonTaskStore(task_file).save([task], next_id=2)
    persisted = json.loads(task_file.read_text(encoding="utf-8"))

    assert persisted == {
        "schema_version": 1,
        "next_id": 2,
        "tasks": [
            {
                "id": 1,
                "title": "Read a book",
                "priority": "Medium",
                "status": "Pending",
                "tags": ["Home"],
            }
        ],
    }
