web: gunicorn main:app
worker: celery -A app.celery_worker.celery worker --loglevel=info
