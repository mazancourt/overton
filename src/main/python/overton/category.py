# Categorization of phrases in the Overton Classification
# uses both Spacy matcher to locate entries from the classification and
# word2vec resources to semantically match extracted terms to classification entries (using Word Mover Distance)
import functools
import json
import importlib.resources as pkg_resources
import math
import re
from operator import itemgetter
from typing import Optional
from collections import Counter

from gensim.models import KeyedVectors
from nltk import word_tokenize
import spacy
from spacy.attrs import LEMMA
from spacy.matcher import PhraseMatcher


class Entry:
    """
    Item in the Classification
    """
    def __init__(self, word, path):
        self.word = word
        self.tokens = [w.lower() for w in word_tokenize(word, language="french")]
        self.category = Category(path)
        self.has_oov = False

    def __str__(self):
        return str(self.category) + ":" + self.word


class Category:
    def __init__(self, path_items):
        self.path = path_items

    def __str__(self):
        return "/".join(self.path)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return self.path == other.path

    @staticmethod
    def from_str(text: str):
        path = text.split("/")
        return Category(path)


class ClassificationTree:
    def __init__(self, categories_file):
        self.entries = []
        self._load_entries(categories_file)
        self.folders = {}
        for entry in self.entries:
            folder = entry.category
            if folder not in self.folders:
                self.folders[folder] = [entry]
            else:
                self.folders[folder].append(entry)

    def _load_entries(self, categories_file: Optional[str]) -> None:
        if categories_file:
            with open(categories_file, encoding="utf8") as cat:
                categories = json.load(cat)
        else:
            from . import models
            with pkg_resources.open_text(models, "categories.json") as cat:
                categories = json.load(cat)
        self._load_each_entry(categories, [])

    def _load_each_entry(self, node, path):
        if isinstance(node, dict):
            for c in node:
                self._load_each_entry(node[c], path + [c])
        else:   # list of entries
            self.entries.extend([Entry(word=w, path=path) for w in node])


# terms to remove from vector comparison (too noisy)
class KillList:
    def __init__(self, pathname):
        self.kill = []
        self.killre = re.compile(r"\b(?:est|sont)\b", re.IGNORECASE | re.UNICODE)

        if pathname:
            with open(pathname, "r", encoding="utf8") as k:
                for line in k.readlines():
                    line = line.strip()
                    if line.startswith("#") or len(line) == 0:
                        continue
                    else:
                        self.kill.append(line)

    def __contains__(self, item):
        return item in self.kill or re.search(r"\b(?:est|sont)\b", item)


class Categorizer:
    def __init__(self, model_file, categories_file=None, kill_list_file=None):
        self.parser = spacy.load('fr_core_news_sm', exclude=["ner"])
        self.model = KeyedVectors.load_word2vec_format(model_file, binary=True, unicode_errors="ignore")
        self.kill_list = KillList(kill_list_file)
        self.classification = ClassificationTree(categories_file)
        self._mark_oov()
        self.matcher = PhraseMatcher(self.parser.vocab, attr=LEMMA)
        self._build_matchers()

    def _build_matchers(self):
        """
        Creates SpaCy matchers from the categories entries
        """
        for folder, entries in self.classification.folders.items():
            patterns = []
            for entry in entries:
                patterns.append(self.parser(entry.word))
            self.matcher.add(str(folder), patterns)

    # Mark entries that have OOV tokens (thus should not be used for vector comparison)
    def _mark_oov(self):
        for entry in self.classification.entries:
            entry.has_oov = self.has_oov(entry.tokens)

    def has_oov(self, tokens):
        return len([t for t in tokens if t not in self.model.key_to_index]) > 0

    def direct_match(self, text: str):
        """
        evaluates a direct match with the classification (using Spacy Matchers)
        :param text:
        :return: dict of folders associated with match count and a dict of matches
        """
        counter = Counter()
        matches = dict()
        doc = self.parser(text)
        for match_id, start, end in self.matcher(doc):
            term = doc[start:end].text
            cat = Category.from_str(self.parser.vocab.strings[match_id])
            counter[cat] += 1
            matches[term] = cat
        return counter, matches

    @functools.lru_cache(maxsize=2048)
    def categorize_scores(self, form, n_results=5):
        if form in self.kill_list:
            return []
        else:
            tokens = word_tokenize(form, language="french")
            match = [(term, self.model.wmdistance(tokens, term.tokens))
                     for term in self.classification.entries if not term.has_oov]
            best = [m for m in match if m[1] < 1]
            top = []
            if best:
                best.sort(key=itemgetter(1))
                if best[0][1] < 0.1:
                    top = [best[0]]
                elif len(best) > 15:  # too ambiguous
                    top = []
                else:
                    top = best
            return top[0:min(len(top), n_results)]

    def find_category(self, phrase: str) -> Optional[Entry]:
        """
        Find the most appropriate category for the input
        :param phrase: input word or group of word
        :return: closest entry in the category tree
        """
        cats = self.categorize_scores(phrase, 1)
        if len(cats) > 0:
            return cats[0][0]
        else:
            return None

    def categorize_sentence(self, text, terms, n_cat_per_term=1):
        """
        Computes the most likely categories from a text using direct matches from the Classification +
        semantic matching on terms
        :param text: the input sentence (or paragraph)
        :param terms: the extracted terms from the text
        :param: n_cat_per_term: number of categories to retain for each term
        :return: a (sorted) list of couples (category, score) and a dict of matching terms
        """
        categories, matches = self.direct_match(text)
        for term in terms:
            entries = self.categorize_scores(term, n_results=n_cat_per_term)
            if term not in matches:
                matches[term] = None
            for e in entries:
                cat = e[0].category
                categories[cat] += 1-e[1]
                if not matches[term]:
                    matches[term] = str(e[0])
        # Normalize through softmax
        e_sum = sum([math.exp(x) for x in categories.values()])
        result = []
        for cat in categories.keys():
            result.append((cat, math.exp(categories[cat]) / e_sum))
        result.sort(key=itemgetter(1), reverse=True)
        return result, matches
