import json
import re
from pathlib import Path

from tqdm import tqdm

from overton.nlp import Punct, Pso

punct = Punct()
pso = Pso()

root = Path("with_transcripts")
for source in root.glob("*.json"):
    file = source.name
    tqdm.write(file)

    with open(source, "r", encoding="utf8") as t:
        data = json.loads(t.read())

    for d in data:
        transcript = d["transcript"]
        text = []
        if transcript:
            d["sentences"] = []
            for chunk in transcript:
                if not re.match(r"\[\w+?\]", chunk["text"]):
                    text.append(chunk["text"])
            raw_text = " ".join(text)
            for sentence in tqdm(punct.rebuild_sentences(raw_text), desc="classify", unit="sentence"):
                sent = {}
                sent["text"] = sentence
                sent["type"] = pso.classify(sentence)[0]
                d["sentences"].append(sent)

    with open(Path("augmented") / source, "w", encoding="utf8") as out:
        json.dump(data, out)
