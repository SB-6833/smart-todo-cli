import pytest

from smart_todo.models import Priority, Status, Task
from smart_todo.validation import (
    normalize_tags,
    normalize_title,
    task_from_record,
    validate_positive_id,
    validate_priority,
    validate_status,
)


def test_normalize_title_trims_surrounding_whitespace() -> None:
    assert normalize_title("  Write documentation \t") == "Write documentation"


@pytest.mark.parametrize("title", ["", "  ", "\t\n", None, 42])
def test_normalize_title_rejects_blank_or_non_string_values(title: object) -> None:
    with pytest.raises(ValueError):
        normalize_title(title)


def test_normalize_tags_trims_discards_empty_and_deduplicates_case_insensitively() -> None:
    assert normalize_tags([" Work ", "work", "", "  ", "Personal"]) == (
        "Work",
        "Personal",
    )


def test_normalize_tags_accepts_no_tags() -> None:
    assert normalize_tags([]) == ()


@pytest.mark.parametrize("tags", ["work", None, ["work", 7]])
def test_normalize_tags_rejects_invalid_containers_or_values(tags: object) -> None:
    with pytest.raises(ValueError):
        normalize_tags(tags)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("High", Priority.HIGH),
        ("Medium", Priority.MEDIUM),
        ("Low", Priority.LOW),
    ],
)
def test_validate_priority_accepts_only_supported_values(
    value: str, expected: Priority
) -> None:
    assert validate_priority(value) is expected


@pytest.mark.parametrize("value", ["urgent", " high", "", None])
def test_validate_priority_rejects_unsupported_values(value: object) -> None:
    with pytest.raises(ValueError):
        validate_priority(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Pending", Status.PENDING),
        ("In Progress", Status.IN_PROGRESS),
        ("Completed", Status.COMPLETED),
    ],
)
def test_validate_status_accepts_only_supported_values(
    value: str, expected: Status
) -> None:
    assert validate_status(value) is expected


@pytest.mark.parametrize("value", ["Started", "pending", "", None])
def test_validate_status_rejects_unsupported_values(value: object) -> None:
    with pytest.raises(ValueError):
        validate_status(value)


@pytest.mark.parametrize(("value", "expected"), [(1, 1), (12, 12)])
def test_validate_positive_id_accepts_positive_integers(
    value: int, expected: int
) -> None:
    assert validate_positive_id(value) == expected


@pytest.mark.parametrize("value", [0, -1, True, "1", None])
def test_validate_positive_id_rejects_invalid_values(value: object) -> None:
    with pytest.raises(ValueError):
        validate_positive_id(value)


def test_task_from_record_builds_a_validated_task() -> None:
    record = {
        "id": 3,
        "title": "  Read a book ",
        "priority": "High",
        "status": "In Progress",
        "tags": [" Home ", "home", "Reading"],
    }

    assert task_from_record(record) == Task(
        id=3,
        title="Read a book",
        priority=Priority.HIGH,
        status=Status.IN_PROGRESS,
        tags=("Home", "Reading"),
    )


@pytest.mark.parametrize(
    "record",
    [
        {"id": 1, "title": "Read", "priority": "High", "status": "Pending"},
        {
            "id": 1,
            "title": "Read",
            "priority": "High",
            "status": "Pending",
            "tags": [],
            "extra": "not supported",
        },
        "not a task record",
    ],
)
def test_task_from_record_rejects_invalid_record_shapes(record: object) -> None:
    with pytest.raises(ValueError):
        task_from_record(record)
