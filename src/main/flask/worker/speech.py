import json
import re
import requests
from celery.utils.log import get_task_logger
from nltk.tokenize import sent_tokenize

logger = get_task_logger(__name__)


def ts_extract(fulltext, ts_server_url):
    endpoint = ts_server_url + "/extract"
    headers = {"Content-Type": "application/json;charset=utf-8"}
    terms = []
    try:
        response = requests.post(endpoint, data=json.dumps({"text": fulltext}), headers=headers)
    except Exception as err:
        logger.warning("TS Extract error: WS raised exception %s", err)
        return terms
    if response.status_code != 200:
        logger.warning("TS Extract error: bad response from WS: %s", response.text)
    else:
        for term in response.json():
            if float(term["spec"]) > 1:
                terms.append(term["pilot"])
    return terms


def enhance(speech, pso, punct, categorizer, ts_server_url):
    sentences_split = speech.get("sentences_split")
    transcript = speech.get("transcript")
    fulltext = speech.get("text")
    # Step 1: rebuild full-text from transcript chunks if needed
    if transcript and not fulltext:
        parts = []
        for chunk in transcript:
            if not re.match(r"\[\w+?]", chunk["text"]):  # discard elements like "[Music]"
                parts.append(chunk["text"])
        fulltext = "\n".join(parts)
    sentences = []
    # Step 2: break full-text in sentences
    if not sentences_split:  # need to discover punctuation
        for sent in punct.rebuild_sentences(fulltext):
            sentences.append({"text": sent})
    else:  # sentences already have punctuation. Let's use a standard sentence splitter
        for sent in sent_tokenize(fulltext, "french"):
            sentences.append({"text": sent})
    # Step 3: qualify each sentence as problem/solution/other
    for sent in sentences:
        sent["type"] = pso.classify(sent["text"])[0]
    # Step 4: extract terms from fulltext and categorize them
    terms = ts_extract(fulltext, ts_server_url)
    if terms:
        for sent in sentences:
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
        logger.warning("No terms found")
    speech["sentences"] = sentences
    return speech
