#!/bin/sh

until timeout 5s celery -A celery_app inspect ping; do
    >&2 echo "Celery workers not available"
done

echo 'Starting flower'
celery -A celery_app flower --address=0.0.0.0 --port=5555 --persistent=True
