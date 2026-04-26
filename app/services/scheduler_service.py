import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_app = None
_scheduler = None


def init_scheduler(app):
    global _app, _scheduler
    _app = app

    try:
        from apscheduler.schedulers.gevent import GeventScheduler
        _scheduler = GeventScheduler()
    except ImportError:
        from apscheduler.schedulers.background import BackgroundScheduler
        _scheduler = BackgroundScheduler()

    retention_days = int(os.getenv("LOG_RETENTION_DAYS", 30))

    _scheduler.add_job(
        _cleanup_old_logs,
        "interval",
        hours=24,
        id="cleanup_logs",
        replace_existing=True,
        kwargs={"retention_days": retention_days},
    )

    _scheduler.add_job(
        _weekly_summary,
        "cron",
        day_of_week="mon",
        hour=8,
        id="weekly_summary",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started (log retention: %d days, weekly summary: Mon 08:00)",
        retention_days,
    )


def get_scheduler():
    return _scheduler


def _cleanup_old_logs(retention_days: int = 30):
    if _app is None:
        return
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    try:
        with _app.app_context():
            from app.extensions import db
            from app.models.recognition_log import RecognitionLog
            from app.extensions import cache

            count = RecognitionLog.query.filter(
                RecognitionLog.timestamp < cutoff
            ).delete()
            if count:
                db.session.commit()
                cache.delete("api_stats")
                logger.info("Scheduler: removed %d recognition log entries older than %d days", count, retention_days)
    except Exception as exc:
        logger.error("Scheduler cleanup job failed: %s", exc)


def _weekly_summary():
    """Send a weekly email digest if MAIL_SERVER and MAIL_REPORT_TO are configured."""
    if _app is None:
        return

    mail_server = os.getenv("MAIL_SERVER", "")
    report_to = os.getenv("MAIL_REPORT_TO", "")
    if not mail_server or not report_to:
        return

    try:
        with _app.app_context():
            from datetime import date
            from app.extensions import db
            from app.models.recognition_log import RecognitionLog
            from app.models.face_encoding import FaceEncoding
            from flask_mail import Message
            from app.extensions import mail

            week_ago = datetime.utcnow() - timedelta(days=7)
            total = RecognitionLog.query.filter(RecognitionLog.timestamp >= week_ago).count()
            enrolled = db.session.query(db.func.count(db.distinct(FaceEncoding.name))).scalar()

            top = (
                db.session.query(RecognitionLog.face_name, db.func.count().label("cnt"))
                .filter(RecognitionLog.timestamp >= week_ago)
                .group_by(RecognitionLog.face_name)
                .order_by(db.func.count().desc())
                .limit(5)
                .all()
            )
            top_lines = "\n".join(f"  {r.face_name}: {r.cnt}" for r in top) or "  (none)"

            body = (
                f"FaceID Weekly Summary — {date.today()}\n"
                f"{'='*40}\n"
                f"Recognitions this week : {total}\n"
                f"Enrolled faces         : {enrolled}\n\n"
                f"Top recognised people:\n{top_lines}\n"
            )
            msg = Message(
                subject=f"FaceID Weekly Report — {date.today()}",
                recipients=[report_to],
                body=body,
            )
            mail.send(msg)
            logger.info("Weekly summary sent to %s", report_to)
    except Exception as exc:
        logger.error("Weekly summary job failed: %s", exc)
