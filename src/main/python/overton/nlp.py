import re
import unicodedata
import nltk
from itertools import chain
from nltk import bigrams
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline, AutoModelForTokenClassification


class Pso:
    """
    Classifier for sequences. Classifies as "problem", "solution" or "other"
    """

    def __init__(self):
        model = AutoModelForSequenceClassification.from_pretrained("mazancourt/politics-sentence-classifier",
                                                                   use_auth_token=True)
        tokenizer = AutoTokenizer.from_pretrained("mazancourt/politics-sentence-classifier", use_auth_token=True)
        self.nlp = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

    def classify(self, text):
        outputs = self.nlp(text)
        return outputs[0]["label"], outputs[0]["score"]


class Punct:

    def __init__(self):
        model_name = "oliverguhr/fullstop-punctuation-multilang-large"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForTokenClassification.from_pretrained(model_name)
        self.nlp = pipeline("ner", tokenizer=tokenizer, model=model)

    def rebuild_sentences(self, text):
        text = re.sub(r"\s+", " ", text)
        results = self.nlp(text, aggregation_strategy="simple")
        sentence = ""
        # restore punctuation from text
        sentences = []
        sentence = ""
        for chunk in results:
            sentence += text[chunk["start"]:chunk["end"]]
            tag = chunk["entity_group"]
            if tag != "0":
                sentence += tag
            if tag == ".":
                sentences.append(sentence)
                sentence = ""
        if sentence:
            sentences.append(sentence)

        return [re.sub(r"^\s+", "", s) for s in sentences]

    @classmethod
    def clean_text(cls, text):
        text = re.sub(r"(?<!\.)</p>", ".\n", text)
        text = re.sub(r"</p>", "\n", text)
        text = re.sub(r"<.*?>", " ", text)
        text = re.sub("…", "...", text)
        text = re.sub("’", "'", text)
        text = re.sub(r"\s+", " ", text)
        return text


def strip_accents(text):
    """
    Strip accents from input String.

    :param text: The input string.
    :type text: String.

    :returns: The processed String.
    :rtype: String.
    """
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore')
    text = text.decode("utf-8")
    return str(text)


def text_to_id(text):
    """
    Convert input text to id.

    :param text: The input string.
    :type text: String.

    :returns: The processed String.
    :rtype: String.
    """
    text = strip_accents(text.lower())
    text = re.sub('[ ]+', '_', text)
    text = re.sub('[^0-9a-zA-Z_-]', '', text)
    return text
