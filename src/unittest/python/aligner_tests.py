import json
import os
import re
import unittest
from pathlib import Path

from worker.aligner import align_sentences


class TimestampAlignerTests(unittest.TestCase):

    cwd = Path(os.path.dirname(os.path.realpath(__file__)))

    def test_long_alignment(self):
        for speech in ["macron.json", "montebourg-full.json"]:
            with open(self.cwd / speech) as data:
                video = json.load(data)
            # remove possibly existing timestamps
            sentences = [{"text": s["text"]} for s in video["sentences"]]
            align_sentences([t for t in video["transcript"] if not re.match(r"\[\w+]", t["text"])], sentences)
            last_sentence = sentences[-1]
            self.assertTrue("start" in last_sentence)  # timestamp shall be marked up to the last sentence


if __name__ == '__main__':
    unittest.main()
