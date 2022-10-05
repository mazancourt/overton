from collections import Counter

from flask import Flask, jsonify, request
from worker.celery import make_celery
from tasks import enhance_speech, enhance_hot, enhance_politics

app = Flask(__name__)
app.config.from_object("config")
app.config.update(CELERY_CONFIG={
    "broker_url": app.config['CELERY_BACKEND'],
    "result_backend": app.config['CELERY_BACKEND']
})
client = make_celery(app)

@app.route('/transcript', methods=['POST'])
def transcript():
    """
    Enqueues a speech for enhancement
    :return: the task-id
    """
    speech = request.get_json()
    task = enhance_speech.delay(speech)
    return jsonify({"id": task.id})\

@app.route('/hot', methods=['POST'])
def hot_parse():
    """
    Enqueues a speech for hot enhancement
    :return: the task-id
    """
    speech = request.get_json()
    task = enhance_hot.delay(speech)
    return jsonify({"id": task.id})

@app.route('/politics', methods=['POST'])
def politics_parse():
    """
    Enqueues a speech for NLP enhancements
    :return: the task-id
    """
    speech = request.get_json()
    task = enhance_politics.delay(speech)
    return jsonify({"id": task.id})


@app.route('/result/<task_id>')
def task_result(task_id):
    """
    Get the result of a task. Calling this endpoint will remove the result from the queue
    :param task_id: the Id of the task
    :return: the annotated speech
    """
    try:
        # there is no way to verify if the id is valid or not
        # https://github.com/celery/celery/issues/3596
        task = client.AsyncResult(task_id)
    except Exception as err:
        app.logger.error("Error fetching results from worker: %s", err)
        return 500
    if task.state == "SUCCESS":
        data = task.get()
        task.forget()
        return jsonify(data)
    else:
        return jsonify(task.info) if task else jsonify(None)


@app.route('/status/<task_id>')
def task_status(task_id):
    """
    Get the status of the task
    :param task_id: the Id of the task
    :return: a JSON like {"status": value}
    """
    task = None
    try:
        task = client.AsyncResult(task_id)
    except Exception as err:
        app.logger.error("Error getting task status from worker: task_id=%s - %s", task_id, err)
    return jsonify({"status":task.state if task else "FAIL"})


@app.route('/batch_status', methods=['POST'])
def batch_status():
    """
    Same as status, but for a list of IDs.
    INput message shall be { "ids": [id1, id2, ...] } where ids are task-ids
    The returned global status will be PENDING unless all tasks are SUCCESSful
    :return: json message with {"status": global status, "progress": progress-message, "details": counts by status }
    """
    speech = request.get_json()
    status_counts = Counter()
    task_id_list = speech["ids"]
    for task_id in task_id_list:
        try:
            task = client.AsyncResult(task_id)
            status = task.state
        except Exception as err:
            app.logger.error("Error getting task status from worker: task_id=%s - %s", task_id, err)
            status = "ERROR"
        status_counts[status] += 1
    if status_counts["SUCCESS"] == len(task_id_list):
        global_status = "SUCCESS"
    else:
        global_status = "PENDING"
    progress = "%.2f%% (%d out of %d)" % (100*status_counts["SUCCESS"]/len(task_id_list),
                                          status_counts["SUCCESS"], len(task_id_list))
    details = [{status: status_counts[status] for status in status_counts}]
    return jsonify({"status": global_status, "progress": progress, "details": details})
