import unittest

from icecream import ic

from overton.nlp import Punct


class RebuildSentencesTest(unittest.TestCase):
    punct = Punct()

    def test_rebuild_simple_sentences(self):
        text = "l'immigration s'invite dans le débat tout le monde en parle sur toutes les chaînes dans tous les journaux voici notre invité"
        sentences = self.punct.rebuild_sentences(text)
        ic(sentences)
        self.assertEqual(len(sentences), 3)

