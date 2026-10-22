from datetime import datetime, timedelta, timezone

import pytest

from app import core


def future(days=1):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def test_task_lifecycle_and_user_isolation():
    task = core.create_task("alice", "Java exam", future(), 90, priority=5)
    assert task["status"] == "pending"
    assert core.list_tasks("bob") == []
    changed = core.update_task("alice", task["id"], estimated_minutes=120)
    assert changed["estimated_minutes"] == 120
    completed = core.complete_task("alice", task["id"])
    assert completed["completed"] is True
    with pytest.raises(ValueError, match="not found"):
        core.complete_task("bob", task["id"])


def test_plan_persists_prioritized_sessions_and_replans():
    now = datetime.now(timezone.utc)
    core.create_task("student", "Later", (now + timedelta(days=3)).isoformat(), 90, priority=3)
    urgent = core.create_task("student", "Sooner", (now + timedelta(days=1)).isoformat(), 70, priority=5)
    plan = core.create_study_plan("student", now.isoformat(), 120)
    assert plan["sessions"][0]["task_id"] == urgent["id"]
    assert sum(session["minutes"] for session in plan["sessions"]) == 120
    persisted = core.get_study_plan("student", plan["plan_id"])
    assert len(persisted["sessions"]) == len(plan["sessions"])
    missed = plan["sessions"][0]
    replacement = core.replan_missed_session("student", missed["id"], (now + timedelta(hours=2)).isoformat(), 60)
    assert replacement["missed_session_id"] == missed["id"]
    assert replacement["plan_id"] != plan["plan_id"]


def test_context_and_activity_are_persistent():
    updated = core.update_student_context("alice", "Asia/Colombo", {"session_minutes": 40}, [{"course": "Java"}])
    assert updated["timezone"] == "Asia/Colombo"
    core.log_activity("alice", "update_student_context", {"timezone_name": "Asia/Colombo"}, "success", updated, 1)
    assert core.list_activity("alice")[0]["database_changes"] == 1


def test_invalid_naive_deadline_rejected():
    with pytest.raises(ValueError, match="timezone offset"):
        core.create_task("alice", "Bad", "2026-10-20T12:00:00", 10)
