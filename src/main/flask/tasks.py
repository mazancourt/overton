"""
Definition of Celery task to enhance a speech
"""

from flask import Flask
from howler import SentenceBuilder, Semantizer, Howler, Namer, TextTiler
from howler.category import OrgRepository
from howler.deep import Pso

from worker.speech import enhance, hot_parse, politics_parse
from worker.celery import make_celery
from worker.utils import Tools

import nltk

nltk.download("punkt")  # to be moved into Howler ?

flask_app = Flask(__name__)
flask_app.config.from_object("config")
flask_app.config.update(CELERY_CONFIG={
    "broker_url": flask_app.config['CELERY_BACKEND'],
    "result_backend": flask_app.config['CELERY_BACKEND']
})

client = make_celery(flask_app)

PUNCT = None
PSO = None
CATEGORIZER = None
NAMER = None
TOOLS = None
# Lazy loading of resources, to avoid initializing them when importing the package,
# but still have resource loaded once.
def _lazy_load():
    global PUNCT, PSO, CATEGORIZER, NAMER, TOOLS
    if flask_app.config["ENABLE_DEEP_SENTENCE_BUILDER"] and not PUNCT:
        PUNCT = SentenceBuilder()
    if flask_app.config["ENABLE_DEEP_PSO"] and not PSO:
        PSO = Pso()
    if not CATEGORIZER:
        org_repo = None
        if flask_app.config["ORGS_LIST"]:
            org_repo = OrgRepository(flask_app.config["ORGS_LIST"], delimiter=";")
        CATEGORIZER = Howler("fr",
                             categorisation_file=flask_app.config["CATEGORIES_JSON"],
                             stop_list_file=flask_app.config["KILL_LIST"],
                             known_orgs_repo=org_repo)
        CATEGORIZER.config(compound_score_ratio=0.0, simple_word_min_score=0.0,
                           semantizer=Semantizer() if flask_app.config["ENABLE_DEEP_CATEGORIZER"] else None,
                           similarity_threshold=0.56)
    if not NAMER:
        NAMER = Namer()
    TOOLS = Tools(sentence_builder=PUNCT, pso=PSO, namer=NAMER, howler=CATEGORIZER, text_tiler=TextTiler("fr"))
    return TOOLS

@client.task
def enhance_hot(speech_json):
    """
    Hot version of
    :param speech_json:
    :return:
    """
    _lazy_load()
    parsed = hot_parse(speech_json, tools=TOOLS)
    return parsed

@client.task
def enhance_politics(speech_json):
    """
    Hot version of
    :param speech_json:
    :return:
    """
    _lazy_load()
    parsed = politics_parse(speech_json, tools=TOOLS)
    return parsed


@client.task
def enhance_speech(speech_json):
    """
    ** legacy version **
    Enhances the speech with sentences, categories and types (problem/solution/other)
    :param speech_json: the json containing the speech
    :return: the json with a "sentences" block containing the enhanced sentences. Other elements are left as is
    """
    _lazy_load()
    parsed = enhance(
        speech_json, punct=PUNCT, pso=PSO, categorizer=CATEGORIZER, namer=NAMER)
    return parsed
