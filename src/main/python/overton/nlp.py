import re
import unicodedata

from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline, AutoModelForTokenClassification


class Pso:
    """
    Classifier for sequences. Classifies as "problem", "solution" or "other"
    """

    def __init__(self):
        model_name = "mazancourt/politics-sentence-classifier"
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)

        self.nlp = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

    def classify(self, text):
        outputs = self.nlp(text)
        return outputs[0]["label"], outputs[0]["score"]
      

class Punct:

    def __init__(self):
        model_name = "oliverguhr/fullstop-punctuation-multilang-large"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForTokenClassification.from_pretrained(model_name)
        self.nlp = pipeline("ner", tokenizer=tokenizer, model=model, aggregation_strategy="simple")
        # Max input size for model seems to be 2200, so 2000 is a good choice
        self.MAX_SIZE = 2000

    def rebuild_sentences(self, text):
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"^\s+", "", text)
        start = 0
        text_length = len(text)
        sentences = []
        while start < text_length:
            end = self._find_word_boundary(start, text)
            if end == 0:
                sents = self._rebuild_sentences(text[start:])[0]
                sentences.extend(sents)
                break
            else:
                sents, i = self._rebuild_sentences(text[start:end])
                if i == 0 or len(sents) <= 1:
                    sentences.extend(sents)
                    start = end
                else:
                    sentences.extend(sents[:-1])
                    start += i+1
        return sentences

    def _rebuild_sentences(self, text):
        results = self.nlp(text)
        sentence = ""
        # restore punctuation from text
        sentences = []
        sentence = ""
        last_sentence_offset = 0
        for item in results:
            sentence += text[item["start"]:item["end"]]
            tag = item["entity_group"]
            if tag != "0":
                sentence += tag
            if tag == "." or tag == "?":
                sentences.append(sentence)
                sentence = ""
                last_sentence_offset = item["end"]
        if sentence:
            sentences.append(sentence)

        return [re.sub(r"^\s+", "", s) for s in sentences], last_sentence_offset

    # find offset of next text chunk
    def _find_word_boundary(self, start, text):
        text_length = len(text)
        if text_length - start < self.MAX_SIZE:
            return 0
        try:
            pos = text.index(" ", start + self.MAX_SIZE)
        except ValueError:
            # not found - hope remaining text is no too long
            pos = 0
        return pos


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
