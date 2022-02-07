"""
Definition of Celery task to enhance a speech
"""

from flask import Flask
from howler.deep import SentenceBuilder, Pso, Semantizer

from worker.speech import enhance
from worker.celery import make_celery

from howler.howler import Howler

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
        PUNCT = SentenceBuilder()
    if not PSO:
        PSO = Pso()
    if not CATEGORIZER:
        CATEGORIZER = Howler("fr",
                             categorisation_file=flask_app.config["CATEGORIES_JSON"],
                             stop_list_file=flask_app.config["KILL_LIST"])
        CATEGORIZER.config(compound_score_ratio=0.0, simple_word_min_score=0.0,
                           semantizer=Semantizer(), similarity_threshold=0.56)


@client.task
def enhance_speech(speech_json):
    """
    Enhances the speech with sentences, categories and types (problem/solution/other)
    :param speech_json: the json containing the speech
    :return: the json with a "sentences" block containing the enhanced sentences. Other elements are left as is
    """
    _lazy_load()
    parsed = enhance(
        speech_json, punct=PUNCT, pso=PSO, categorizer=CATEGORIZER)
    return parsed
