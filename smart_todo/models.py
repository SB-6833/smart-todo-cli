"""Data types used by Smart Todo."""

from dataclasses import dataclass
from enum import Enum


class Priority(str, Enum):
    """Supported task priorities."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Status(str, Enum):
    """Supported task statuses."""

    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


@dataclass(frozen=True)
class Task:
    """A validated task record."""

    id: int
    title: str
    priority: Priority = Priority.MEDIUM
    status: Status = Status.PENDING
    tags: tuple[str, ...] = ()

    def to_record(self) -> dict[str, int | str | list[str]]:
        """Return the JSON-compatible task representation."""
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority.value,
            "status": self.status.value,
            "tags": list(self.tags),
        }
