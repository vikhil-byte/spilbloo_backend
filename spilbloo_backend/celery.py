import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spilbloo_backend.settings')

app = Celery('spilbloo_backend')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# Celery Beat Configuration (Replica of timer.php)
from celery.schedules import crontab

app.conf.beat_schedule = {
    'send_booking_notification_every_15_mins': {
        'task': 'core.tasks.send_booking_notification',
        'schedule': crontab(minute='*/15'),
    },
    'inactive_booking_call_every_15_mins': {
        'task': 'core.tasks.inactive_booking_call',
        'schedule': crontab(minute='*/15'),
    },
    'auto_cancel_booking_every_15_mins': {
        'task': 'core.tasks.auto_cancel_booking',
        'schedule': crontab(minute='*/15'),
    },
    'calculate_earning_daily': {
        'task': 'core.tasks.calculate_earning',
        'schedule': crontab(hour=0, minute=0), # Daily at midnight
    },
    'auto_complete_booking_hourly': {
        'task': 'core.tasks.auto_complete_booking',
        'schedule': crontab(minute=0), # Every hour
    },
    'booking_reminder_every_15_mins': {
        'task': 'core.tasks.booking_reminder',
        'schedule': crontab(minute='*/15'),
    },
    'cancel_pending_booking_every_15_mins': {
        'task': 'core.tasks.cancel_pending_booking',
        'schedule': crontab(minute='*/15'),
    },
    'cancel_plans_daily': {
        'task': 'core.tasks.cancel_plans',
        'schedule': crontab(hour=1, minute=0),
    },
    'cancel_trial_plans_daily': {
        'task': 'core.tasks.cancel_trial_plans',
        'schedule': crontab(hour=1, minute=10),
    },
    'cancel_halted_plans_daily': {
        'task': 'core.tasks.cancel_halted_plans',
        'schedule': crontab(hour=1, minute=20),
    },
    'subscription_reminder_daily': {
        'task': 'core.tasks.subscription_reminder',
        'schedule': crontab(hour=9, minute=0), # 9 AM daily
    },
    'admin_notifications_daily': {
        'task': 'core.tasks.admin_notifications',
        'schedule': crontab(hour=10, minute=0),
    },
    'cancel_free_plans_daily': {
        'task': 'core.tasks.cancel_free_plans',
        'schedule': crontab(hour=2, minute=0),
    },
    'expire_one_time_plans_daily': {
        'task': 'core.tasks.expire_one_time_plans',
        'schedule': crontab(hour=2, minute=30),
    },
    'active_upcoming_plans_hourly': {
        'task': 'core.tasks.active_upcoming_plans',
        'schedule': crontab(minute=0),
    },
    'add_company_invoice_daily': {
        'task': 'core.tasks.add_company_invoice',
        'schedule': crontab(hour=3, minute=0),
    },
    'generate_limited_coupon_invoice_daily': {
        'task': 'core.tasks.generate_limited_coupon_invoice',
        'schedule': crontab(hour=3, minute=30),
    },
    'generate_un_limited_coupon_invoice_daily': {
        'task': 'core.tasks.generate_un_limited_coupon_invoice',
        'schedule': crontab(hour=4, minute=0),
    },
    'inactive_company_coupon_daily': {
        'task': 'core.tasks.inactive_company_coupon',
        'schedule': crontab(hour=4, minute=30),
    },
    'notify_subscribed_user_daily': {
        'task': 'core.tasks.notify_subscribed_user',
        'schedule': crontab(hour=12, minute=0),
    },
}
