from typing import List
from dataclasses import dataclass
from howler import SentenceBuilder, Semantizer, Howler, Namer, TextTiler
from howler.deep import Pso


@dataclass
class Tools:
    sentence_builder: SentenceBuilder
    howler: Howler
    pso: Pso
    namer: Namer
    text_tiler: TextTiler
