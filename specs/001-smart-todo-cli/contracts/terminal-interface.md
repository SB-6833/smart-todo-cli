# Terminal Interface Contract

**Status**: Proposed interaction contract based on the approved feature specification.

## Main Menu

Present a numbered menu that makes each supported action visible:

1. Add task
2. View all tasks
3. Update task
4. Delete task
5. Filter by tag
6. Sort by priority
0. Exit

Invalid menu choices produce a clear error and do not change task data. The menu is shown again after an operation unless the user chooses Exit; exiting displays a clear goodbye message.

## Operations

### Add

- Prompt for a title; reject blank or whitespace-only input.
- Allow zero or more tags.
- Offer High, Medium, and Low priorities; default to Medium.
- Use Pending as the initial status.
- On successful persistence, show a success message and the new task ID.
- On validation or storage failure, show an error and do not claim success.

### View

Display each task's ID, title, priority, tags, and status. If the list is empty, explain that there are no tasks yet.

### Update

- Ask for a task ID and report a clear error if it does not exist.
- Offer title, priority, tags, and status as editable fields.
- Validate the proposed value and keep the existing task unchanged if the input is invalid or persistence fails.
- Preserve the task ID.

### Delete

- Ask for a task ID and report a clear error if it does not exist.
- Require explicit confirmation before removing it.
- If the user cancels, keep the task unchanged and show a cancellation message.

### Filter by tag

- Ask for one tag.
- Match the full normalized tag, ignoring letter case; do not perform substring matching.
- Display matching tasks or explain that none match.

### Sort by priority

- Display tasks in High, Medium, Low order.
- Preserve relative order among tasks with equal priority.
- Sorting is a display operation and does not change the stored task order.

## Feedback and Privacy

Each operation communicates success, error, or cancellation in plain language. Errors must not include secrets or task contents. Do not print full operating-system paths or raw exception tracebacks in normal user-facing messages.

## Persistence Expectations

Successful add, update, and delete operations are saved before success is shown. The application stores `tasks.json` at the project-level path resolved from the package location, independent of the terminal's current working directory. The project `.gitignore` excludes `/tasks.json`.

A missing task file is treated as an empty first-run list. An existing malformed, invalid, unreadable, or unsavable file results in a clear error and is not silently replaced. The versioned JSON object contains `schema_version`, `next_id`, and `tasks`; sequential positive integer IDs are not reused after deletion.

Only one application instance may run at a time. A second simultaneous instance is unsupported in v1; no file locking is used.
