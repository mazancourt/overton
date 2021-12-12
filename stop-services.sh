#!/usr/bin/env bash
# Stops worker services (redis & + celery worker)
echo "Stopping Celery worker"
cd src/main/flask && celery -A tasks.client control shutdown
sleep 10
echo "Stopping Redis database"
docker stop $(docker ps -f name=redis -q)
echo "Services stopped"
