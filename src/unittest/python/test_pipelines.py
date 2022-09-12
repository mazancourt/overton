import json
import os
import unittest
from pathlib import Path

from tasks import _lazy_load
from worker.pipelines import politics_pipeline
from worker.speech import hot_parse


class TestPipelines(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # Store where we are as the test can be run by itself or through pybuilder
        cls.cwd = Path(os.path.dirname(os.path.realpath(__file__)))
        cls.tools = _lazy_load()


    def test_politics_pipeline(self):
        with open(self.cwd / "politics_article.json") as art:
            speech = json.load(art)
        zones = speech["meta"]["zones"]
        extracted = politics_pipeline(speech, zones, self.tools)
        terms = [m["value"] for m in speech["_parsed"]["fulltext"]["paragraphs"][0]["mapping"]]
        cats = [m["value"] for m in speech["_parsed"]["fulltext"]["paragraphs"][0]["cats"]]
        self.assertIn("salon des sports", terms)
        self.assertIn("Sport", cats)


    def test_hot_pipeline(self):
        with open(self.cwd / "crawled_article.json") as art:
            speech = json.load(art)
        extracted = hot_parse(speech, self.tools)
        people = [m["speaking"] for m in speech["_parsed"]["fulltext"]["paragraphs"]]
        self.assertIn("Stéphane Civier", people)


if __name__ == '__main__':
    unittest.main()
