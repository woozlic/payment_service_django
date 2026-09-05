import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("payment_service")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

from celery.schedules import crontab

app.conf.beat_schedule = {
    "process-pending-payouts": {
        "task": "payouts.tasks.process_pending_payouts",
        "schedule": 60.0,          # каждую минуту
    },
}