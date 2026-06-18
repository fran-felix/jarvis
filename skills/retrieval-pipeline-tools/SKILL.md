---
name: retrieval-pipeline-tools
description: Comprehensive guide to the Jarvis retrieval pipeline tools for task management, scheduling, and worksheet generation. Covers tool schemas, best practices, integration patterns, and optimization strategies for academic and administrative workflows.
---

# Retrieval Pipeline Tools Skill

## Overview

The Jarvis retrieval pipeline provides six specialized tools for managing academic tasks, class schedules, and generating educational content. These tools interact with a persistent journal database and document retrieval system to support student workflows.

**Core Capabilities:**
- Task management (create, list, update completion status)
- Class schedule management (add sessions, view schedules)
- Intelligent worksheet generation with skill-based guidelines
- Document retrieval and context-aware responses

## Tool Schemas

### 1. `add_task`

**Purpose**: Create a new task in the journal database

**Parameters:**
```
title (required, str)
  - The task name/title
  - Examples: "Study for exam", "Complete essay", "Lab report"

description (optional, str)
  - Detailed task description
  - Examples: "Review chapters 3-5", "Answer all questions"

category (optional, str, default: 'other')
  - Valid values: 'test', 'essay', 'class', 'other'
  - Use 'test' for exams/quizzes
  - Use 'essay' for writing assignments
  - Use 'class' for in-class activities
  - Use 'other' for miscellaneous tasks

due_date (optional, str)
  - Format: DD/MM/YYYY (strict format requirement)
  - Examples: "31/05/2026", "15/06/2026"
  - Always ensure correct formatting

course (optional, str)
  - Course or subject name
  - Examples: "Biology", "Advanced Math", "History"

completed (optional, bool, default: False)
  - Whether the task is initially marked complete
  - Usually False for new tasks, True for archival
```

**Return Value:**
- `task_id` (int) - The unique identifier for the created task
- Success indicator

**Example Calls:**
```json
{"tool_name": "add_task", "parameters": {"title": "Study for midterm", "category": "test", "due_date": "20/06/2026", "course": "Biology"}}
{"tool_name": "add_task", "parameters": {"title": "Write essay on climate change", "category": "essay", "description": "3000 words minimum", "due_date": "25/06/2026", "course": "Environmental Science"}}
{"tool_name": "add_task", "parameters": {"title": "Lab cleanup", "category": "class"}}
```

**Best Practices:**
- Always provide meaningful titles
- Use appropriate categories for filtering/organization
- Include due dates when known
- Add descriptions for complex tasks
- Set course when relevant for context

### 2. `list_tasks`

**Purpose**: Retrieve tasks from the database with optional filtering

**Parameters:**
```
category (optional, str)
  - Filter by: 'test', 'essay', 'class', 'other'
  - Omit to retrieve all categories

completed (optional, bool)
  - Filter by completion status
  - true: show only completed tasks
  - false: show only incomplete tasks
  - Omit to retrieve all statuses

course (optional, str)
  - Filter by course/subject name
  - Exact string matching
  - Examples: "Biology", "Advanced Math"

due_before (optional, str)
  - Filter tasks due before this date
  - Format: DD/MM/YYYY
  - Inclusive boundary

due_after (optional, str)
  - Filter tasks due after this date
  - Format: DD/MM/YYYY
  - Inclusive boundary
```

**Return Value:**
```
tasks (array of objects)
  Each task contains:
  - id: unique identifier
  - title: task name
  - description: optional details
  - category: 'test', 'essay', 'class', or 'other'
  - due_date: DD/MM/YYYY format
  - course: subject/course name
  - completed: boolean status
```

**Example Calls:**
```json
{"tool_name": "list_tasks", "parameters": {"completed": false}}
{"tool_name": "list_tasks", "parameters": {"category": "test", "completed": false}}
{"tool_name": "list_tasks", "parameters": {"course": "Biology"}}
{"tool_name": "list_tasks", "parameters": {"due_after": "01/06/2026", "due_before": "30/06/2026"}}
```

**Best Practices:**
- Use multiple filters to narrow results efficiently
- Query incomplete tasks regularly (status check)
- Filter by course to see workload per subject
- Use date ranges to identify upcoming deadlines
- Combine category and course filters for precise queries

### 3. `mark_task_completed`

**Purpose**: Update a task's completion status

**Parameters:**
```
task_id (required, int)
  - The unique identifier of the task
  - Retrieve from list_tasks results
  - Examples: 1, 5, 42

completed (optional, bool, default: True)
  - true: mark as completed
  - false: mark as incomplete (reopen task)
  - Default action is to mark completed
```

**Return Value:**
- Success indicator (boolean)
- Status message

**Example Calls:**
```json
{"tool_name": "mark_task_completed", "parameters": {"task_id": 5}}
{"tool_name": "mark_task_completed", "parameters": {"task_id": 12, "completed": true}}
{"tool_name": "mark_task_completed", "parameters": {"task_id": 3, "completed": false}}
```

**Best Practices:**
- Always retrieve task IDs using list_tasks first
- Mark tasks completed immediately upon finishing
- Use `completed: false` to reopen tasks if needed
- Chain with list_tasks to confirm status changes

### 4. `add_class_session`

**Purpose**: Add a class meeting to the weekly schedule

**Parameters:**
```
course (required, str)
  - Course or class name
  - Examples: "Biology Lab", "Advanced Math", "History 101"

day_of_week (required, str)
  - Day name (case-insensitive)
  - Valid values: 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
  - Examples: "Monday", "wednesday", "FRIDAY"

start_time (required, str)
  - Start time in 24-hour format
  - Format: HH:MM
  - Examples: "09:00", "14:30", "08:15"

end_time (required, str)
  - End time in 24-hour format
  - Format: HH:MM
  - Must be after start_time
  - Examples: "10:30", "16:00"

location (optional, str)
  - Classroom or location name
  - Examples: "Room 301", "Lab B", "Building A"

notes (optional, str)
  - Additional session notes
  - Examples: "Bring calculator", "Lab materials provided"
```

**Constraints:**
- Classes cannot overlap on the same day
- System will reject overlapping time slots
- Times must be in valid 24-hour format
- Day of week must be in english, translate otherwise

**Return Value:**
- `session_id` (int) - Unique identifier for the class session
- Success indicator

**Example Calls:**
```json
{"tool_name": "add_class_session", "parameters": {"course": "Biology", "day_of_week": "Monday", "start_time": "09:00", "end_time": "10:30", "location": "Room 301"}}
{"tool_name": "add_class_session", "parameters": {"course": "Advanced Math", "day_of_week": "Wednesday", "start_time": "14:00", "end_time": "15:30", "location": "Lab B", "notes": "Bring calculator"}}
```

**Best Practices:**
- Add all recurring classes at session setup
- Maintain consistent time formatting (HH:MM)
- Include location for easy reference
- Add notes for special requirements
- Verify no overlaps before adding sessions

### 5. `list_class_schedule`

**Purpose**: Retrieve the weekly class schedule with optional filtering

**Parameters:**
```
course (optional, str)
  - Filter by course name
  - Exact string matching
  - Omit to retrieve all courses

day_of_week (optional, str)
  - Filter by day
  - Valid values: 'Monday', 'Tuesday', etc.
  - Omit to retrieve all days
```

**Return Value:**
```
sessions (array of objects)
  Each session contains:
  - id: unique identifier
  - course: course name
  - day_of_week: day of week
  - start_time: HH:MM format
  - end_time: HH:MM format
  - location: classroom/location
  - notes: optional notes
```

**Example Calls:**
```json
{"tool_name": "list_class_schedule", "parameters": {}}
{"tool_name": "list_class_schedule", "parameters": {"day_of_week": "Monday"}}
{"tool_name": "list_class_schedule", "parameters": {"course": "Biology"}}
```

**Best Practices:**
- Retrieve full schedule at session start
- Filter by day to see daily workload
- Filter by course to track time per subject
- Use to identify free time slots
- Sync with task deadlines for planning

### 6. `generate_worksheet`

**Purpose**: Create an educational worksheet with AI-generated questions, answer keys, and citations

**Parameters:**
```
topic (required, str)
  - The worksheet subject
  - Retrieved from document store via RAG system
  - Examples: "Photosynthesis", "World War II", "Newton's Laws"

difficulty (optional, str, default: 'medium')
  - Valid values: 'easy', 'medium', 'hard'
  - easy: Definition/recall, True/False, comprehension
  - medium: Recall/comprehension, application, short answer
  - hard: Analysis, synthesis, critical thinking, evaluation

number_of_questions (optional, int, default: 10)
  - Recommended range: 5-15 questions
  - Higher = more comprehensive
  - Lower = more focused worksheet

include_answer_key (optional, bool, default: True)
  - true: generate answers with key points
  - false: questions only

include_citations (optional, bool, default: True)
  - true: include source document references
  - false: omit citations
```

**Difficulty Breakdown:**

**Easy Level:**
- 40% Definition/Recall (What, Who, When, Where)
- 40% True/False statements
- 20% Simple comprehension
- Requires direct retrieval from documents

**Medium Level:**
- 30% Recall/Comprehension questions
- 40% Application and Comparison questions
- 30% Short answer requiring analysis
- Requires interpretation and synthesis

**Hard Level:**
- 20% Analysis questions (Why, How does this relate)
- 40% Synthesis questions (combining concepts)
- 20% Critical thinking (What if, evaluate validity)
- 20% Evaluation questions
- Requires higher-order thinking

**Return Value:**
```
worksheet (str)
  - Formatted markdown with:
    - Questions section (formatted Q#)
    - Answer key (if requested)
    - Source citations (if requested)
    - Clear headers and structure

message: Confirmation of successful generation
```

**Example Calls:**
```json
{"tool_name": "generate_worksheet", "parameters": {"topic": "Photosynthesis", "difficulty": "medium", "number_of_questions": 10}}
{"tool_name": "generate_worksheet", "parameters": {"topic": "World War II", "difficulty": "hard", "number_of_questions": 15, "include_answer_key": true, "include_citations": true}}
{"tool_name": "generate_worksheet", "parameters": {"topic": "Newton's Laws", "difficulty": "easy", "number_of_questions": 8}}
```

**Best Practices:**
- Choose difficulty matching student level
- Start with medium difficulty if unsure
- Request 10-12 questions for balanced worksheet
- Always include answer key for self-study
- Include citations for reference and credibility
- Topic should match document store content

**Skill Integration:**
- Automatically loads `/skills/generate-worksheet/SKILL.md` instructions
- Applies skill guidelines to question quality and formatting
- Uses skill recommendations for answer key structure

## Tool Usage Patterns

### Pattern 1: Task Workflow (Planning & Tracking)

**Scenario**: Student receives multiple assignments and needs to organize them

```
1. add_task(title: "Essay on climate", category: "essay", due_date: "25/06/2026", course: "Environmental Science")
2. add_task(title: "Study for midterm", category: "test", due_date: "20/06/2026", course: "Biology")
3. list_tasks(completed: false) → view all pending work
4. mark_task_completed(task_id: 1) → mark essay done
```

**Key Principles:**
- Add tasks immediately upon assignment
- Use list_tasks to maintain overview
- Update completion status regularly
- Filter by course to track subject-specific load

### Pattern 2: Schedule & Deadline Integration

**Scenario**: Student wants to coordinate class times with assignment due dates

```
1. list_class_schedule() → see all classes
2. list_tasks(category: "test") → see upcoming exams
3. add_class_session(course: "Review Session", day_of_week: "Friday", start_time: "16:00", end_time: "17:00")
4. Identify conflicts or free study slots
```

**Key Principles:**
- Review schedule and tasks together
- Identify busy days for advance planning
- Add review/study sessions manually if needed
- Plan around class schedules

### Pattern 3: Content Generation Workflow

**Scenario**: Student needs study materials for upcoming exam

```
1. list_tasks(category: "test", completed: false) → find exams
2. generate_worksheet(topic: "Photosynthesis", difficulty: "hard", number_of_questions: 12)
3. Use generated worksheet for self-assessment
4. Compare answers with provided answer key
5. Revisit sources via citations if needed
```

**Key Principles:**
- Generate worksheets aligned with exam difficulty
- Use answer keys for self-assessment
- Reference citations for deeper understanding
- Generate multiple worksheets for different topics

### Pattern 4: Multi-Task Processing

**Scenario**: Processing multiple student requests efficiently

```
Batch 1 (Parallel):
- add_task(assignments...)
- list_class_schedule()
- list_tasks(filters...)

Batch 2 (Sequential after Batch 1):
- mark_task_completed(IDs...)
- generate_worksheet(topic...)
```

**Key Principles:**
- Batch read operations (list_tasks, list_class_schedule)
- Batch write operations (add_task calls)
- Sequential operations only when dependent
- Minimize database queries through filtering

## Common Workflows

### Weekly Planning

```
Monday Morning Workflow:
1. list_tasks(completed: false) → See all pending tasks
2. list_class_schedule() → See weekly schedule
3. Generate worksheets for upcoming exams
4. Identify high-stress days
5. Add tasks as needed for the week
```

### Daily Status Check

```
Daily Workflow:
1. list_class_schedule(day_of_week: "Monday") → Today's classes
2. list_tasks(completed: false) → Pending work
3. mark_task_completed(finished_task_ids) → Update status
```

### Course Planning

```
Course-Specific Workflow:
1. list_tasks(course: "Biology") → All Biology work
2. list_class_schedule(course: "Biology") → Biology classes
3. generate_worksheet(topic: "Mitochondria", difficulty: "medium")
4. Assess workload and prepare study materials
```

## Best Practices & Optimization

### Data Integrity

**Task Management:**
- Always use exact DD/MM/YYYY date format
- Validate task IDs before marking complete
- Keep descriptions concise but informative
- Use categories consistently

**Schedule Management:**
- Use 24-hour time format (HH:MM)
- Ensure no time overlaps
- Keep location information updated
- Note special requirements in notes field

**Worksheet Generation:**
- Match difficulty to student level
- Keep question count reasonable (5-15)
- Verify topic exists in document store
- Always include citations for reliability

### Efficiency Tips

**Reduce API Calls:**
- Combine filters in list_tasks (category + course + date range)
- Retrieve full schedule once, parse locally
- Batch multiple add_task calls when possible
- Use completion status to filter active tasks

**Optimize Results:**
- Filter by completion status for actionable items
- Use date ranges to focus on upcoming deadlines
- Generate worksheets by topic relevance
- Review high-priority tasks first

### Error Handling

**Common Issues:**

1. **Invalid Date Format**
   - Problem: Using "2026-06-25" instead of "25/06/2026"
   - Solution: Always use DD/MM/YYYY format

2. **Schedule Overlap**
   - Problem: Overlapping class times
   - Solution: Check list_class_schedule before adding new sessions

3. **Nonexistent Task ID**
   - Problem: Attempting to mark task with wrong ID
   - Solution: Retrieve task list first, verify ID exists

4. **Topic Not Found**
   - Problem: Worksheet topic has no documents
   - Solution: Check document store, use related topic names

## Integration Architecture

### Document Retrieval Context

When a worksheet is generated:
1. System searches document store for topic
2. Retrieves up to 5 relevant documents (threshold: 0.4 similarity)
3. Passes documents to LLM with skill guidelines
4. LLM generates questions based on documents
5. Citations reference original documents

### Tool Call Format

All tool calls follow this JSON structure:
```json
{
  "tool_name": "function_name",
  "parameters": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

Multiple tool calls in sequence:
```json
{"tool_name": "list_tasks", "parameters": {"completed": false}}
{"tool_name": "generate_worksheet", "parameters": {"topic": "Photosynthesis", "difficulty": "medium"}}
```

### Database Persistence

- All tasks and class sessions persist across sessions
- Database location: configurable (default: `journal.db`)
- Journal DB handles concurrent access safely
- Auto-saves after each modification

## Decision Matrix

### When to Use Each Tool

| Need | Tool | When |
|------|------|------|
| Create assignment | `add_task` | Assignment given, need to track |
| View pending work | `list_tasks` | Need overview, status check |
| Mark work complete | `mark_task_completed` | Task finished, need to update status |
| Add class meeting | `add_class_session` | Course registration, new schedule |
| View class schedule | `list_class_schedule` | Planning study time, checking conflicts |
| Create study materials | `generate_worksheet` | Exam prep, review needed, topic known |

### Filter Selection Guide

**For `list_tasks`:**
- Need incomplete work? → Use `completed: false`
- Exam coming up? → Use `category: "test"`
- Overwhelmed? → Filter `course` to focus
- Deadline approaching? → Use `due_before` and `due_after`

**For `list_class_schedule`:**
- Monday schedule? → Use `day_of_week: "Monday"`
- Biology classes? → Use `course: "Biology"`
- Full week? → No filters

## Performance Benchmarks

**Operation Costs (relative):**
- `add_task`: Single write, minimal cost
- `mark_task_completed`: Minimal cost
- `list_tasks` (no filters): Medium cost
- `list_tasks` (with filters): Lower cost (fewer results)
- `list_class_schedule`: Low cost (small dataset)
- `generate_worksheet`: High cost (LLM + document retrieval)

**Optimization Strategy:**
- Filter aggressively to reduce result sets
- Batch multiple add operations
- Generate worksheets infrequently (high cost)
- Cache schedule data (rarely changes)

## Quick Reference

```
TASK MANAGEMENT:
├─ Create: add_task(title, category?, due_date?, course?)
├─ List: list_tasks(completed?, category?, course?, date_range?)
└─ Update: mark_task_completed(task_id, completed?)

SCHEDULING:
├─ Add: add_class_session(course, day, start_time, end_time, location?, notes?)
└─ List: list_class_schedule(course?, day?)

CONTENT:
└─ Generate: generate_worksheet(topic, difficulty?, count?, answers?, citations?)
```
