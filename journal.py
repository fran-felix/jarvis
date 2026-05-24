from __future__ import annotations

import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "dataset" / "journal.db"

TASK_CATEGORIES = ("test", "essay", "class", "other")
WEEK_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

CREATE_TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL DEFAULT 'other',
    due_date TEXT,
    course TEXT,
    completed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_CLASS_SCHEDULE_TABLE = """
CREATE TABLE IF NOT EXISTS class_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course TEXT NOT NULL,
    day_of_week TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    location TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

@dataclass
class Task:
    id: Optional[int]
    title: str
    description: Optional[str] = None
    category: str = "other"
    due_date: Optional[str] = None
    course: Optional[str] = None
    completed: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.category not in TASK_CATEGORIES:
            raise ValueError(f"Invalid category '{self.category}'. Valid categories: {TASK_CATEGORIES}")

@dataclass
class ClassSession:
    id: Optional[int]
    course: str
    day_of_week: str
    start_time: str
    end_time: str
    location: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class JournalDB:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._setup_schema()

    def _setup_schema(self) -> None:
        cursor = self.connection.cursor()
        cursor.executescript(CREATE_TASKS_TABLE)
        cursor.executescript(CREATE_CLASS_SCHEDULE_TABLE)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    @staticmethod
    def _normalize_day_of_week(day_of_week: str) -> str:
        normalized = day_of_week.strip().title()
        if normalized not in WEEK_DAYS:
            raise ValueError(f"day_of_week must be one of {WEEK_DAYS}, got '{day_of_week}'")
        return normalized

    @staticmethod
    def _parse_time_string(time_string: str) -> str:
        try:
            return datetime.strptime(time_string.strip(), "%H:%M").time().strftime("%H:%M")
        except ValueError as exc:
            raise ValueError(f"Time must be in HH:MM format, got '{time_string}'") from exc

    def _has_overlapping_session(self, day_of_week: str, start_time: str, end_time: str) -> bool:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT 1 FROM class_schedule
            WHERE day_of_week = ?
              AND NOT (end_time <= ? OR start_time >= ?)
            LIMIT 1
            """,
            (day_of_week, start_time, end_time),
        )
        return cursor.fetchone() is not None

    def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        category: str = "other",
        due_date: Optional[str] = None,
        course: Optional[str] = None,
        completed: bool = False,
    ) -> int:
        if category not in TASK_CATEGORIES:
            raise ValueError(f"Category must be one of {TASK_CATEGORIES}")

        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (title, description, category, due_date, course, completed)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, description, category, due_date, course, int(completed)),
        )
        self.connection.commit()
        row_id = cursor.lastrowid
        assert row_id is not None
        return row_id

    def get_task(self, task_id: int) -> Optional[Task]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        return self._row_to_task(row) if row else None

    def list_tasks(
        self,
        category: Optional[str] = None,
        completed: Optional[bool] = None,
        course: Optional[str] = None,
        due_before: Optional[str] = None,
        due_after: Optional[str] = None,
    ) -> List[Task]:
        query = "SELECT * FROM tasks"
        conditions: List[str] = []
        values: List[object] = []

        if category is not None:
            conditions.append("category = ?")
            values.append(category)
        if completed is not None:
            conditions.append("completed = ?")
            values.append(int(completed))
        if course is not None:
            conditions.append("course = ?")
            values.append(course)
        if due_before is not None:
            conditions.append("due_date <= ?")
            values.append(due_before)
        if due_after is not None:
            conditions.append("due_date >= ?")
            values.append(due_after)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY due_date IS NULL, due_date ASC, created_at ASC"
        cursor = self.connection.cursor()
        cursor.execute(query, tuple(values))
        return [self._row_to_task(row) for row in cursor.fetchall()]

    def update_task(self, task_id: int, **fields) -> bool:
        allowed_fields = {"title", "description", "category", "due_date", "course", "completed"}
        if not fields:
            return False

        updates = []
        values: List[object] = []
        for key, value in fields.items():
            if key not in allowed_fields:
                continue
            if key == "category" and value not in TASK_CATEGORIES:
                raise ValueError(f"Category must be one of {TASK_CATEGORIES}")
            updates.append(f"{key} = ?")
            values.append(int(value) if key == "completed" else value)

        if not updates:
            return False

        values.append(task_id)
        query = f"UPDATE tasks SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        cursor = self.connection.cursor()
        cursor.execute(query, tuple(values))
        self.connection.commit()
        return cursor.rowcount > 0

    def mark_task_completed(self, task_id: int, completed: bool = True) -> bool:
        return self.update_task(task_id, completed=completed)

    def delete_task(self, task_id: int) -> bool:
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.connection.commit()
        return cursor.rowcount > 0

    def erase_completed_tasks(self) -> int:
        """Delete tasks marked as completed.

        Returns number of rows deleted.
        """
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM tasks WHERE completed = 1")
        deleted = cursor.rowcount
        self.connection.commit()
        return deleted



    def add_class_session(
        self,
        course: str,
        day_of_week: str,
        start_time: str,
        end_time: str,
        location: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        normalized_day = self._normalize_day_of_week(day_of_week)
        normalized_start = self._parse_time_string(start_time)
        normalized_end = self._parse_time_string(end_time)

        if normalized_start >= normalized_end:
            raise ValueError("start_time must be earlier than end_time")

        if self._has_overlapping_session(normalized_day, normalized_start, normalized_end):
            raise ValueError(
                f"Class session overlaps an existing session on {normalized_day} "
                f"between {normalized_start} and {normalized_end}."
            )

        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO class_schedule (course, day_of_week, start_time, end_time, location, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (course, normalized_day, normalized_start, normalized_end, location, notes),
        )
        self.connection.commit()
        row_id = cursor.lastrowid
        assert row_id is not None
        return row_id

    def list_class_schedule(
        self,
        course: Optional[str] = None,
        day_of_week: Optional[str] = None,
    ) -> List[ClassSession]:
        query = "SELECT * FROM class_schedule"
        conditions: List[str] = []
        values: List[object] = []

        if course is not None:
            conditions.append("course = ?")
            values.append(course)
        if day_of_week is not None:
            conditions.append("day_of_week = ?")
            values.append(day_of_week)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += (
            " ORDER BY CASE day_of_week "
            "WHEN 'Monday' THEN 1 "
            "WHEN 'Tuesday' THEN 2 "
            "WHEN 'Wednesday' THEN 3 "
            "WHEN 'Thursday' THEN 4 "
            "WHEN 'Friday' THEN 5 "
            "WHEN 'Saturday' THEN 6 "
            "WHEN 'Sunday' THEN 7 "
            "ELSE 8 END, start_time ASC"
        )

        cursor = self.connection.cursor()
        cursor.execute(query, tuple(values))
        return [self._row_to_class_session(row) for row in cursor.fetchall()]

    def get_upcoming_tasks(self, days: int = 7) -> List[Task]:
        now = datetime.now()
        future = now.replace(hour=23, minute=59, second=59)
        limit = (future + timedelta(days=days)).isoformat(timespec="seconds")
        query = "SELECT * FROM tasks WHERE completed = 0 AND due_date IS NOT NULL AND due_date <= ? ORDER BY due_date ASC"
        cursor = self.connection.cursor()
        cursor.execute(query, (limit,))
        return [self._row_to_task(row) for row in cursor.fetchall()]



    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            category=row["category"],
            due_date=row["due_date"],
            course=row["course"],
            completed=bool(row["completed"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_class_session(row: sqlite3.Row) -> ClassSession:
        return ClassSession(
            id=row["id"],
            course=row["course"],
            day_of_week=row["day_of_week"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            location=row["location"],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    

    def reset_database(self) -> int:
        # Deletes all rows from TASKS and CLASS_SCHEDULE tabels
        # Essentially resets the database

        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM tasks")
        cursor.execute("DELETE FROM class_schedule")
        deleted = cursor.rowcount
        self.connection.commit()
        return deleted





def main() -> None:
    journal = JournalDB()

    print("Initializing student journal database at:", journal.db_path)

    journal.reset_database()

    print("Tasks:")
    for task in journal.list_tasks():
        print(asdict(task))

    print("Class schedule:")
    for session in journal.list_class_schedule():
        print(asdict(session))

    journal.mark_task_completed(1)
    journal.erase_completed_tasks()

    journal.close()


if __name__ == "__main__":
    main()
