"""
Different implementations of NLP pipeline depending on input text format (from transcript to formatted text)
Each pipeline returns the updated speech object
"""
import logging
import re

from howler import TextTiler
from nltk import sent_tokenize

from worker.aligner import align_sentences
from worker.categorizer import categorize_sentences
from worker.tag_persons import tag_person_names

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
    if punct:
        for sent in punct.rebuild_sentences(text):
            sentences.append({"text": sent})
    else:
        sentences.append({"text", text})
    return sentences


def qualify_sentences(sentences, pso):
    """
    Apply PSO categorizer to each sentence
    :param sentences: list of sentences
    :param pso: PSO categorizer
    :return: the sentences enhanced with a "type" field
    """
    logger.info("Qualify sentence type")
    for sent in sentences:
        if len(sent) < 2000 and pso:
            try:
                sent["type"] = pso.classify(sent["text"])[0]
            except RuntimeError as e:
                logger.warning("Caught runtime error while categorizing sentence : ", e)
                sent["type"] = "other"
        else:
            sent["type"] = "na"


def tile_sentences(sentences):
    """
    Builds paragraphs from a flat list of sentences
    :param sentences: the sentences
    :return: the sentences, each with a "chunk_id" field determining the paragraph it belongs to
    """
    logger.info("Building text chunks from sentences")
    tiles = tiler.tile([sent["text"] for sent in sentences])
    last_chunk_id = 0
    for i, sent in enumerate(sentences):
        if i < len(tiles):
            sent["chunk_id"] = tiles[i]
            last_chunk_id = tiles[i]
        else:
            sent["chunk_id"] = last_chunk_id



def transcript_pipeline(speech, pso, punct, categorizer, namer) -> dict:
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
    tag_person_names(speech, categorizer, namer)
    return speech


def raw_text_pipeline(speech, punct, pso, categorizer, namer) -> dict:
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
    tag_person_names(speech, categorizer, namer)
    return speech


def punctuated_text_pipeline(speech, pso, categorizer, namer) -> dict:
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
    for sent in sent_tokenize(speech["text"], "french"):
        sentences.append({"text": sent})
    qualify_sentences(sentences, pso)
    tile_sentences(sentences)
    categorize_sentences(sentences, speech["text"], categorizer)
    speech["sentences"] = sentences
    tag_person_names(speech, categorizer, namer)
    return speech


def formatted_text_pipeline(speech, pso, categorizer, namer) -> dict:
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
    tag_person_names(speech, categorizer, namer)
    return speech
