import os
from pathlib import Path

import pytest

import smart_todo.storage as storage_module
from smart_todo.models import Priority, Status, Task
from smart_todo.storage import JsonTaskStore, StorageError


def test_missing_file_loads_as_an_empty_first_run(tmp_path: Path) -> None:
    task_file = tmp_path / "tasks.json"

    tasks, next_id = JsonTaskStore(task_file).load()

    assert tasks == []
    assert next_id == 1
    assert not task_file.exists()


def test_store_round_trips_tasks_and_next_id(tmp_path: Path) -> None:
    store = JsonTaskStore(tmp_path / "tasks.json")
    tasks = [
        Task(
            id=2,
            title="Read a book",
            priority=Priority.HIGH,
            status=Status.IN_PROGRESS,
            tags=("Home", "Reading"),
        )
    ]

    store.save(tasks, next_id=3)

    loaded_tasks, next_id = JsonTaskStore(store.path).load()
    assert loaded_tasks == tasks
    assert next_id == 3


def test_task_snapshots_persist_add_update_delete_and_id_counter(
    tmp_path: Path,
) -> None:
    task_file = tmp_path / "tasks.json"
    original = Task(
        id=1,
        title="Read a book",
        priority=Priority.MEDIUM,
        status=Status.PENDING,
        tags=("Home",),
    )
    JsonTaskStore(task_file).save([original], next_id=2)

    loaded, next_id = JsonTaskStore(task_file).load()
    assert loaded == [original]
    assert next_id == 2

    updated = Task(
        id=1,
        title="Read a reference book",
        priority=Priority.HIGH,
        status=Status.IN_PROGRESS,
        tags=("Home", "Reading"),
    )
    JsonTaskStore(task_file).save([updated], next_id=2)

    loaded, next_id = JsonTaskStore(task_file).load()
    assert loaded == [updated]
    assert next_id == 2

    JsonTaskStore(task_file).save([], next_id=2)
    loaded, next_id = JsonTaskStore(task_file).load()
    assert loaded == []
    assert next_id == 2

    replacement = Task(
        id=2,
        title="Write a summary",
        priority=Priority.LOW,
        status=Status.PENDING,
    )
    JsonTaskStore(task_file).save([replacement], next_id=3)
    loaded, next_id = JsonTaskStore(task_file).load()
    assert loaded == [replacement]
    assert next_id == 3


@pytest.mark.parametrize(
    "contents",
    [
        "{not json",
        "[]",
        '{"schema_version": 2, "next_id": 1, "tasks": []}',
        '{"schema_version": 1, "next_id": 1, "tasks": [], "extra": true}',
        '{"schema_version": 1, "next_id": true, "tasks": []}',
        (
            '{"schema_version": 1, "next_id": 2, "tasks": ['
            '{"id": 2, "title": "Read", "priority": "High", '
            '"status": "Pending", "tags": []}]}'
        ),
        (
            '{"schema_version": 1, "next_id": 3, "tasks": ['
            '{"id": 1, "title": "Read", "priority": "High", '
            '"status": "Pending", "tags": []},'
            '{"id": 1, "title": "Write", "priority": "Low", '
            '"status": "Completed", "tags": []}]}'
        ),
        (
            '{"schema_version": 1, "next_id": 3, "tasks": ['
            '{"id": 2, "title": "Read", "priority": "Urgent", '
            '"status": "Pending", "tags": []}]}'
        ),
    ],
)
def test_load_rejects_invalid_existing_data_without_overwriting(
    tmp_path: Path, contents: str
) -> None:
    task_file = tmp_path / "tasks.json"
    task_file.write_text(contents, encoding="utf-8")
    original_contents = task_file.read_bytes()

    with pytest.raises(StorageError, match="Task data file"):
        JsonTaskStore(task_file).load()

    assert task_file.read_bytes() == original_contents


def test_load_reports_read_errors_instead_of_returning_empty_tasks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_file = tmp_path / "tasks.json"
    task_file.write_text(
        '{"schema_version": 1, "next_id": 1, "tasks": []}', encoding="utf-8"
    )
    original_contents = task_file.read_bytes()
    original_read_text = Path.read_text

    def fail_read(
        path: Path, *args: object, **kwargs: object
    ) -> str:
        if path == task_file:
            raise PermissionError("simulated read failure")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_read)

    with pytest.raises(StorageError, match="Could not read task data file"):
        JsonTaskStore(task_file).load()
    assert task_file.read_bytes() == original_contents


def test_failed_replace_preserves_previous_file_and_cleans_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_file = tmp_path / "tasks.json"
    task_file.write_text(
        (
            '{"schema_version": 1, "next_id": 2, "tasks": ['
            '{"id": 1, "title": "Keep this task", "priority": "Medium", '
            '"status": "Pending", "tags": []}]}'
        ),
        encoding="utf-8",
    )
    original_contents = task_file.read_bytes()

    def fail_replace(
        source: str | os.PathLike[str], target: str | os.PathLike[str]
    ) -> None:
        raise PermissionError("simulated replace failure")

    monkeypatch.setattr(storage_module.os, "replace", fail_replace)

    with pytest.raises(StorageError, match="Could not save task data"):
        JsonTaskStore(task_file).save([], next_id=1)

    assert task_file.read_bytes() == original_contents
    assert list(tmp_path.iterdir()) == [task_file]
