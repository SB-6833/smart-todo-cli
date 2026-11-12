"""Task operations and persistence coordination."""

from smart_todo.models import Priority, Status, Task
from smart_todo.storage import JsonTaskStore
from smart_todo.validation import (
    normalize_tags,
    normalize_title,
    validate_positive_id,
    validate_priority,
    validate_status,
)

_PRIORITY_ORDER = {
    Priority.HIGH: 0,
    Priority.MEDIUM: 1,
    Priority.LOW: 2,
}


class TaskNotFoundError(LookupError):
    """Raised when an operation refers to a task that does not exist."""


class TaskService:
    """Manage tasks and persist each successful change."""

    def __init__(self, store: JsonTaskStore) -> None:
        self._store = store
        self._tasks, self._next_id = store.load()

    def add_task(
        self,
        title: object,
        tags: object = (),
        priority: object = Priority.MEDIUM,
        status: object = Status.PENDING,
    ) -> Task:
        """Validate, persist, and return a new task."""
        task = Task(
            id=self._next_id,
            title=normalize_title(title),
            priority=validate_priority(priority),
            status=validate_status(status),
            tags=normalize_tags(tags),
        )
        candidate_tasks = [*self._tasks, task]
        next_id = self._next_id + 1
        self._store.save(candidate_tasks, next_id)
        self._tasks = candidate_tasks
        self._next_id = next_id
        return task

    def list_tasks(self) -> list[Task]:
        """Return a separate list containing all current tasks."""
        return list(self._tasks)

    def filter_by_tag(self, tag: object) -> list[Task]:
        """Return tasks with one exact tag, ignoring letter case."""
        if not isinstance(tag, str):
            raise ValueError("Tag must be text.")
        normalized_tag = tag.strip().casefold()
        if not normalized_tag:
            raise ValueError("Tag cannot be empty.")

        return [
            task
            for task in self._tasks
            if any(existing_tag.casefold() == normalized_tag for existing_tag in task.tags)
        ]

    def sort_by_priority(self) -> list[Task]:
        """Return tasks in stable High, Medium, Low priority order."""
        return sorted(
            self._tasks,
            key=lambda task: _PRIORITY_ORDER[task.priority],
        )

    def update_task(self, task_id: object, **changes: object) -> Task:
        """Validate and persist field changes while retaining the task ID."""
        validated_id = validate_positive_id(task_id)
        task_index = self._find_task_index(validated_id)
        allowed_fields = {"title", "priority", "status", "tags"}
        invalid_fields = set(changes) - allowed_fields
        if invalid_fields:
            field_list = ", ".join(sorted(invalid_fields))
            raise ValueError(f"Unsupported task field(s): {field_list}.")
        if not changes:
            raise ValueError("Provide at least one task field to update.")

        current = self._tasks[task_index]
        updated = Task(
            id=current.id,
            title=normalize_title(changes.get("title", current.title)),
            priority=validate_priority(changes.get("priority", current.priority)),
            status=validate_status(changes.get("status", current.status)),
            tags=normalize_tags(changes.get("tags", current.tags)),
        )
        candidate_tasks = list(self._tasks)
        candidate_tasks[task_index] = updated
        self._store.save(candidate_tasks, self._next_id)
        self._tasks = candidate_tasks
        return updated

    def delete_task(self, task_id: object) -> Task:
        """Persist task removal and return the removed task."""
        validated_id = validate_positive_id(task_id)
        task_index = self._find_task_index(validated_id)
        deleted = self._tasks[task_index]
        candidate_tasks = [
            task for task in self._tasks if task.id != validated_id
        ]
        self._store.save(candidate_tasks, self._next_id)
        self._tasks = candidate_tasks
        return deleted

    def _find_task_index(self, task_id: int) -> int:
        for index, task in enumerate(self._tasks):
            if task.id == task_id:
                return index
        raise TaskNotFoundError(f"Task {task_id} was not found.")
