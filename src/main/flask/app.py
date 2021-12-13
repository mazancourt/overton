from flask import Flask, jsonify, request
from worker.celery import make_celery

app = Flask(__name__)
app.config.from_object("config")

client = make_celery(app)

@app.route('/transcript', methods=['POST'])
def transcript():
    video = request.get_json()
    task = client.send_task("parse", args=[video])
    return jsonify({"id": task.id})


@app.route('/result/<task_id>')
def task_result(task_id):
    try:
        # there is no way to verify if the id is valid or not
        # https://github.com/celery/celery/issues/3596
        task = client.AsyncResult(task_id)
    except Exception as err:
        app.logger.error("Error fetching results from worker: %s", err)
        return 500
    if task.state == "SUCCESS":
        data = task.get()
        # task.forget()
        return jsonify(data)
    else:
        return jsonify(task.info)


@app.route('/status/<task_id>')
def task_status(task_id):
    task = None
    try:
        task = client.AsyncResult(task_id)
    except Exception as err:
        app.logger.error("Error getting task status from worker: task_id=%s - %s", task_id, err)
    return jsonify({"status":task.state if task else "FAIL"})
