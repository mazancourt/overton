"""
Definition of Celery task to enhance a speech
"""

from flask import Flask

from worker.speech import enhance
from worker.celery import make_celery

from overton.category import Categorizer
from overton.nlp import Punct, Pso

flask_app = Flask(__name__)
flask_app.config.from_object("config")

client = make_celery(flask_app)

PUNCT = None
PSO = None
CATEGORIZER = None


# Lazy loading of resources, to avoid initializing them when importing the package,
# but still have resource loaded once.
def _lazy_load():
    global PUNCT, PSO, CATEGORIZER
    if not PUNCT:
        PUNCT = Punct()
    if not PSO:
        PSO = Pso()
    if not CATEGORIZER:
        CATEGORIZER = Categorizer(model_file=flask_app.config["WORD_EMBEDDINGS"],
                                  categories_file=flask_app.config["CATEGORIES_JSON"],
                                  kill_list_file=flask_app.config["KILL_LIST"])


@client.task
def enhance_speech(speech_json):
    """
    Enhances the speech with sentences, categories and types (problem/solution/other)
    :param speech_json: the json containing the speech
    :return: the json with a "sentences" block containing the enhanced sentences. Other elements are left as is
    """
    _lazy_load()
    parsed = enhance(
        speech_json, punct=PUNCT, pso=PSO, categorizer=CATEGORIZER, ts_server_url=flask_app.config["TS_SERVER_URL"])
    return parsed
