import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
import logging
import dotenv
from tqdm import tqdm

from overton.nlp import Punct, Pso, Categorizer

dotenv.load_dotenv()

punct = Punct()
pso = Pso()
categorizer = Categorizer(os.environ.get("WORD_EMBEDDINGS"))
logger = logging.getLogger(__name__)

TS_CMD = ["/usr/bin/java", "-cp",
          "/home/hugues/.local/termsuite/termsuite-core-3.0.10.jar fr.univnantes.termsuite.tools.TerminologyExtractorCLI",
          "-t", "/home/hugues/.local/treetagger/", "--tsv-properties", "pilot,lemma,spec,freq", "-l", "fr"]
          # add:  -c corpus --tsv all.tsv"

def process_json(data, corpus_path):
    """
    Processes a dictionary representing and transcripts.
    The transcripts are joined in sentences and the sentences are classified as problem/solution/other.
    Then terms are extracted from the text using TermSuite and classified with the Overton categories.

    :param data: the data containing the video info and trsancripts
    :param corpus_path: work directory for TermSuite (shall be a temp dir in production)
    :return: the data, enhanced with sentences, classes and categories
    """
    for d in data:
        video_id = d["video_id"]
        transcript = d["transcript"]
        text = []
        if transcript:
            if d["sentences"]:
                raw_text = "\n".join([sent["text"].capitalize() for sent in d["sentences"]])
            else:
                d["sentences"] = []
                for chunk in transcript:
                    if not re.match(r"\[\w+?\]", chunk["text"]):
                        text.append(chunk["text"])
                raw_text = "\n".join([t.capitalize() for t in text])
                for sentence in tqdm(punct.rebuild_sentences(raw_text), desc="classify", unit="sentence"):
                    sent = {}
                    sent["text"] = sentence
                    sent["type"] = pso.classify(sentence)[0]
                    d["sentences"].append(sent)
            # Launch TermSuite on raw_text
            ts_corpus = corpus_path / video_id
            ts_corpus_fr = ts_corpus / "fr"
            ts_corpus_fr.mkdir(exist_ok=True, parents=True)
            with open(ts_corpus_fr / "all.txt", "w", encoding="utf8") as all_corpus:
                all_corpus.write(raw_text)
            ts = TS_CMD.copy()
            ts_output = corpus_path / video_id / "all.tsv"
            ts.extend(["-c", ts_corpus.absolute().as_posix(), "--tsv", ts_output.absolute().as_posix()])
            logger.debug(ts)
            p = subprocess.run(ts, capture_output=True)
            if p.returncode != 0:
                logger.warning("TermSuite failed: %s", p.stderr)
            # find terms on sentences
            if ts_output.exists():
                terms = []
                matched = {}
                with open(ts_output, "r", encoding="utf8") as ts:
                    for line in ts.readlines():
                        if line.startswith("#"):
                            continue
                        fields = line.split("\t")
                        item = categorizer.categorize(fields[2])
                        if item:
                            terms.append(item)
                            matched[item.word] = 0
                for sent in tqdm(d["sentences"], desc="tag", unit="sentence"):
                    sent["categories"] = {}
                    for term in terms:
                        if re.search(r"\b" + re.escape(term.word) + r"\b", sent["text"], re.IGNORECASE):
                            matched[term.word] += 1
                            if term.cat in sent["categories"]:
                                sent["categories"][term.cat].append(term.theme)
                            else:
                                sent["categories"][term.cat] = [term.theme]
                missed = [w for w in matched if matched[w] == 0]
                if missed:
                    logger.warning("Missed %d out of %d terms", len(missed), len(terms))
            else:
                logger.warning("No terms for %s", video_id)
    return data


def process_jsons(source_path, target_path):
    for source in source_path.glob("*.json"):
        file = source.name
#        corpus = Path(tempfile.TemporaryDirectory())
        corpus = Path("ts.corpus")
        corpus.mkdir(exist_ok=True)
        tqdm.write(file)
        with open(source, "r", encoding="utf8") as t:
            data = json.loads(t.read())
        data = process_json(data, corpus_path=corpus)

        with open(target_path / file, "w", encoding="utf8") as out:
            json.dump(data, out)


if __name__ == '__main__':
    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    target.mkdir(exist_ok=True)
    print("Processing Json files from %s to %s" % (source, target))
    process_jsons(source, target)
