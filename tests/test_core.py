from datetime import datetime, timedelta, timezone
from app import core

def test_plan_prioritizes_deadline(tmp_path, monkeypatch):
    monkeypatch.setattr(core, 'DB_PATH', str(tmp_path/'test.db'))
    now = datetime.now(timezone.utc)
    core.create_task('Later', (now+timedelta(days=3)).isoformat(), 90)
    core.create_task('Sooner', (now+timedelta(days=1)).isoformat(), 70)
    plan = core.build_plan(now.isoformat(), 120)
    assert plan['sessions'][0]['title'] == 'Sooner'
    assert sum(s['minutes'] for s in plan['sessions']) == 120
    assert all(s['minutes'] <= 50 for s in plan['sessions'])
    core.complete_task(2)
    assert all(s['task_id'] != 2 for s in core.list_sessions())

def test_naive_deadline_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(core, 'DB_PATH', str(tmp_path/'test.db'))
    try:
        core.create_task('Bad', '2026-10-20T12:00:00', 10)
    except ValueError:
        pass
    else:
        assert False
