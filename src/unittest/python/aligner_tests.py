import json
import os
import re
import unittest
from pathlib import Path

from worker.aligner import align_sentences


class TimestampAlignerTests(unittest.TestCase):

    cwd = Path(os.path.dirname(os.path.realpath(__file__)))

    @unittest.skip("worker is not packaged as a module, thus import align_sentences will fail under pybuilder")
    def test_long_alignment(self):
        # jfc has missing parts, but should be catched up, the two other are OK
        for speech in ["jfc.json", "macron.json", "montebourg-full.json"]:
            with open(self.cwd / speech) as data:
                video = json.load(data)
            # remove possibly existing timestamps
            sentences = [{"text": s["text"]} for s in video["sentences"]]
            transcripts = [t for t in video["transcript"] if not re.match(r"\[\w+]", t["text"])]
            align_ok, total, aligned = align_sentences(transcripts, sentences)
            print(f"{speech}: {aligned} out of {total}")
            self.assertTrue(align_ok, "Couldn't align " + speech)  # timestamp shall be marked up to the last sentence


if __name__ == '__main__':
    unittest.main()
