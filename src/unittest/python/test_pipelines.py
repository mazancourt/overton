import json
import os
import unittest
from pathlib import Path

from tasks import _lazy_load
from worker.pipelines import politics_pipeline
from worker.speech import hot_parse


class TestPipelines(unittest.TestCase):

    CWD = Path(os.path.dirname(os.path.realpath(__file__)))
    TOOLS = _lazy_load()

    def test_politics_pipeline(self):
        with open(self.CWD / "politics_article.json") as art:
            speech = json.load(art)
        zones = speech["meta"]["zones"]
        extracted = politics_pipeline(speech, zones, self.TOOLS)
        terms = [m["value"] for m in speech["_parsed"]["fulltext"]["paragraphs"][0]["mapping"]]
        cats = [m["value"] for m in speech["_parsed"]["fulltext"]["paragraphs"][0]["cats"]]
        self.assertIn("salon des sports", terms)
        self.assertIn("Sport", cats)

    def test_hot_attribution(self):
        with open(self.CWD / "article_elections.json") as art:
            speech = json.load(art)
        extracted = hot_parse(speech, self.TOOLS)
        self.assertIn("Emmanuel Macron", speech["speaking"])
        self.assertIn("Jean-Luc Mélenchon", speech["speaking"])

    def test_hot_pipeline(self):
        with open(self.CWD / "crawled_article.json") as art:
            speech = json.load(art)
        extracted = hot_parse(speech, self.TOOLS)
        people = [m["speaking"] for m in speech["_parsed"]["fulltext"]["paragraphs"]]
        self.assertIn("Stéphane Civier", people)

    # this test needs repunctuation model ON
    def test_long_video(self):
        with open(self.CWD / "paris.json") as paris:
            speech = json.load(paris)
        extracted = hot_parse(speech, self.TOOLS)
        found = False
        for p in extracted["_parsed"]["transcript"]["paragraphs"]:
            if "réseau de chaleur" in p["text"]:
                found = True
                break
        self.assertTrue(found)


if __name__ == '__main__':
    unittest.main()
