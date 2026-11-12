"""Input and persisted-record validation for Smart Todo."""

from smart_todo.models import Priority, Status, Task


def normalize_title(value: object) -> str:
    """Trim a title and reject blank or non-string values."""
    if not isinstance(value, str):
        raise ValueError("Title must be text.")

    title = value.strip()
    if not title:
        raise ValueError("Title cannot be empty.")
    return title


def normalize_tags(values: object) -> tuple[str, ...]:
    """Trim tags, discard blanks, and keep the first case-insensitive occurrence."""
    if not isinstance(values, (list, tuple)):
        raise ValueError("Tags must be a list of text values.")

    tags: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise ValueError("Each tag must be text.")

        tag = value.strip()
        if not tag:
            continue

        key = tag.casefold()
        if key not in seen:
            tags.append(tag)
            seen.add(key)

    return tuple(tags)


def validate_priority(value: object) -> Priority:
    """Return a supported priority or raise a clear validation error."""
    if isinstance(value, Priority):
        return value
    if not isinstance(value, str):
        raise ValueError("Priority must be High, Medium, or Low.")

    try:
        return Priority(value)
    except ValueError as exc:
        raise ValueError("Priority must be High, Medium, or Low.") from exc


def validate_status(value: object) -> Status:
    """Return a supported status or raise a clear validation error."""
    if isinstance(value, Status):
        return value
    if not isinstance(value, str):
        raise ValueError("Status must be Pending, In Progress, or Completed.")

    try:
        return Status(value)
    except ValueError as exc:
        raise ValueError("Status must be Pending, In Progress, or Completed.") from exc


def validate_positive_id(value: object) -> int:
    """Accept positive integers but not booleans or numeric strings."""
    if type(value) is not int or value <= 0:
        raise ValueError("Task ID must be a positive integer.")
    return value


def task_from_record(record: object) -> Task:
    """Validate a JSON task object and convert it to a Task."""
    expected_fields = {"id", "title", "priority", "status", "tags"}
    if not isinstance(record, dict) or set(record) != expected_fields:
        raise ValueError("Task record has an invalid shape.")

    return Task(
        id=validate_positive_id(record["id"]),
        title=normalize_title(record["title"]),
        priority=validate_priority(record["priority"]),
        status=validate_status(record["status"]),
        tags=normalize_tags(record["tags"]),
    )
