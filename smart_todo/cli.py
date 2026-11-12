"""Command-line interaction for Smart Todo."""

from collections.abc import Callable

from smart_todo.models import Task
from smart_todo.service import TaskNotFoundError, TaskService
from smart_todo.storage import StorageError
from smart_todo.validation import validate_positive_id


def run_cli(
    service: TaskService,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    """Run the numbered menu with injectable terminal input and output."""
    while True:
        output_fn("Smart Todo")
        output_fn("1. Add task")
        output_fn("2. View all tasks")
        output_fn("3. Update task")
        output_fn("4. Delete task")
        output_fn("5. Filter by tag")
        output_fn("6. Sort by priority")
        output_fn("0. Exit")

        try:
            choice = input_fn("Choose an option: ").strip()
        except EOFError:
            output_fn("Input ended. Exiting Smart Todo.")
            return

        if choice == "0":
            output_fn("Goodbye.")
            return
        if choice == "1":
            _add_task(service, input_fn, output_fn)
        elif choice == "2":
            _view_tasks(service, output_fn)
        elif choice == "3":
            _update_task(service, input_fn, output_fn)
        elif choice == "4":
            _delete_task(service, input_fn, output_fn)
        elif choice == "5":
            _filter_tasks_by_tag(service, input_fn, output_fn)
        elif choice == "6":
            _sort_tasks_by_priority(service, output_fn)
        else:
            output_fn("Error: Choose 0, 1, 2, 3, 4, 5, or 6.")


def _add_task(
    service: TaskService,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    try:
        title = input_fn("Title: ")
        raw_tags = input_fn("Tags (comma-separated, optional): ")
        task = service.add_task(title, tags=raw_tags.split(","))
    except (ValueError, StorageError) as exc:
        output_fn(f"Error: {exc}")
        return
    output_fn(f"Added task {task.id}.")


def _view_tasks(
    service: TaskService, output_fn: Callable[[str], None]
) -> None:
    tasks = service.list_tasks()
    if not tasks:
        output_fn("No tasks found.")
        return
    for task in tasks:
        output_fn(_format_task(task))


def _filter_tasks_by_tag(
    service: TaskService,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    try:
        tag = input_fn("Tag to filter by: ")
        tasks = service.filter_by_tag(tag)
    except ValueError as exc:
        output_fn(f"Error: {exc}")
        return

    if not tasks:
        output_fn(f"No tasks match tag '{tag.strip()}'.")
        return
    output_fn(f"Tasks matching tag '{tag.strip()}':")
    for task in tasks:
        output_fn(_format_task(task))


def _sort_tasks_by_priority(
    service: TaskService, output_fn: Callable[[str], None]
) -> None:
    tasks = service.sort_by_priority()
    if not tasks:
        output_fn("No tasks found.")
        return
    output_fn("Tasks sorted by priority:")
    for task in tasks:
        output_fn(_format_task(task))


def _update_task(
    service: TaskService,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    try:
        task_id = _read_task_id(input_fn("Task ID to update: "))
        _find_task(service, task_id)
        output_fn("Choose a field to update:")
        output_fn("1. Title")
        output_fn("2. Priority")
        output_fn("3. Tags")
        output_fn("4. Status")
        field_choice = input_fn("Field: ").strip()

        field_prompts: dict[str, tuple[str, str]] = {
            "1": ("title", "New title: "),
            "2": ("priority", "Priority (High, Medium, Low): "),
            "3": ("tags", "Tags (comma-separated): "),
            "4": (
                "status",
                "Status (Pending, In Progress, Completed): ",
            ),
        }
        selected_field = field_prompts.get(field_choice)
        if selected_field is None:
            raise ValueError("Choose field 1, 2, 3, or 4.")

        field, prompt = selected_field
        value = input_fn(prompt)
        if field == "tags":
            value = value.split(",")
        task = service.update_task(task_id, **{field: value})
    except (ValueError, TaskNotFoundError, StorageError) as exc:
        output_fn(f"Error: {exc}")
        return
    output_fn(f"Updated task {task.id}.")


def _delete_task(
    service: TaskService,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    try:
        task_id = _read_task_id(input_fn("Task ID to delete: "))
        task = _find_task(service, task_id)
        output_fn(f"Delete task {task.id}: {task.title}? (y/n)")
        confirmation = input_fn("Confirm deletion: ").strip().casefold()
        if confirmation in {"n", "no"}:
            output_fn("Deletion cancelled.")
            return
        if confirmation not in {"y", "yes"}:
            raise ValueError("Enter y or n to confirm deletion.")
        deleted = service.delete_task(task_id)
    except (ValueError, TaskNotFoundError, StorageError) as exc:
        output_fn(f"Error: {exc}")
        return
    output_fn(f"Deleted task {deleted.id}.")


def _read_task_id(value: str) -> int:
    try:
        parsed_id = int(value)
    except ValueError as exc:
        raise ValueError("Task ID must be a positive integer.") from exc
    return validate_positive_id(parsed_id)


def _find_task(service: TaskService, task_id: int) -> Task:
    for task in service.list_tasks():
        if task.id == task_id:
            return task
    raise TaskNotFoundError(f"Task {task_id} was not found.")


def _format_task(task: Task) -> str:
    tags = ", ".join(task.tags) if task.tags else "None"
    return (
        f"ID: {task.id} | Title: {task.title} | "
        f"Priority: {task.priority.value} | Status: {task.status.value} | "
        f"Tags: {tags}"
    )
