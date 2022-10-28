FROM python:3.8-buster

# all-in-one dockerfile that encapsulates both Flask server and Celery worker
# It will be used from docker-compose with different commands (one for the flask server, one for the worker)

# Force Celery as root
ENV C_FORCE_ROOT true

ENV HOST 0.0.0.0
ENV PORT 5000

ARG root=src/main
COPY ${root}/flask/*.py /app/
COPY ${root}/flask/worker/*.py /app/worker/
COPY ${root}/resources/* /resources/
COPY requirements.txt /app/
WORKDIR /app

# install requirements
RUN pip install --trusted-host pypi.hedwige.fr --extra-index-url=http://datapolitics:hyHqykgzb8QF@pypi.hedwige.fr:8080/simple -r requirements.txt

# expose the app port
EXPOSE ${PORT}

# run the app server
env FLASK_APP "/app/app.py"
CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]