"""Versioned JSON task-file storage."""

import json
import os
import tempfile
from collections.abc import Sequence
from pathlib import Path

from smart_todo.models import Task
from smart_todo.validation import (
    normalize_tags,
    normalize_title,
    task_from_record,
    validate_positive_id,
    validate_priority,
    validate_status,
)


class StorageError(Exception):
    """Raised when task data cannot be safely loaded or saved."""


def default_task_file_path() -> Path:
    """Return the project-level task file, independent of the current directory."""
    return Path(__file__).resolve().parents[1] / "tasks.json"


class JsonTaskStore:
    """Load and save task snapshots in the versioned JSON format."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_task_file_path()

    def load(self) -> tuple[list[Task], int]:
        """Return validated tasks and the next available ID."""
        try:
            contents = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return [], 1
        except OSError as exc:
            raise StorageError("Could not read task data file.") from exc
        except UnicodeError as exc:
            raise StorageError("Task data file is not valid UTF-8.") from exc

        try:
            data = json.loads(contents)
        except json.JSONDecodeError as exc:
            raise StorageError("Task data file contains invalid JSON.") from exc

        if not isinstance(data, dict) or set(data) != {
            "schema_version",
            "next_id",
            "tasks",
        }:
            raise StorageError("Task data file has an invalid envelope.")

        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise StorageError("Task data file uses an unsupported schema version.")

        next_id = data["next_id"]
        if type(next_id) is not int or next_id <= 0:
            raise StorageError("Task data file has an invalid next ID.")

        records = data["tasks"]
        if not isinstance(records, list):
            raise StorageError("Task data file has an invalid task list.")

        try:
            tasks = [task_from_record(record) for record in records]
        except ValueError as exc:
            raise StorageError("Task data file contains an invalid task.") from exc

        task_ids = [task.id for task in tasks]
        if len(task_ids) != len(set(task_ids)):
            raise StorageError("Task data file contains duplicate task IDs.")
        if task_ids and next_id <= max(task_ids):
            raise StorageError("Task data file next ID is not greater than saved IDs.")

        return tasks, next_id

    def save(self, tasks: Sequence[Task], next_id: int) -> None:
        """Atomically save a complete, validated task snapshot."""
        if not isinstance(tasks, Sequence) or isinstance(tasks, (str, bytes)):
            raise ValueError("Tasks must be provided as a list or tuple.")

        validated_tasks: list[Task] = []
        seen_ids: set[int] = set()
        for task in tasks:
            if not isinstance(task, Task):
                raise ValueError("Each saved item must be a Task.")

            validated_task = Task(
                id=validate_positive_id(task.id),
                title=normalize_title(task.title),
                priority=validate_priority(task.priority),
                status=validate_status(task.status),
                tags=normalize_tags(task.tags),
            )
            if validated_task.id in seen_ids:
                raise ValueError("Task IDs must be unique.")
            seen_ids.add(validated_task.id)
            validated_tasks.append(validated_task)

        validate_positive_id(next_id)
        if seen_ids and next_id <= max(seen_ids):
            raise ValueError("Next task ID must be greater than saved task IDs.")

        document = {
            "schema_version": 1,
            "next_id": next_id,
            "tasks": [task.to_record() for task in validated_tasks],
        }
        serialized = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(serialized)
                temporary_file.flush()

            os.replace(temporary_path, self.path)
            temporary_path = None
        except (OSError, UnicodeError) as exc:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError as cleanup_error:
                    raise StorageError(
                        "Could not save task data or clean up its temporary file."
                    ) from cleanup_error
            raise StorageError("Could not save task data.") from exc
