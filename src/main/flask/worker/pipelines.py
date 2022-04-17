"""
Different implementations of NLP pipeline depending on input text format (from transcript to formatted text)
Each pipeline returns the updated speech object
"""
import logging
import re
from collections import Counter

from howler import TextTiler
from nltk import sent_tokenize

from worker.aligner import align_sentences
from worker.categorizer import categorize_sentences

tiler = TextTiler()
logger = logging.getLogger(__name__)


def repunctuate(text, punct):
    """
    Apply SentenceBuilder to input text
    :param text: input text as a list of words without any punctuation
    :param punct: list of re-punctuated sentences
    :return:
    """
    logger.info("Restoring punctuation")
    sentences = []
    for sent in punct.rebuild_sentences(text):
        sentences.append({"text": sent})
    return sentences


def qualify_sentences(sentences, pso):
    """
    Apply PSO categorizer to each sentence
    :param sentences: list of sentences
    :param pso: PSO categorizer
    :return: the sentences enhanced with a "type" field
    """
    logger.info("Qualifity sentence type")
    for sent in sentences:
        sent["type"] = pso.classify(sent["text"])[0]


def tile_sentences(sentences):
    """
    Builds paragraphs from a flat list of sentences
    :param sentences: the sentences
    :return: the sentences, each with a "chunk_id" field determining the paragraph it belongs to
    """
    logger.info("Building text chunks from sentences")
    tiles = tiler.tile([sent["text"] for sent in sentences])
    for i, sent in enumerate(sentences):
        sent["chunk_id"] = tiles[i]


def tag_person_names(speech, categorizer):
    """
    Annotate each sentence with person names identified in it
    :param speech: the speech data
    :param categorizer: the NLP engine
    :return: Nothing
    """
    all_persons = Counter()
    for sentence in speech["sentences"]:
        sent_persons = categorizer.extract_persons(sentence["text"])
        sentence["persons"] = list(sent_persons.keys())
        all_persons.update(sent_persons)
    speech["meta"]["persons"] = dict(all_persons)


def transcript_pipeline(speech, pso, punct, categorizer) -> dict:
    """
    Analysis for video transcripts:
    - repunctuate,
    - extract sentences,
    - align sentences with speech timestamps,
    - rebuilds paragraphs,
    - classify using PSO,
    - extract terms and categorize
    - extract person names per sentence and per document
    :param speech: input speech data structure
    :param pso: PSO categorizer
    :param punct: SentenceBuilder
    :param categorizer: Term extractor and categorizer
    :return: the updated speech
    """
    filtered_transcript = []
    for chunk in speech["transcript"]:
        if not re.match(r"\[\w+?]", chunk["text"]):  # discard elements like "[Music]"
            filtered_transcript.append(chunk)
    fulltext = "\n".join([t["text"] for t in filtered_transcript])
    sentences = repunctuate(fulltext, punct)
    align_sentences(filtered_transcript, sentences)
    tile_sentences(sentences)
    qualify_sentences(sentences, pso)
    categorize_sentences(sentences, fulltext, categorizer)
    speech["sentences"] = sentences
    tag_person_names(speech, categorizer)
    return speech


def raw_text_pipeline(speech, punct, pso, categorizer) -> dict:
    """
    Analysis for concatenated transcript text
    - repunctuate,
    - extract sentences,
    - rebuilds paragraphs,
    - classify using PSO,
    - extract terms and categorize,
    - extract person names per sentence and per document

    :param speech: input speech data structure
    :param pso: PSO categorizer
    :param punct: SentenceBuilder
    :param categorizer: Term extractor and categorizer
    :return: the updated speech
    """
    sentences = repunctuate(speech["fulltext"], punct)
    tile_sentences(sentences)
    qualify_sentences(sentences, pso)
    categorize_sentences(sentences, speech["fulltext"], categorizer)
    speech["sentences"] = sentences
    tag_person_names(speech, categorizer)
    return speech


def punctuated_text_pipeline(speech, pso, categorizer) -> dict:
    """
    Analysis for text with punctuation but no paragraph breaks
    - extract sentences using punctuation,
    - rebuilds paragraphs,
    - classify using PSO,
    - extract terms and categorize,
    - extract person names per sentence and per document
    :param speech: input speech data structure
    :param pso: PSO categorizer
    :param categorizer: Term extractor and categorizer
    :return: the updated speech
    """
    # sentences already have punctuation. Let's use a standard sentence splitter
    sentences = []
    for sent in sent_tokenize(speech["fulltext"], "french"):
        sentences.append({"text": sent})
    qualify_sentences(sentences, pso)
    tile_sentences(sentences)
    categorize_sentences(sentences, speech["fulltext"], categorizer)
    speech["sentences"] = sentences
    tag_person_names(speech, categorizer)
    return speech


def formatted_text_pipeline(speech, pso, categorizer) -> dict:
    """
    Analysis for text with punctuation and paragraph breaks (usually from web crawling)
    Speech might include "title" and "description" fields together with mandatory "text"

    - extract sentences using punctuation,
    - rebuilds paragraphs,
    - classify using PSO,
    - extract terms and categorize,
    - extract person names per sentence and per document
    :param speech: input speech data structure
    :param pso: PSO categorizer
    :param categorizer: Term extractor and categorizer
    :return: the updated speech
    """
    tiler = TextTiler()
    chunk_id = 0
    sentences = []
    fulltext = ""
    for zone in ["title", "description", "text"]:
        if speech.get(zone):
            fulltext += speech[zone] + "\n\n"
            for paragraph in tiler.tile_text(speech[zone]):
                chunk_id += 1
                for sent in paragraph:
                    sentences.append({"chunk_id": chunk_id, "text": sent, "zone": zone})
    qualify_sentences(sentences, pso)
    categorize_sentences(sentences, fulltext, categorizer)
    speech["sentences"] = sentences
    tag_person_names(speech, categorizer)
    return speech