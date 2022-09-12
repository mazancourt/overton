import logging
import re
from collections import defaultdict
from operator import itemgetter

import math
from howler import helper_get_subsequences
from nltk import word_tokenize

logger = logging.getLogger(__name__)


def categorize_sentences(sentences, fulltext, categorizer, legacy=True):
    """
    Extracts terms and categories, map them to sentences (or paragraphs)
    :param sentences: list of sentences/paragraphs to tag
    :param fulltext: the concatenated text of all sentences
    :param categorizer: the extractor (Howler)
    :param legacy: create legacy format of flat one
    :return: None
    """
    logger.info("Extracting terms & categories")
    terms = categorizer(fulltext)
    logger.info("Mapping terms to sentences")
    if terms:
        lookup_term_re = {}
        for term in terms:
            lookup_term_re[term] = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
        for sent in sentences:
            if legacy:
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
            if legacy:
                cats.sort(key=itemgetter(1), reverse=True)
                sent["categories"] = dict((str(c), s) for c, s in cats)
                # debug info: get source matching cat
                sent["debug"] = {}
                for t in sentence_terms:
                    c = terms[t]["category"]
                    if c and terms[t]["source"]:
                        c += ":" + terms[t]["source"]
                    sent["debug"][t] = c
            else:   # flat format
                # normalize category score
                sent["cats"] = [{"value": cat, "score": score} for cat, score in cats]  # remove low scores ?
                sent["mapping"] = [{"value": term, "category": terms[term]["category"]} for term in sentence_terms]
                sent["all_terms"] = list(sentence_terms)
    else:
        logger.warning("No terms found")


def categorize_paragraphs(paragraphs, fulltext, extractor):
    categorize_sentences(paragraphs, fulltext, extractor, legacy=False)
