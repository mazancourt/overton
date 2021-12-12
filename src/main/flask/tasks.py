import logging

from flask import Flask

from worker.speech import parse_video
from worker.celery import make_celery

from overton.category import Categorizer
from overton.nlp import Punct, Pso

flask_app = Flask(__name__)
flask_app.config.from_object("config")

client = make_celery(flask_app)

punct = None
pso = None
categorizer = None

logger = logging.getLogger(__name__)

TS_CMD = "./ts_wrapper.sh"


def lazy_load():
    global punct, pso, categorizer
    if not punct:
        punct = Punct()
    if not pso:
        pso = Pso()
    if not categorizer:
        categorizer = Categorizer(model_file=flask_app.config["WORD_EMBEDDINGS"],
                                  categories_file=flask_app.config["CATEGORIES_JSON"],
                                  kill_list_file=flask_app.config["KILL_LIST"])
@client.task(name='parse')
def enhance_video(video_json):
    logger.info("Analyzing video " + video_json["video_id"])
    lazy_load()
    parsed = parse_video(
        video_json, punct=punct, pso=pso, categorizer=categorizer)
    logger.info("Finished parsing video")
    return parsed





