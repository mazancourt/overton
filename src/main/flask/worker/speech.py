import logging
import re

from tqdm import tqdm

logger = logging.getLogger(__name__)

TS_CMD = "./ts_wrapper.sh"


def parse_video(video, pso, punct, categorizer):
    video_id = video["video_id"]
    has_sentences = video.get("sentences_split")
    transcript = video.get("transcript")
    text = []
    if transcript:
        fulltext = ""
        if video.get("sentences"):
            fulltext = "\n".join([sent["text"].capitalize() for sent in video["sentences"]])
        else:
            video["sentences"] = []
            for chunk in transcript:
                if not re.match(r"\[\w+?]", chunk["text"]):
                    text.append(chunk["text"])
                if has_sentences:  # transcript already split in sentences
                    s = chunk["text"]
                    sent = {"text": s, "type": pso.classify(s)[0]}
                    video["sentences"].append(sent)
                fulltext = "\n".join([s["text"] for s in video["sentences"]])
            if not has_sentences:
                raw_text = " ".join(text)
                for sentence in punct.rebuild_sentences(raw_text):
                    sent = {"text": sentence, "type": pso.classify(sentence)[0]}
                    video["sentences"].append(sent)
                    fulltext += sentence + "\n"
        terms = []  # termsuite_extract(fulltext, corpus_path, video_id)
        if terms:
            for sent in video["sentences"]:
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
        return video