"""Persistent, user-isolated task and study-planning domain service."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

DB_PATH = os.getenv("LUNA_DB_PATH", str(Path(__file__).resolve().parent.parent / "luna.db"))
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SESSION_MINUTES = 50
BREAK_MINUTES = 10

SCHEMA = """
CREATE TABLE IF NOT EXISTS student_context (
    user_id TEXT PRIMARY KEY,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    preferences_json TEXT NOT NULL DEFAULT '{{}}',
    commitments_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    id {id_type},
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    course TEXT NOT NULL DEFAULT '',
    deadline TEXT NOT NULL,
    estimated_minutes INTEGER NOT NULL CHECK(estimated_minutes BETWEEN 1 AND 10080),
    priority INTEGER NOT NULL DEFAULT 3 CHECK(priority BETWEEN 1 AND 5),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','in_progress','completed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_user_deadline ON tasks(user_id,status,deadline);
CREATE TABLE IF NOT EXISTS study_plans (
    id {id_type},
    user_id TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    available_minutes INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','superseded','completed')),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS study_sessions (
    id {id_type},
    plan_id INTEGER NOT NULL REFERENCES study_plans(id),
    user_id TEXT NOT NULL,
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    starts_at TEXT NOT NULL,
    minutes INTEGER NOT NULL CHECK(minutes > 0),
    status TEXT NOT NULL DEFAULT 'planned' CHECK(status IN ('planned','completed','missed','cancelled','superseded')),
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_start ON study_sessions(user_id,status,starts_at);
CREATE TABLE IF NOT EXISTS activity_log (
    id {id_type},
    user_id TEXT NOT NULL,
    request_id TEXT,
    tool_name TEXT NOT NULL,
    arguments_json TEXT NOT NULL,
    status TEXT NOT NULL,
    result_json TEXT,
    database_changes INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
"""


class Connection:
    """Small DB-API adapter that keeps the domain SQL portable across SQLite and Postgres."""

    def __init__(self) -> None:
        self.is_postgres = bool(DATABASE_URL)
        if self.is_postgres:
            self.raw = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        else:
            self.raw = sqlite3.connect(DB_PATH, timeout=10)
            self.raw.row_factory = sqlite3.Row

    def execute(self, query: str, params: Any = ()) -> Any:
        if self.is_postgres:
            query = query.replace("?", "%s")
        return self.raw.execute(query, params)

    def commit(self) -> None:
        self.raw.commit()

    def __enter__(self) -> Connection:
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if exc_type is None:
            self.raw.commit()
        else:
            self.raw.rollback()
        self.raw.close()


def _insert_id(con: Connection, query: str, params: Any) -> int:
    if con.is_postgres:
        return int(con.execute(f"{query} RETURNING id", params).fetchone()["id"])
    return int(con.execute(query, params).lastrowid)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Use a valid ISO-8601 date and time") from exc
    if parsed.tzinfo is None:
        raise ValueError("Include a timezone offset, e.g. +05:30")
    return parsed.astimezone(timezone.utc)


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def connect() -> Connection:
    con = Connection()
    if con.is_postgres:
        for statement in SCHEMA.format(id_type="BIGSERIAL PRIMARY KEY").split(";"):
            if statement.strip():
                con.execute(statement)
    else:
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA journal_mode=WAL")
        con.raw.executescript(SCHEMA.format(id_type="INTEGER PRIMARY KEY AUTOINCREMENT"))
    con.commit()
    return con


def _task(row: Any) -> dict[str, Any]:
    result = dict(row)
    result["completed"] = result["status"] == "completed"
    result["minutes"] = result["estimated_minutes"]
    return result


def create_task(
    user_id: str,
    title: str,
    deadline: str,
    estimated_minutes: int,
    priority: int = 3,
    description: str = "",
    course: str = "",
) -> dict[str, Any]:
    title = title.strip()
    if not title:
        raise ValueError("Title is required")
    if not 1 <= estimated_minutes <= 10080:
        raise ValueError("estimated_minutes must be between 1 and 10080")
    if not 1 <= priority <= 5:
        raise ValueError("priority must be between 1 and 5")
    due = utc(deadline)
    stamp = now_utc().isoformat()
    with connect() as con:
        task_id = _insert_id(
            con,
            """INSERT INTO tasks(user_id,title,description,course,deadline,estimated_minutes,priority,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                user_id,
                title,
                description.strip(),
                course.strip(),
                due.isoformat(),
                estimated_minutes,
                priority,
                stamp,
                stamp,
            ),
        )
        return _task(con.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())


def list_tasks(user_id: str, status: str | None = None) -> list[dict[str, Any]]:
    params: list[Any] = [user_id]
    query = "SELECT * FROM tasks WHERE user_id=?"
    if status:
        if status not in {"pending", "in_progress", "completed"}:
            raise ValueError("Invalid task status")
        query += " AND status=?"
        params.append(status)
    query += " ORDER BY CASE status WHEN 'completed' THEN 1 ELSE 0 END, priority DESC, deadline, id"
    with connect() as con:
        return [_task(row) for row in con.execute(query, params)]


def update_task(user_id: str, task_id: int, **changes: Any) -> dict[str, Any]:
    allowed = {"title", "description", "course", "deadline", "estimated_minutes", "priority", "status"}
    supplied = {key: value for key, value in changes.items() if value is not None}
    unknown = supplied.keys() - allowed
    if unknown:
        raise ValueError(f"Unsupported fields: {', '.join(sorted(unknown))}")
    if not supplied:
        raise ValueError("Provide at least one field to update")
    if "title" in supplied:
        supplied["title"] = str(supplied["title"]).strip()
        if not supplied["title"]:
            raise ValueError("Title is required")
    if "deadline" in supplied:
        supplied["deadline"] = utc(str(supplied["deadline"])).isoformat()
    if "estimated_minutes" in supplied and not 1 <= int(supplied["estimated_minutes"]) <= 10080:
        raise ValueError("estimated_minutes must be between 1 and 10080")
    if "priority" in supplied and not 1 <= int(supplied["priority"]) <= 5:
        raise ValueError("priority must be between 1 and 5")
    if "status" in supplied and supplied["status"] not in {"pending", "in_progress", "completed"}:
        raise ValueError("Invalid task status")
    supplied["updated_at"] = now_utc().isoformat()
    if supplied.get("status") == "completed":
        supplied["completed_at"] = supplied["updated_at"]
    assignments = ",".join(f"{key}=?" for key in supplied)
    with connect() as con:
        cur = con.execute(
            f"UPDATE tasks SET {assignments} WHERE id=? AND user_id=?",
            [*supplied.values(), task_id, user_id],
        )
        if not cur.rowcount:
            raise ValueError("Task not found")
        if supplied.get("status") == "completed":
            con.execute(
                "UPDATE study_sessions SET status='cancelled' WHERE task_id=? AND user_id=? AND status='planned'",
                (task_id, user_id),
            )
        return _task(con.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())


def complete_task(user_id: str, task_id: int) -> dict[str, Any]:
    return update_task(user_id, task_id, status="completed")


def create_study_plan(user_id: str, start_at: str, available_minutes: int) -> dict[str, Any]:
    start = utc(start_at)
    if not 1 <= available_minutes <= 1440:
        raise ValueError("available_minutes must be between 1 and 1440")
    tasks = [task for task in list_tasks(user_id) if task["status"] != "completed"]
    remaining, cursor, sessions = available_minutes, start, []
    stamp = now_utc().isoformat()
    with connect() as con:
        con.execute("UPDATE study_plans SET status='superseded' WHERE user_id=? AND status='active'", (user_id,))
        con.execute("UPDATE study_sessions SET status='superseded' WHERE user_id=? AND status='planned'", (user_id,))
        plan_id = _insert_id(
            con,
            "INSERT INTO study_plans(user_id,starts_at,available_minutes,created_at) VALUES (?,?,?,?)",
            (user_id, start.isoformat(), available_minutes, stamp),
        )
        for task in tasks:
            needed = task["estimated_minutes"]
            while needed > 0 and remaining > 0 and cursor < utc(task["deadline"]):
                chunk = min(SESSION_MINUTES, needed, remaining)
                session_id = _insert_id(
                    con,
                    "INSERT INTO study_sessions(plan_id,user_id,task_id,starts_at,minutes) VALUES (?,?,?,?,?)",
                    (plan_id, user_id, task["id"], cursor.isoformat(), chunk),
                )
                sessions.append(
                    {
                        "id": session_id,
                        "plan_id": plan_id,
                        "task_id": task["id"],
                        "title": task["title"],
                        "starts_at": cursor.isoformat(),
                        "minutes": chunk,
                        "deadline": task["deadline"],
                        "status": "planned",
                    }
                )
                needed -= chunk
                remaining -= chunk
                cursor += timedelta(minutes=chunk + (BREAK_MINUTES if remaining and needed else 0))
            if remaining == 0:
                break
    return {
        "plan_id": plan_id,
        "sessions": sessions,
        "unallocated_minutes": remaining,
        "unscheduled_task_count": sum(1 for task in tasks if not any(s["task_id"] == task["id"] for s in sessions)),
    }


def get_study_plan(user_id: str, plan_id: int | None = None) -> dict[str, Any] | None:
    with connect() as con:
        if plan_id is None:
            plan = con.execute(
                "SELECT * FROM study_plans WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)
            ).fetchone()
        else:
            plan = con.execute("SELECT * FROM study_plans WHERE user_id=? AND id=?", (user_id, plan_id)).fetchone()
        if not plan:
            return None
        sessions = [
            dict(row)
            for row in con.execute(
                """SELECT s.*,t.title,t.deadline FROM study_sessions s JOIN tasks t ON t.id=s.task_id
               WHERE s.user_id=? AND s.plan_id=? ORDER BY s.starts_at""",
                (user_id, plan["id"]),
            )
        ]
        result = dict(plan)
        result["sessions"] = sessions
        return result


def list_sessions(user_id: str, active_only: bool = True) -> list[dict[str, Any]]:
    query = """SELECT s.*,t.title,t.deadline FROM study_sessions s JOIN tasks t ON t.id=s.task_id WHERE s.user_id=?"""
    params: list[Any] = [user_id]
    if active_only:
        query += " AND s.status='planned'"
    query += " ORDER BY s.starts_at,s.id"
    with connect() as con:
        return [dict(row) for row in con.execute(query, params)]


def complete_session(user_id: str, session_id: int) -> dict[str, Any]:
    stamp = now_utc().isoformat()
    with connect() as con:
        cur = con.execute(
            "UPDATE study_sessions SET status='completed',completed_at=? WHERE id=? AND user_id=? AND status='planned'",
            (stamp, session_id, user_id),
        )
        if not cur.rowcount:
            raise ValueError("Planned session not found")
        return dict(con.execute("SELECT * FROM study_sessions WHERE id=?", (session_id,)).fetchone())


def replan_missed_session(user_id: str, session_id: int, start_at: str, available_minutes: int) -> dict[str, Any]:
    with connect() as con:
        session = con.execute(
            "SELECT * FROM study_sessions WHERE id=? AND user_id=? AND status='planned'", (session_id, user_id)
        ).fetchone()
        if not session:
            raise ValueError("Planned session not found")
        con.execute("UPDATE study_sessions SET status='missed' WHERE id=?", (session_id,))
    plan = create_study_plan(user_id, start_at, available_minutes)
    plan["missed_session_id"] = session_id
    return plan


def get_student_context(user_id: str) -> dict[str, Any]:
    with connect() as con:
        row = con.execute("SELECT * FROM student_context WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return {"user_id": user_id, "timezone": "UTC", "preferences": {}, "commitments": [], "updated_at": None}
        return {
            "user_id": user_id,
            "timezone": row["timezone"],
            "preferences": json.loads(row["preferences_json"]),
            "commitments": json.loads(row["commitments_json"]),
            "updated_at": row["updated_at"],
        }


def update_student_context(
    user_id: str,
    timezone_name: str | None = None,
    preferences: dict[str, Any] | None = None,
    commitments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    current = get_student_context(user_id)
    timezone_name = timezone_name or current["timezone"]
    preferences = current["preferences"] if preferences is None else preferences
    commitments = current["commitments"] if commitments is None else commitments
    if len(_json(preferences)) > 20_000 or len(_json(commitments)) > 50_000:
        raise ValueError("Student context is too large")
    stamp = now_utc().isoformat()
    with connect() as con:
        con.execute(
            """INSERT INTO student_context(user_id,timezone,preferences_json,commitments_json,updated_at)
               VALUES (?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET timezone=excluded.timezone,
               preferences_json=excluded.preferences_json,commitments_json=excluded.commitments_json,updated_at=excluded.updated_at""",
            (user_id, timezone_name, _json(preferences), _json(commitments), stamp),
        )
    return get_student_context(user_id)


def log_activity(
    user_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    status: str,
    result: Any = None,
    database_changes: int = 0,
    request_id: str | None = None,
) -> dict[str, Any]:
    with connect() as con:
        activity_id = _insert_id(
            con,
            """INSERT INTO activity_log(user_id,request_id,tool_name,arguments_json,status,result_json,database_changes,created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                user_id,
                request_id,
                tool_name,
                _json(arguments),
                status,
                _json(result),
                database_changes,
                now_utc().isoformat(),
            ),
        )
        return dict(con.execute("SELECT * FROM activity_log WHERE id=?", (activity_id,)).fetchone())


def list_activity(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    with connect() as con:
        rows = con.execute(
            "SELECT * FROM activity_log WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, min(max(limit, 1), 200))
        )
        result = []
        for row in rows:
            item = dict(row)
            item["arguments"] = json.loads(item.pop("arguments_json"))
            raw_result = item.pop("result_json")
            item["result"] = json.loads(raw_result) if raw_result else None
            result.append(item)
        return result


def build_plan(start_at: str, available_minutes: int, user_id: str = "demo") -> dict[str, Any]:
    return create_study_plan(user_id, start_at, available_minutes)
