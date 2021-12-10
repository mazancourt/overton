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

from overton.nlp import Punct, Pso
from overton.category import Categorizer

dotenv.load_dotenv()

punct = Punct()
pso = Pso()
categorizer = Categorizer(model_file=os.environ.get("WORD_EMBEDDINGS"),
                          categories_file=os.environ.get("CATEGORIES_JSON"),
                          kill_list_file=os.environ.get("KILL_LIST"))
logger = logging.getLogger(__name__)

TS_CMD = "./ts_wrapper.sh"


def termsuite_extract(fulltext, corpus_path, video_id):
    ts_corpus = corpus_path / video_id
    ts_corpus_fr = ts_corpus / "fr"
    ts_corpus_fr.mkdir(exist_ok=True, parents=True)
    with open(ts_corpus_fr / "all.txt", "w", encoding="utf8") as all_corpus:
        all_corpus.write(fulltext)
    ts_output = ts_corpus / "all.tsv"
    if not ts_output.exists():
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
                spec = float(fields[4])
                if spec > 1:
                    terms.append(term)
    return terms


def process_json(data, corpus_path):
    """
    Processes a dictionary representing video with transcripts.
    The transcripts are joined in sentences and the sentences are classified as problem/solution/other.
    Then terms are extracted from the text using TermSuite and classified with the Overton categories.

    :param data: the data containing the video info and trsancripts
    :param corpus_path: work directory for TermSuite (shall be a temp dir in production)
    :return: the data, enhanced with sentences, classes and categories
    """
    for d in data:
        video_id = d["video_id"]
        has_sentences = d.get("sentences_split")
        transcript = d.get("transcript")
        text = []
        if transcript:
            fulltext = ""
            if d.get("sentences"):
                fulltext = "\n".join([sent["text"].capitalize() for sent in d["sentences"]])
            else:
                d["sentences"] = []
                for chunk in transcript:
                    if not re.match(r"\[\w+?]", chunk["text"]):
                        text.append(chunk["text"])
                    if has_sentences:   # transcript already split in sentences
                        s = chunk["text"]
                        sent = {"text": s, "type": pso.classify(s)[0]}
                        d["sentences"].append(sent)
                    fulltext = "\n".join([s["text"] for s in d["sentences"]])
                if not has_sentences:
                    raw_text = " ".join(text)
                    for sentence in tqdm(punct.rebuild_sentences(raw_text), desc="classify", unit="sentence"):
                        sent = {}
                        sent["text"] = sentence
                        sent["type"] = pso.classify(sentence)[0]
                        d["sentences"].append(sent)
                        fulltext += sentence + "\n"
            terms = termsuite_extract(fulltext, corpus_path, video_id)
            if terms:
                for sent in tqdm(d["sentences"], desc="tag", unit="sentence"):
                    sent["categories"] = {}
                    sentence_terms = []
                    for term in terms:
                        if re.search(r"\b" + re.escape(term) + r"\b", sent["text"], re.IGNORECASE):
                            sentence_terms.append(term)
                    cats, matches = categorizer.categorize_sentence(sent["text"], terms=sentence_terms)
                    sent["categories"] = dict((str(c), s) for c, s in cats)
                    # debug info:
                    sent["debug"] = dict((w, str(c)) for w, c in matches.items())
            else:
                logger.warning("No terms for %s", video_id)
    return data


def process_jsons(source_path, target_path, ts_temp_dir):
    for source in source_path.glob("*.json"):
        file = source.name
        if ts_temp_dir:
            corpus = Path(ts_temp_dir)
        else:
            temp = tempfile.TemporaryDirectory(prefix="ts")
            corpus = Path(temp.name)
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
    process_jsons(source, target, "ts.corpus")
