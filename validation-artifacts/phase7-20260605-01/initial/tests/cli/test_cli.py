from pathlib import Path

import pytest

from smart_todo.cli import run_cli
from smart_todo.models import Priority, Status, Task
from smart_todo.service import TaskService
from smart_todo.storage import JsonTaskStore, StorageError


def make_service(tmp_path: Path) -> tuple[TaskService, JsonTaskStore]:
    store = JsonTaskStore(tmp_path / "tasks.json")
    return TaskService(store), store


def run_with_inputs(service: TaskService, responses: list[str]) -> str:
    answers = iter(responses)
    output: list[str] = []

    def read_input(prompt: str) -> str:
        output.append(prompt)
        return next(answers)

    run_cli(service, input_fn=read_input, output_fn=output.append)
    return "\n".join(output)


def test_numbered_menu_exposes_crud_filter_and_sort_operations(
    tmp_path: Path,
) -> None:
    service, _ = make_service(tmp_path)

    output = run_with_inputs(service, ["0"])

    assert "1. Add task" in output
    assert "2. View all tasks" in output
    assert "3. Update task" in output
    assert "4. Delete task" in output
    assert "5. Filter by tag" in output
    assert "6. Sort by priority" in output
    assert "0. Exit" in output


def test_filter_by_tag_displays_only_exact_case_insensitive_matches(
    tmp_path: Path,
) -> None:
    service, _ = make_service(tmp_path)
    service.add_task("Home task", tags=["Home"])
    service.add_task("Home office task", tags=["Home office"])
    service.add_task("Another home task", tags=["home"])
    service.add_task("Office task", tags=["Office"])

    output = run_with_inputs(service, ["5", " hOmE ", "0"])

    display_lines = [
        line for line in output.splitlines() if line.startswith("ID: ")
    ]
    assert display_lines == [
        "ID: 1 | Title: Home task | Priority: Medium | Status: Pending | Tags: Home",
        "ID: 3 | Title: Another home task | Priority: Medium | Status: Pending | Tags: home",
    ]


def test_filter_with_no_matches_gives_clear_feedback(tmp_path: Path) -> None:
    service, store = make_service(tmp_path)
    existing = service.add_task("Home task", tags=["Home"])
    original_bytes = store.path.read_bytes()

    output = run_with_inputs(service, ["5", "missing", "0"])

    assert "No tasks match tag 'missing'." in output
    assert service.list_tasks() == [existing]
    assert store.path.read_bytes() == original_bytes


def test_filter_success_identifies_the_matching_tag(tmp_path: Path) -> None:
    service, _ = make_service(tmp_path)
    service.add_task("Home task", tags=["Home"])

    output = run_with_inputs(service, ["5", "home", "0"])

    assert "Tasks matching tag 'home':" in output
    assert "ID: 1" in output


def test_sort_by_priority_displays_stably_without_changing_saved_order(
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

    output = run_with_inputs(service, ["6", "0"])

    displayed_ids = [
        line.split("|", maxsplit=1)[0].strip()
        for line in output.splitlines()
        if line.startswith("ID: ")
    ]
    assert displayed_ids == ["ID: 2", "ID: 4", "ID: 3", "ID: 1", "ID: 5"]
    assert service.list_tasks() == original_tasks
    assert store.load() == (original_tasks, 6)
    assert store.path.read_bytes() == original_bytes


def test_blank_filter_tag_is_rejected_without_changing_saved_data(
    tmp_path: Path,
) -> None:
    service, store = make_service(tmp_path)
    existing = service.add_task("Home task", tags=["Home"])
    original_bytes = store.path.read_bytes()

    output = run_with_inputs(service, ["5", "  ", "0"])

    assert "Error:" in output
    assert service.list_tasks() == [existing]
    assert store.path.read_bytes() == original_bytes


def test_add_and_view_prompt_and_display_all_task_fields(tmp_path: Path) -> None:
    service, _ = make_service(tmp_path)

    output = run_with_inputs(
        service,
        ["1", "Read a book", "Home, Reading", "2", "0"],
    )

    assert "Title:" in output
    assert "Tags" in output
    assert "Added task 1" in output
    assert "ID: 1" in output
    assert "Read a book" in output
    assert "Medium" in output
    assert "Pending" in output
    assert "Home, Reading" in output


def test_add_reports_success_only_after_saved_data_is_readable(
    tmp_path: Path,
) -> None:
    service, store = make_service(tmp_path)
    answers = iter(["1", "Saved before success", "", "0"])
    outputs: list[str] = []

    def output_and_check_persistence(message: str) -> None:
        outputs.append(message)
        if message.startswith("Added task"):
            assert store.load() == ([Task(id=1, title="Saved before success")], 2)

    run_cli(
        service,
        input_fn=lambda prompt: next(answers),
        output_fn=output_and_check_persistence,
    )

    assert "Added task 1." in outputs


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_update_and_delete_report_success_only_after_persistence(
    tmp_path: Path, operation: str
) -> None:
    service, store = make_service(tmp_path)
    original = service.add_task("Existing")
    if operation == "update":
        expected_saved_tasks = [
            Task(
                id=original.id,
                title="Updated",
                priority=Priority.MEDIUM,
                status=Status.PENDING,
            )
        ]
        success_message = "Updated task 1."
        responses = ["3", "1", "1", "Updated", "0"]
    else:
        expected_saved_tasks = []
        success_message = "Deleted task 1."
        responses = ["4", "1", "y", "0"]
    outputs: list[str] = []
    answers = iter(responses)

    def output_and_check_persistence(message: str) -> None:
        outputs.append(message)
        if message == success_message:
            assert store.load() == (expected_saved_tasks, 2)

    run_cli(
        service,
        input_fn=lambda prompt: next(answers),
        output_fn=output_and_check_persistence,
    )

    assert success_message in outputs


def test_update_prompts_for_each_editable_field_and_preserves_task_id(
    tmp_path: Path,
) -> None:
    service, _ = make_service(tmp_path)
    original = service.add_task("Draft", tags=["work"])

    output = run_with_inputs(
        service,
        [
            "3",
            "1",
            "1",
            "Final draft",
            "3",
            "1",
            "2",
            "High",
            "3",
            "1",
            "3",
            "work, review",
            "3",
            "1",
            "4",
            "Completed",
            "0",
        ],
    )

    updated = service.list_tasks()[0]
    assert updated == Task(
        id=original.id,
        title="Final draft",
        priority=Priority.HIGH,
        status=Status.COMPLETED,
        tags=("work", "review"),
    )
    assert "1. Title" in output
    assert "2. Priority" in output
    assert "3. Tags" in output
    assert "4. Status" in output
    assert "Updated task 1" in output


def test_empty_list_view_and_sort_explain_that_there_are_no_tasks(
    tmp_path: Path,
) -> None:
    service, _ = make_service(tmp_path)

    output = run_with_inputs(service, ["2", "6", "0"])

    assert output.count("No tasks found.") == 2


def test_delete_cancel_leaves_task_unchanged(tmp_path: Path) -> None:
    service, store = make_service(tmp_path)
    task = service.add_task("Keep until confirmed")
    original_bytes = store.path.read_bytes()

    output = run_with_inputs(
        service,
        ["4", "1", "n", "0"],
    )

    assert "Deletion cancelled" in output
    assert service.list_tasks() == [task]
    assert store.path.read_bytes() == original_bytes


def test_delete_confirmation_removes_task(tmp_path: Path) -> None:
    service, store = make_service(tmp_path)
    service.add_task("Delete after confirmation")

    output = run_with_inputs(service, ["4", "1", "y", "0"])

    assert "Deleted task 1" in output
    assert service.list_tasks() == []
    assert store.load() == ([], 2)


def test_invalid_menu_choice_and_missing_ids_are_reported(
    tmp_path: Path,
) -> None:
    service, store = make_service(tmp_path)
    existing = service.add_task("Keep this task")
    original_bytes = store.path.read_bytes()

    output = run_with_inputs(service, ["8", "3", "99", "4", "99", "0"])

    assert "Error: Choose 0, 1, 2, 3, 4, 5, or 6." in output
    assert output.count("Error: Task 99 was not found.") == 2
    assert service.list_tasks() == [existing]
    assert store.path.read_bytes() == original_bytes


def test_invalid_priority_and_blank_title_leave_saved_data_unchanged(
    tmp_path: Path,
) -> None:
    service, store = make_service(tmp_path)
    original = service.add_task("Existing")
    original_bytes = store.path.read_bytes()

    output = run_with_inputs(
        service,
        ["3", "1", "2", "Urgent", "1", "  ", "", "0"],
    )

    assert output.count("Error:") >= 2
    assert "Error: Priority must be High, Medium, or Low." in output
    assert "Error: Title cannot be empty." in output
    assert service.list_tasks() == [original]
    assert store.path.read_bytes() == original_bytes


def test_invalid_status_is_reported_without_changing_saved_data(
    tmp_path: Path,
) -> None:
    service, store = make_service(tmp_path)
    original = service.add_task("Existing")
    original_bytes = store.path.read_bytes()

    output = run_with_inputs(service, ["3", "1", "4", "Started", "0"])

    assert "Error: Status must be Pending, In Progress, or Completed." in output
    assert "Updated task 1" not in output
    assert service.list_tasks() == [original]
    assert store.path.read_bytes() == original_bytes


@pytest.mark.parametrize("operation", ["add", "update", "delete"])
def test_save_failures_are_reported_without_changing_saved_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    service, store = make_service(tmp_path)
    existing = service.add_task("Private existing task")
    original_bytes = store.path.read_bytes()

    def fail_save(tasks: object, next_id: int) -> None:
        raise StorageError("Could not save task data.")

    monkeypatch.setattr(store, "save", fail_save)
    responses = {
        "add": ["1", "New task", "", "0"],
        "update": ["3", "1", "1", "Changed task", "0"],
        "delete": ["4", "1", "y", "0"],
    }[operation]

    output = run_with_inputs(service, responses)
    error_messages = [
        message for message in output.splitlines() if message.startswith("Error:")
    ]

    assert error_messages == ["Error: Could not save task data."]
    assert "Private existing task" not in error_messages[0]
    assert not any(
        message.startswith(("Added task", "Updated task", "Deleted task"))
        for message in output.splitlines()
    )
    assert service.list_tasks() == [existing]
    assert store.path.read_bytes() == original_bytes


def test_unexpected_errors_are_not_silently_swallowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _ = make_service(tmp_path)

    def fail_add(title: object, **kwargs: object) -> Task:
        raise RuntimeError("unexpected service failure")

    monkeypatch.setattr(service, "add_task", fail_add)

    with pytest.raises(RuntimeError, match="unexpected service failure"):
        run_with_inputs(service, ["1", "Task", "", "0"])
