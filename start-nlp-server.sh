#!/bin/bash
# Starts flask server for content annotation
export FLASK_APP=src/main/flask/app.py
export FLASK_ENV=production
export FLASK_DEBUG=0
flask run --host=0.0.0.0 --port=5000
