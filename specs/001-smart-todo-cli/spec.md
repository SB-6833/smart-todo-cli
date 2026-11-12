# Feature Specification: Smart Todo CLI

**Feature Branch**: Not applicable (the workspace is not a Git repository)

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: Build a beginner-friendly Python terminal todo application with task management, priorities, tags, status tracking, priority sorting, and JSON persistence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manage Tasks (Priority: P1)

As a user, I want to add, view, update, and delete tasks so I can keep a clear and current list of things to do.

**Why this priority**: Task management is the core value of the application.

**Independent Test**: Add a task, view it, update its details, and delete it; confirm the displayed task reflects each change and is absent after deletion.

**Acceptance Scenarios**:

1. **Given** the task list is empty, **When** I add a task with a title, **Then** it appears with a unique ID, Medium priority, Pending status, and any supplied tags.
2. **Given** a task exists, **When** I view the task list, **Then** I can see its ID, title, priority, tags, and status.
3. **Given** a task exists, **When** I update its title, priority, tags, or status, **Then** the selected details change and its ID remains the same.
4. **Given** a task exists, **When** I confirm its deletion, **Then** it is removed from the task list.
5. **Given** I am asked to confirm deletion, **When** I cancel, **Then** the task remains unchanged.

### User Story 2 - Find and Prioritize Tasks (Priority: P2)

As a user, I want to filter tasks by a tag and sort them by priority so I can focus on relevant and more important work.

**Why this priority**: Filtering and sorting make a growing task list easier to use.

**Independent Test**: Create tasks with different tags and priorities; verify that filtering shows only matching tasks and sorting orders them High, Medium, then Low.

**Acceptance Scenarios**:

1. **Given** tasks have different tags, **When** I filter by one tag, **Then** only tasks with that exact tag are shown, regardless of letter case.
2. **Given** tasks have different priorities, **When** I sort by priority, **Then** High tasks appear before Medium tasks, which appear before Low tasks.
3. **Given** multiple tasks have the same priority, **When** I sort by priority, **Then** those tasks retain their existing relative order.
4. **Given** no task has the selected tag, **When** I filter by that tag, **Then** I see a clear message that there are no matching tasks.

### User Story 3 - Continue After Restart (Priority: P1)

As a user, I want my tasks to remain available after closing and reopening the application so I do not lose my work.

**Why this priority**: Persistence is essential for a todo list users rely on over time.

**Independent Test**: Add and update tasks, close and reopen the application, and confirm their IDs and details are preserved.

**Acceptance Scenarios**:

1. **Given** tasks have been saved, **When** I reopen the application, **Then** all saved tasks and their details are available.
2. **Given** no task data file exists yet, **When** I start the application, **Then** I can use it with an empty task list.
3. **Given** the task data cannot be read or saved, **When** an operation encounters that problem, **Then** I receive a clear error and existing saved data is not silently discarded or replaced.
4. **Given** I add, update, or delete a task, **When** the operation succeeds, **Then** the change is saved automatically before the application reports success.

### User Story 4 - Receive Clear Feedback (Priority: P1)

As a user, I want a clear result message after each operation so I know whether it succeeded, failed, or was cancelled.

**Why this priority**: Clear feedback helps beginners use the application and identify problems without guessing.

**Independent Test**: Perform successful, invalid, and cancelled operations and verify that each produces an understandable result message.

**Acceptance Scenarios**:

1. **Given** I complete a valid operation, **When** it finishes, **Then** I see a clear success message.
2. **Given** I enter an invalid choice or task value, **When** the application rejects it, **Then** I see a clear error message and existing task details remain unchanged.
3. **Given** I cancel an operation, **When** it ends, **Then** I see a clear cancellation message and the task list remains unchanged.

### Edge Cases

- A title containing only spaces is rejected as empty.
- A user selects an ID that does not exist; the application reports an error and does not change any task.
- A user enters an unsupported priority, status, or menu choice; the application reports an error and preserves task data.
- The task list is empty, or a tag filter has no matches; the application explains that there are no tasks to show.
- Multiple tasks share a priority; sorting preserves their relative order.
- A task has no tags, or tags contain extra surrounding whitespace or differ only by letter case.
- The task data file is missing, malformed, unreadable, or cannot be saved; the application reports the problem and does not silently replace saved data with an empty list.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST provide a clear, numbered terminal menu for the supported task operations.
- **FR-002**: Users MUST be able to add tasks with a non-empty title and zero or more tags.
- **FR-003**: The application MUST assign each task a unique ID that remains stable when that task is updated.
- **FR-004**: Users MUST be able to view all tasks and their IDs, titles, priorities, tags, and statuses.
- **FR-005**: Users MUST be able to update a task's title, priority, tags, and status by selecting its ID.
- **FR-006**: The application MUST reject titles that are empty or contain only whitespace, both when adding and updating a task.
- **FR-007**: Users MUST be able to assign each task one of three priorities: High, Medium, or Low. New tasks MUST default to Medium priority.
- **FR-008**: Users MUST be able to set a task's status to Pending, In Progress, or Completed. New tasks MUST default to Pending, and users MUST be able to change a task between any of these statuses.
- **FR-009**: Users MUST be able to delete a task by its ID. The application MUST request confirmation before deletion and MUST leave the task unchanged if deletion is cancelled.
- **FR-010**: Users MUST be able to filter tasks by one exact tag at a time; tag matching MUST ignore letter case.
- **FR-011**: Users MUST be able to sort tasks in High, Medium, Low priority order. Tasks with equal priority MUST retain their existing relative order.
- **FR-012**: The application MUST store task data in a JSON file named `tasks.json` beside the application and MUST automatically save each successful add, update, or delete before reporting success, so the change is available after restart.
- **FR-013**: If the task data file does not exist, the application MUST start with an empty task list. If the file exists but cannot be read, the application MUST report an error and MUST NOT silently treat the file as an empty list or overwrite it.
- **FR-014**: After each operation, the application MUST show a clear success, error, or cancellation message. Failed or cancelled operations MUST NOT silently alter task data.
- **FR-015**: Invalid task IDs, menu choices, priorities, and statuses MUST be reported clearly without changing the selected task.

### Key Entities *(include if feature involves data)*

- **Task**: A user-managed item with a unique ID, non-empty title, one priority, one status, and zero or more tags.
- **Priority**: One of High, Medium, or Low, used to organize tasks.
- **Status**: One of Pending, In Progress, or Completed, representing a task's current progress.
- **Tag**: A label associated with a task and used to find matching tasks.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A manual acceptance run can complete task creation, viewing, updating, and confirmed deletion, with the displayed task list matching the expected result after each step.
- **SC-002**: In all priority-sort acceptance cases, tasks appear in High-to-Low order and equal-priority tasks retain their relative order.
- **SC-003**: In all restart acceptance cases, 100% of saved task IDs, titles, priorities, statuses, and tags are available after reopening the application.
- **SC-004**: 100% of tested invalid or cancelled operations produce a clear result message and leave existing task data unchanged.
- **SC-005**: Every supported operation is reachable from the visible menu, and its result is communicated in plain language.

## Assumptions

- The first version is for one person using one local task list; accounts, collaboration, and network access are out of scope.
- New tasks use Medium priority and Pending status unless the user changes them.
- Duplicate task titles are allowed because each task is identified by its unique ID.
- Tags are trimmed of surrounding whitespace and duplicate tags that differ only by letter case are treated as the same tag on a task.
- When sorting, tasks of equal priority keep the order they had before sorting.
- The word “Smart” refers to finding and prioritizing tasks through tags and priority sorting; automated recommendations are not part of this version.
- The task data is stored locally in the requested JSON file; a missing file means there are no saved tasks, while an unreadable or malformed existing file is reported rather than silently replaced.
- The application is intended to be simple and beginner-friendly; graphical interfaces, due dates, reminders, and task sharing are out of scope.
