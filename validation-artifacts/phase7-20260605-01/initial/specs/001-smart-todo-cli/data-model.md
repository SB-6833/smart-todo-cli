# Smart Todo Data Model

**Status**: Approved technical decisions; Phase 2 models, validation, and storage are implemented. Service and CLI work has not started.
**Source**: [spec.md](./spec.md), especially FR-002–013.

## Task

| Field | Proposed type | Rules |
|---|---|---|
| `id` | Positive integer | Sequential, unique, and stable when updated. IDs are allocated from `next_id` and are never reused after deletion. |
| `title` | String | Required; trim surrounding whitespace; reject an empty or whitespace-only result. |
| `priority` | String enum | Exactly `High`, `Medium`, or `Low`; defaults to `Medium`. |
| `status` | String enum | Exactly `Pending`, `In Progress`, or `Completed`; defaults to `Pending`. Any status may transition to any other status. |
| `tags` | List of strings | Zero or more; trim each tag, discard empty entries, and treat case-insensitive duplicates as the same tag. |

Tasks have no parent/child relationship. Duplicate titles are allowed because the ID, not the title, identifies a task. Timestamps are not required by the specification and are not proposed for v1.

## JSON File Shape

The version-1 file is a JSON object:

```json
{
  "schema_version": 1,
  "next_id": 1,
  "tasks": []
}
```

Each entry in `tasks` contains the fields in the Task table. `next_id` is a sequential positive integer. An add receives its value; the counter advances only when the add is successfully persisted. Delete never decrements or resets the counter, so IDs are not reused after deletion.

The application supports `schema_version` 1. An unsupported version or invalid envelope is a clear load error; the application must not overwrite it with an empty list. Any later schema change requires a documented, tested migration that preserves user data.

## Validation and State Rules

- A missing file represents a first run and loads as an empty task collection.
- An existing file must parse as JSON and match the approved envelope and task shape. Invalid JSON, unsupported schema versions, duplicate IDs, or invalid field values are explicit load errors.
- A failed or invalid load must not be converted to an empty collection or saved over the existing file.
- A successful title update retains the task ID. A successful status update can move between any of the three allowed statuses.
- Filtering compares one selected tag to task tags exactly after normalization, ignoring letter case.
- Sorting uses `High`, `Medium`, `Low` order and is stable for ties. Filtering and sorting do not mutate saved task order.
- Add, update, and delete are successful only after the new complete state has been persisted.
- A cancelled delete and any rejected operation leave both in-memory and saved task state unchanged.
- Only one application instance may run at a time; v1 does not implement file locking.

## Persistence Boundary

The storage module owns serialization and disk errors. With the proposed package layout, its default path is `Path(__file__).resolve().parents[1] / "tasks.json"`, derived from the package location rather than the terminal's current working directory. The service supplies a complete candidate state and publishes it as current state only after the store confirms the write.

Tests inject a `tmp_path`-backed store or use an isolated temporary project copy. They must never read or write the real project-root `tasks.json`.
