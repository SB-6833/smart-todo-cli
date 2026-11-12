from pathlib import Path

import pytest

from smart_todo.models import Priority, Status, Task
from smart_todo.service import TaskNotFoundError, TaskService
from smart_todo.storage import JsonTaskStore, StorageError


def make_service(tmp_path: Path) -> tuple[TaskService, JsonTaskStore]:
    store = JsonTaskStore(tmp_path / "tasks.json")
    return TaskService(store), store


def test_add_uses_unique_ids_defaults_and_persists_normalized_values(
    tmp_path: Path,
) -> None:
    service, store = make_service(tmp_path)

    first = service.add_task("  Read a book ", tags=[" Home ", "home"])
    second = service.add_task("Write a summary")

    assert first == Task(
        id=1,
        title="Read a book",
        priority=Priority.MEDIUM,
        status=Status.PENDING,
        tags=("Home",),
    )
    assert second.id == 2
    assert second.priority is Priority.MEDIUM
    assert second.status is Status.PENDING
    assert store.load() == ([first, second], 3)


def test_list_tasks_returns_all_saved_fields(tmp_path: Path) -> None:
    service, _ = make_service(tmp_path)
    task = service.add_task(
        "Prepare notes",
        tags=["study"],
        priority=Priority.HIGH,
        status=Status.IN_PROGRESS,
    )

    returned_tasks = service.list_tasks()
    assert returned_tasks == [task]
    returned_tasks.clear()
    assert service.list_tasks() == [task]


def test_filter_by_tag_matches_exactly_ignoring_case_and_whitespace(
    tmp_path: Path,
) -> None:
    service, store = make_service(tmp_path)
    home_task = service.add_task("Home task", tags=["Home"])
    home_office_task = service.add_task("Home office task", tags=["Home office"])
    lowercase_home_task = service.add_task("Another home task", tags=["home"])
    original_bytes = store.path.read_bytes()

    matching_tasks = service.filter_by_tag("  hOmE ")

    assert matching_tasks == [home_task, lowercase_home_task]
    assert service.list_tasks() == [
        home_task,
        home_office_task,
        lowercase_home_task,
    ]
    assert store.path.read_bytes() == original_bytes


def test_filter_by_tag_returns_empty_list_when_there_are_no_matches(
    tmp_path: Path,
) -> None:
    service, _ = make_service(tmp_path)
    service.add_task("Home task", tags=["Home"])

    assert service.filter_by_tag("missing") == []


def test_sort_by_priority_is_stable_and_does_not_change_saved_order(
    tmp_path: Path,
) -> None:
    service, store = make_service(tmp_path)
    low_first = service.add_task("Low first", priority=Priority.LOW)
    high_first = service.add_task("High first", priority=Priority.HIGH)
    medium = service.add_task("Medium", priority=Priority.MEDIUM)
    high_second = service.add_task("High second", priority=Priority.HIGH)
    low_second = service.add_task("Low second", priority=Priority.LOW)
    original_tasks = [low_first, high_first, medium, high_second, low_second]
    original_bytes = store.path.read_bytes()

    sorted_tasks = service.sort_by_priority()

    assert sorted_tasks == [high_first, high_second, medium, low_first, low_second]
    assert service.list_tasks() == original_tasks
    assert store.load() == (original_tasks, 6)
    assert store.path.read_bytes() == original_bytes


def test_saved_tasks_are_available_to_a_reopened_service(tmp_path: Path) -> None:
    store = JsonTaskStore(tmp_path / "tasks.json")
    service = TaskService(store)
    original = service.add_task(
        "Persisted task",
        tags=["Home"],
        priority=Priority.HIGH,
        status=Status.IN_PROGRESS,
    )
    updated = service.update_task(original.id, title="Updated persisted task")

    reopened_service = TaskService(JsonTaskStore(store.path))

    assert reopened_service.list_tasks() == [updated]


def test_update_changes_requested_fields_and_preserves_id(
    tmp_path: Path,
) -> None:
    service, store = make_service(tmp_path)
    original = service.add_task("Draft", tags=["work"])

    updated = service.update_task(
        original.id,
        title="  Final draft ",
        priority="High",
        tags=[" work ", "Review"],
        status="Completed",
    )

    assert updated == Task(
        id=original.id,
        title="Final draft",
        priority=Priority.HIGH,
        status=Status.COMPLETED,
        tags=("work", "Review"),
    )
    assert service.list_tasks() == [updated]
    assert store.load() == ([updated], 2)


def test_update_of_one_field_preserves_the_other_fields(tmp_path: Path) -> None:
    service, _ = make_service(tmp_path)
    original = service.add_task(
        "Plan a lesson",
        tags=["school"],
        priority=Priority.HIGH,
        status=Status.IN_PROGRESS,
    )

    updated = service.update_task(original.id, title="Plan the lesson")

    assert updated == Task(
        id=original.id,
        title="Plan the lesson",
        priority=Priority.HIGH,
        status=Status.IN_PROGRESS,
        tags=("school",),
    )


@pytest.mark.parametrize(
    ("starting_status", "target_status"),
    [
        (starting_status, target_status)
        for starting_status in Status
        for target_status in Status
    ],
)
def test_any_supported_status_can_transition_to_any_other(
    tmp_path: Path,
    starting_status: Status,
    target_status: Status,
) -> None:
    service, store = make_service(tmp_path)
    original = service.add_task("Status transition", status=starting_status)

    updated = service.update_task(original.id, status=target_status)

    assert updated.id == original.id
    assert updated.status is target_status
    assert store.load() == ([updated], 2)


def test_delete_persists_removal_without_reusing_the_deleted_id(
    tmp_path: Path,
) -> None:
    service, store = make_service(tmp_path)
    first = service.add_task("First")

    deleted = service.delete_task(first.id)
    replacement = service.add_task("Replacement")

    assert deleted == first
    assert replacement.id == 2
    assert store.load() == ([replacement], 3)


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_missing_task_id_does_not_change_memory_or_disk(
    tmp_path: Path, operation: str
) -> None:
    service, store = make_service(tmp_path)
    existing = service.add_task("Keep this task")
    original_bytes = store.path.read_bytes()

    with pytest.raises(TaskNotFoundError):
        if operation == "update":
            service.update_task(99, title="Changed")
        else:
            service.delete_task(99)

    assert service.list_tasks() == [existing]
    assert store.path.read_bytes() == original_bytes


@pytest.mark.parametrize("task_id", [0, -1, True, "1"])
@pytest.mark.parametrize("operation", ["update", "delete"])
def test_invalid_task_ids_are_rejected_without_changing_state(
    tmp_path: Path, operation: str, task_id: object
) -> None:
    service, store = make_service(tmp_path)
    existing = service.add_task("Keep this task")
    original_bytes = store.path.read_bytes()

    with pytest.raises(ValueError, match="positive integer"):
        if operation == "update":
            service.update_task(task_id, title="Changed")
        else:
            service.delete_task(task_id)

    assert service.list_tasks() == [existing]
    assert store.path.read_bytes() == original_bytes


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", " \t "),
        ("priority", "Urgent"),
        ("status", "Started"),
        ("tags", ["valid", 7]),
    ],
)
def test_invalid_updates_do_not_change_task_or_file(
    tmp_path: Path, field: str, value: object
) -> None:
    service, store = make_service(tmp_path)
    existing = service.add_task("Keep this task", tags=["home"])
    original_bytes = store.path.read_bytes()

    with pytest.raises(ValueError):
        service.update_task(existing.id, **{field: value})

    assert service.list_tasks() == [existing]
    assert store.path.read_bytes() == original_bytes


def test_save_failure_does_not_publish_a_delete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, store = make_service(tmp_path)
    existing = service.add_task("Keep this task")
    original_bytes = store.path.read_bytes()

    def fail_save(tasks: object, next_id: int) -> None:
        raise StorageError("simulated save failure")

    monkeypatch.setattr(store, "save", fail_save)

    with pytest.raises(StorageError, match="simulated save failure"):
        service.delete_task(existing.id)

    assert service.list_tasks() == [existing]
    assert store.path.read_bytes() == original_bytes


def test_blank_title_is_rejected_when_adding(tmp_path: Path) -> None:
    service, store = make_service(tmp_path)

    with pytest.raises(ValueError):
        service.add_task(" \n ")

    assert service.list_tasks() == []
    assert not store.path.exists()


def test_save_failure_does_not_publish_an_add_or_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, store = make_service(tmp_path)
    existing = service.add_task("Keep this task")
    original_bytes = store.path.read_bytes()

    def fail_save(tasks: object, next_id: int) -> None:
        raise StorageError("simulated save failure")

    monkeypatch.setattr(store, "save", fail_save)

    with pytest.raises(StorageError, match="simulated save failure"):
        service.update_task(existing.id, title="Not committed")
    assert service.list_tasks() == [existing]
    assert store.path.read_bytes() == original_bytes

    with pytest.raises(StorageError, match="simulated save failure"):
        service.add_task("Also not committed")
    assert service.list_tasks() == [existing]
    assert store.path.read_bytes() == original_bytes
