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

TS_CMD = "./ts_wrapper.sh"


def termsuite_extract(fulltext, corpus_path, video_id):
    ts_corpus = corpus_path / video_id
    ts_corpus_fr = ts_corpus / "fr"
    ts_corpus_fr.mkdir(exist_ok=True, parents=True)
    with open(ts_corpus_fr / "all.txt", "w", encoding="utf8") as all_corpus:
        all_corpus.write(fulltext)
    ts_output = ts_corpus / "all.tsv"
    ts = [TS_CMD, ts_corpus.absolute().as_posix(), ts_output.absolute().as_posix() ]
    p = subprocess.run(ts, capture_output=True)
    if p.returncode != 0:
        logger.warning("TermSuite failed: command %s returned %s", p.args, p.stderr)
    # find terms associated with a category
    terms = []
    if ts_output.exists():
        with open(ts_output, "r", encoding="utf8") as ts:
            for line in ts.readlines():
                if line.startswith("#"):
                    continue
                fields = line.split("\t")
                term = fields[2]
                item = categorizer.categorize(term)
                if item:
                    terms.append((term, item))
    return terms

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
        transcript = d.get("transcript")
        text = []
        if transcript:
            fulltext = ""
            if d.get("sentences"):
                fulltext = "\n".join([sent["text"].capitalize() for sent in d["sentences"]])
            else:
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
                    fulltext += sentence + "\n"
            terms = termsuite_extract(fulltext, corpus_path, video_id)
            # Launch TermSuite on raw_text
            if terms:
                matched = dict()
                for t in terms:
                    matched[t[0]] = 0
                for sent in tqdm(d["sentences"], desc="tag", unit="sentence"):
                    sent["categories"] = {}
                    for term in terms:
                        if re.search(r"\b" + re.escape(term[0]) + r"\b", sent["text"], re.IGNORECASE):
                            matched[term[0]] += 1
                            if term[1].cat in sent["categories"]:
                                sent["categories"][term[1].cat].append(term[1].theme)
                            else:
                                sent["categories"][term[1].cat] = [term[1].theme]
                missed = [w for w in matched if matched[w] == 0]
                if missed:
                    logger.warning("Missed %d out of %d terms in %s", len(missed), len(terms), video_id)
                    logger.warning("Missing: %s", " & ".join(missed))
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
