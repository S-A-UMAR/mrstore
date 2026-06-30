"""
Celery configuration for Mr Store project.
Handles async tasks for order fulfillment, email notifications, retries.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mr_store_project.settings')

app = Celery('mr_store_project')

# Load config from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

@app.task(bind=True, max_retries=3)
def debug_task(self):
    print(f'Request: {self.request!r}')
