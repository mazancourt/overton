from dataclasses import dataclass
from howler import SentenceBuilder, Semantizer, Howler, Namer, TextTiler
from howler.deep import Pso
from typing import List


@dataclass
class Tools:
    sentence_builder: SentenceBuilder
    howler: Howler
    pso: Pso
    namer: Namer
    text_tiler: TextTiler

@dataclass
class Zone:
    """
    Zone in a speech header.
    Zones allow to determine different content-types for different fields in the incoming speech
    """
    content_type: str
    fields: List[str]
    lang: str = "fr"
    compute_attribution: bool = False
