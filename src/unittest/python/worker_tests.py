import os
import unittest
from pathlib import Path
from howler.howler import Howler

from dotenv import load_dotenv

class MyTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Store where we are as the test can be run by itself or through pybuilder
        cls.cwd = Path(os.path.dirname(os.path.realpath(__file__)))
        cls.howler = Howler("fr", categorisation_file=os.environ.get("CATEGORIES_JSON"),
                            stop_list_file=os.environ.get("KILL_LIST"))

    def test_enhance(self):

        self.assertEqual(True, False)  # add assertion here


if __name__ == '__main__':
    unittest.main()
