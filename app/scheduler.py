from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from .models import db, Worker

OFFLINE_THRESHOLD_SECONDS = 30

scheduler = BackgroundScheduler()


def check_offline_workers(app):
    """Passe OFFLINE tout worker dont le dernier heartbeat date de trop longtemps."""
    with app.app_context():
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=OFFLINE_THRESHOLD_SECONDS)
        stale_workers = Worker.query.filter(
            Worker.status != 'OFFLINE',
            Worker.last_heartbeat < cutoff,
        ).all()

        for worker in stale_workers:
            print(f"[SCHEDULER] Worker {worker.hostname} n'a plus donne signe depuis "
                  f"plus de {OFFLINE_THRESHOLD_SECONDS}s -> OFFLINE")
            worker.status = 'OFFLINE'

        if stale_workers:
            db.session.commit()


def init_scheduler(app):
    scheduler.add_job(
        func=check_offline_workers,
        args=[app],
        trigger="interval",
        seconds=5,
        id="check_offline_workers",
        replace_existing=True,
    )
    scheduler.start()
