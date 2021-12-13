#!/bin/bash
# Starts flask server for TermSuite extractionon port 5001
export FLASK_APP=src/main/ts/ts_server.py
export FLASK_ENV=development
export FLASK_DEBUG=0
# to be changed for local host only
flask run --host=0.0.0.0 --port=5001
