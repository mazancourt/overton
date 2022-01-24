import json
import os

from dotenv import load_dotenv
from howler.deep import Semantizer, SentenceBuilder, Pso
from howler.howler import Howler
from worker.speech import enhance

load_dotenv()

howler = Howler("fr", categorisation_file=os.environ.get("CATEGORIES_JSON"),
                stop_list_file=os.environ.get("KILL_LIST"))
howler.config(compound_score_ratio=0.0, simple_word_min_score=0.0,
              semantizer=Semantizer(), similarity_threshold=0.56)

speech = json.load(open("transcript.json"))

enhanced = enhance(speech, Pso(), SentenceBuilder(), howler)
print(enhanced)
