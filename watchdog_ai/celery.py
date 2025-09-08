import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchdog_ai.production_settings') # ensures Celery uses the same database, cache, and other settings as your Django app

app = Celery('watchdog_ai') # creates a Celery instance named 'watchdog_ai'

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
# Registers any functions decorated with @app.task as Celery tasks
app.autodiscover_tasks()

# simple task that just prints the request
@app.task(bind=True)
def debug_task(self):
    # {self.request!r} formats the request object in a way that's easy to read, used for debugging
    print(f'Request: {self.request!r}') 