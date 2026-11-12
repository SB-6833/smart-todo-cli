"""Launch the Smart Todo command-line application."""

import sys

from smart_todo.cli import run_cli
from smart_todo.service import TaskService
from smart_todo.storage import JsonTaskStore, StorageError


def main() -> int:
    try:
        service = TaskService(JsonTaskStore())
    except StorageError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    run_cli(service)
    return 0


if __name__ == "__main__":
    sys.exit(main())
