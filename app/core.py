"""Deterministic task scheduling engine. All times are UTC ISO-8601."""
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = os.getenv('LUNA_DB_PATH', str(Path(__file__).resolve().parent.parent / 'luna.db'))

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        deadline TEXT NOT NULL,
        minutes INTEGER NOT NULL CHECK(minutes > 0),
        completed INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )''')
    con.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL REFERENCES tasks(id),
        starts_at TEXT NOT NULL,
        minutes INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'planned'
    )''')
    con.commit()
    return con

def utc(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Include timezone offset, e.g. +05:30')
    return parsed.astimezone(timezone.utc)

def create_task(title, deadline, minutes):
    if not title.strip() or not 1 <= minutes <= 1440:
        raise ValueError('Title required; minutes must be between 1 and 1440')
    due = utc(deadline)
    with connect() as con:
        cur = con.execute('INSERT INTO tasks(title,deadline,minutes,created_at) VALUES (?,?,?,?)',
                          (title.strip(), due.isoformat(), minutes, datetime.now(timezone.utc).isoformat()))
        return dict(con.execute('SELECT * FROM tasks WHERE id=?', (cur.lastrowid,)).fetchone())

def list_tasks():
    with connect() as con:
        return [dict(r) for r in con.execute('SELECT * FROM tasks ORDER BY completed,deadline,id')]

def complete_task(task_id):
    with connect() as con:
        cur = con.execute('UPDATE tasks SET completed=1 WHERE id=?', (task_id,))
        if not cur.rowcount:
            raise ValueError('Task not found')
        con.execute("UPDATE sessions SET status='cancelled' WHERE task_id=? AND status='planned'", (task_id,))
        return {'task_id': task_id, 'completed': True}

def build_plan(start_at, available_minutes):
    """Earliest deadline first, split into sessions up to 50 minutes each."""
    start = utc(start_at)
    if not 1 <= available_minutes <= 1440:
        raise ValueError('available_minutes must be between 1 and 1440')
    tasks = [t for t in list_tasks() if not t['completed']]
    remaining = available_minutes
    cursor = start
    sessions = []
    with connect() as con:
        con.execute("UPDATE sessions SET status='superseded' WHERE status='planned'")
        for task in tasks:
            needed = task['minutes']
            while needed > 0 and remaining > 0:
                chunk = min(50, needed, remaining)
                cur = con.execute('INSERT INTO sessions(task_id,starts_at,minutes) VALUES (?,?,?)',
                                  (task['id'], cursor.isoformat(), chunk))
                sessions.append({'id': cur.lastrowid, 'task_id': task['id'], 'title': task['title'],
                                 'starts_at': cursor.isoformat(), 'minutes': chunk,
                                 'deadline': task['deadline']})
                needed -= chunk
                remaining -= chunk
                cursor += timedelta(minutes=chunk)
            if remaining == 0:
                break
    return {'sessions': sessions, 'unallocated_minutes': remaining, 'tasks_remaining': len(tasks)}

def list_sessions():
    with connect() as con:
        return [dict(r) for r in con.execute('SELECT * FROM sessions WHERE status=\'planned\' ORDER BY starts_at')]
