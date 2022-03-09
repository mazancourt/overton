import time
import math
import re
from collections import defaultdict
from operator import itemgetter

from celery.utils.log import get_task_logger
from nltk.tokenize import sent_tokenize, word_tokenize
from howler.combo_basic import helper_get_subsequences
from howler import TextTiler
from worker.aligner import align_sentences

logger = get_task_logger(__name__)

tiler = TextTiler()

def enhance(speech, pso, punct, categorizer):
    start = time.time()
    sentences_split = speech.get("sentences_split")
    transcript = speech.get("transcript")
    fulltext = speech.get("text")
    filtered_transcript = []
    # Step 1: rebuild full-text from transcript chunks if needed
    if transcript and not fulltext:
        for chunk in transcript:
            if not re.match(r"\[\w+?]", chunk["text"]):  # discard elements like "[Music]"
                filtered_transcript.append(chunk)
        fulltext = "\n".join([t["text"] for t in filtered_transcript])
    sentences = []
    # Step 2: break full-text in sentences
    logger.info("Rebuilding sentences")
    if not sentences_split:  # need to discover punctuation
        for sent in punct.rebuild_sentences(fulltext):
            sentences.append({"text": sent})
    else:  # sentences already have punctuation. Let's use a standard sentence splitter
        for sent in sent_tokenize(fulltext, "french"):
            sentences.append({"text": sent})
    # Step 2.1: re-align timestamps from transcript if transcripts are available
    if filtered_transcript:
        logger.info("Re-building timestamps for sentences")
        align_sentences(filtered_transcript, sentences)
    # Step 3: group sentences in chunks
    logger.info("Detecting text chunks")
    tiles = tiler.tile([sent["text"] for sent in sentences])
    for i, sent in enumerate(sentences):
        sent["chunk_id"] = tiles[i]
    # Step 4: qualify each sentence as problem/solution/other
    logger.info("Qualifying sentences")
    for sent in sentences:
        sent["type"] = pso.classify(sent["text"])[0]
    # Step 5: extract terms from fulltext and categorize them
    logger.info("Extracting terms & categories")
    terms = categorizer(fulltext)
    logger.info("Mapping terms to sentences")
    if terms:
        lookup_term_re = {}
        for term in terms:
            lookup_term_re[term] = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
        for sent in sentences:
            sent["categories"] = {}
            sentence_terms = []
            for term in terms:
                if re.search(lookup_term_re[term], sent["text"]):
                    sentence_terms.append(term)
            # remove sub-terms, except those from the classification
            all_subsequences = []
            for term in sentence_terms:
                all_subsequences.extend(helper_get_subsequences(term))
                if " " in term:
                    all_subsequences.extend(word_tokenize(term))
            sentence_terms = [t for t in sentence_terms if t not in all_subsequences or terms[t]["match"] == "direct"]
            # Now compute the best category for the sentence
            sentence_categories = defaultdict(float)
            for sentence_term in sentence_terms:
                category = terms[sentence_term]["category"]
                if not category:
                    continue
                term_cat_score = terms[sentence_term]["cat_score"]
                if not term_cat_score:  # bonus for direct match
                    term_cat_score = 1.1
                sentence_categories[category] += term_cat_score
            # Normalize through softmax
            e_sum = sum([math.exp(x) for x in sentence_categories.values()])
            cats = []
            for cat in sentence_categories.keys():
                cats.append((cat, math.exp(sentence_categories[cat]) / e_sum))
            # sort categories by score
            cats.sort(key=itemgetter(1), reverse=True)
            sent["categories"] = dict((str(c), s) for c, s in cats)
            # debug info: get source matching cat
            sent["debug"] = {}
            for t in sentence_terms:
                c = terms[t]["category"]
                if c and terms[t]["source"]:
                    c += ":" + terms[t]["source"]
                sent["debug"][t] = c
    else:
        logger.warning("No terms found")
    speech["sentences"] = sentences
    speech["classification_version"] = categorizer.classification_version()
    speech["elapsed"] = time.time() - start
    return speech
