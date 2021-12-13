#!/bin/bash
# Starts services necessary to run flask application (but not the application itself)

echo "Starting Redis server"
docker run -d --rm --name redis -p 6379:6379 redis

echo "Starting Celery worker"
cd src/main/flask
# use --pool=solo ? (https://github.com/huggingface/transformers/issues/7516)
celery -A tasks.client worker --concurrency=1 --loglevel=INFO --pool=solo &
# use `cd src/main/python/worker; celery -A tasks.client control shutdown` to stop workers
# You may also
# `use celery -A tasks.client flower`
# to start flower monitoring
