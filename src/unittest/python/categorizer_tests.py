import os
import unittest

from dotenv import load_dotenv
from overton.category import Categorizer

load_dotenv()


class CategorizerTest(unittest.TestCase):

    def setUp(self) -> None:
        self.categorizer = Categorizer(model_file=os.environ.get("WORD_EMBEDDINGS"),
                                       categories_file=os.environ.get("CATEGORIES_JSON"),
                                       kill_list_file=os.environ.get("KILL_LIST"))

    def test_direct_match(self):
        s = "les migrants et les migrants sont un sujet de la prochaine présidentielle"
        cats, matches = self.categorizer.direct_match(s)
        # shall match (twice) on "migrants" and once on "prochaine présidentielle"
        self.assertEqual(len(cats), 2)
        self.assertIn("migrants", matches.keys())

    def test_kill_list(self):
        terms = ["chasse est incompatible", "politique"]
        for t in terms:
            self.assertTrue(t in self.categorizer.kill_list)
        self.assertFalse("développement durable" in self.categorizer.kill_list)

    def test_full_categorization(self):
        s = "il faut donc augmenter le smic, mais tout le monde n'est pas smicard"
        categories = self.categorizer.categorize_sentence(s, ["smic", "smicard", "monde"])
        self.assertEqual(len(categories), 2)


if __name__ == '__main__':
    unittest.main()
