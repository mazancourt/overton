import re
import unicodedata
import nltk
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline


class Nlp:

    sent_splitter = nltk.data.load("tokenizers/punkt/french.pickle")

    def __init__(self):
        model = AutoModelForSequenceClassification.from_pretrained("mazancourt/politics-sentence-classifier", use_auth_token=True)
        tokenizer = AutoTokenizer.from_pretrained("mazancourt/politics-sentence-classifier", use_auth_token=True)
        self.nlp = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

    def classify(self, text):
        outputs = self.nlp(text)
        return outputs[0]["label"], outputs[0]["score"]

    @classmethod
    def split_sentences(cls, text, clean=True):
        if clean:
            text = cls.clean_text(text)
        return cls.sent_splitter.tokenize(text)

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
