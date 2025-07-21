web: OPENBLAS_NUM_THREADS=1 gunicorn watchdog_ai.wsgi --log-file -
worker: OPENBLAS_NUM_THREADS=1 celery -A watchdog_ai.celery worker --loglevel=info