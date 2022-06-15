# Overton NLP web service

This web-service handles the NLP analysis for Hedwige contents.

It is built on top of flask for the server and Celery for the task manager. The NLP itself
is handled by the `howler` component.

## Start/Stop

To start backend services:
```shell
$ ./start-services.sh
```
It starts a REDIS server through docker (see docker-compose.yml) and the Celery server

To start Flask Web Server:
```shell
$ ./start-nlp-server.sh
```

To stop the backend services:
```shell
$ ./stop-services.sh
```
To stop the Flask server, simply kill the associated process.

## Configuration
All configuration flags from `src/main/config.py` are overrideable through environment - simply create a `.env` file with corresponding names.

## Advanced settings
By default, the Celery server is starting in 'solo' mode, meaning that it doesn't fork nor parallelizes tasks. This is needed to run deep-learning modules.
