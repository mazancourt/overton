import json
import logging
import re
import requests

logger = logging.getLogger(__name__)


def ts_extract(fulltext, ts_server_url):
    endpoint = ts_server_url + "/extract"
    headers = {"Content-Type": "application/json;charset=utf-8" }
    terms = []
    try:
        response = requests.post(endpoint, data=json.dumps({"text": fulltext}), headers=headers)
    except Exception as err:
        logger.warning("TS Extract error: WS raised exception %s", err)
    if response.status_code != 200:
        logger.warning("TS Extract error: bad response from WS: %s", response.text)
    else:
        for term in response.json():
            if float(term["spec"] > 1):
                terms.append(term["pilot"])
    return terms


def parse_video(video, pso, punct, categorizer, ts_server_url):
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
        terms = ts_extract(fulltext, ts_server_url)
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
