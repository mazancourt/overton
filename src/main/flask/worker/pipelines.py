"""
Different implementations of NLP pipeline depending on input text format (from transcript to formatted text)
Each pipeline returns the updated speech object
"""
import logging
import re
from collections import defaultdict

from howler import TextTiler
from nltk import sent_tokenize
#from icecream import ic

from worker.aligner import align_sentences, align_paragraphs
from worker.categorizer import categorize_sentences, categorize_paragraphs
from worker.tag_persons import tag_person_names, attribute_paragraphs
from worker.utils import Zone, Tools

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
        sentences.append({"text": text})
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

def tile_sentences_to_paragraphs(sentences, tiler):
    """
    Builds paragraphs from a flat list of sentences
    :param sentences: the sentences
    :param tiler: the text tiler
    :return: the paragraphs, each with a "chunk_id" field determining the paragraph id
    """
    logger.info("Building paragraphs from sentences")
    text = "\n\n".join([s["text"] for s in sentences])
    tiles = tiler.tile_text(text)
    paragraphs = []
    for i, p in enumerate(tiles):
        para_text = "\n".join(p)
        paragraphs.append({"text": para_text, "chunk_id": i})
    return paragraphs


def rebuild_doc_from_paragraphs(paragraphs) -> str:
    """
    Creates a document string from the paragraphs
    :param paragraphs: list of lists of sentences
    :return: the doc text
    """
    doc = []
    for para in paragraphs:
        para_text = "\n".join(para)
        doc.append(para_text)
    return "\n\n".join(doc)

def transcript_pipeline(speech, pso, punct, categorizer, namer) -> dict:
    """
    Analysis for video transcripts - full (legacy) version
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

def transcript_hot_pipeline(speech, tools:Tools, zone:Zone) -> dict:
    """
    Hot analysis of video-like contents:
    - repunctuate
    - split in paragraphs
    - align paragraphs with time marks
    - create full doc text
    :return: the updated speech structure
    """
    for field in zone.fields:
        filtered_transcript = []
        for transcript in speech[field]:
            if not re.match(r"\[\w+?]", transcript["text"]):  # discard elements like "[Music]"
                filtered_transcript.append(transcript)
        fulltext = "\n".join([t["text"] for t in filtered_transcript])
        sentences = repunctuate(fulltext, tools.sentence_builder)
        #ic(sentences)
        paragraphs = tools.text_tiler.tile_text("\n\n".join([s["text"] for s in sentences]))
        align_ok, num_para, para = align_paragraphs(filtered_transcript, paragraphs)
        for i, p in enumerate(para):
            p["chunk_id"] = i
        create_parse_slot(field, speech)
        speech["_parsed"][field]["paragraphs"] = para
        speech["_parsed"][field]["doc"] = {"text": rebuild_doc_from_paragraphs(paragraphs)}
    return speech


def create_parse_slot(field, speech):
    if "_parsed" not in speech:
        speech["_parsed"] = {}
    if field not in speech["_parsed"]:
        speech["_parsed"][field] = {}


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


def formatted_text_hot_pipeline(speech, tools: Tools, zone: Zone) -> dict:
    """
    Analysis for text with punctuation and paragraph breaks (usually from web crawling)
    Speech might include "title" and "description" fields together with mandatory "text"

    - extract sentences using punctuation,
    - rebuilds paragraphs,
    - attribute to person names per paragraph and per document if requested
    :param speech: input speech data structure
    :param tools: the parsing tools
    :param zone: the target zone
    :return: updated speech (side effect)
    """
    for field in zone.fields:
        if speech.get(field):
            paragraphs = []
            for i, paragraph in enumerate(tiler.tile_text(speech[field])):
                paragraphs.append({"text": "\n".join(paragraph), "chunk_id": i})
            doc_text = "\n\n".join(p["text"] for p in paragraphs)
            create_parse_slot(field, speech)
            speech["_parsed"][field]["paragraphs"] = paragraphs
            speech["_parsed"][field]["doc"] = {"text": doc_text}
            if zone.compute_attribution:
                tag_person_names(speech["_parsed"][field], tools.howler, tools.namer, by_paragraphs=True)
                speakers = attribute_paragraphs(speech["_parsed"][field]["paragraphs"])
                speech["_parsed"][field]["doc"]["speaking"] = speakers
            elif zone.speaker:
                speech["_parsed"][field]["doc"]["speaking"] = [zone.speaker]
    return speech

def politics_pipeline(speech:dict, zones:dict, tools:Tools)  -> dict:
    """
    Extract terms and other items from the paragraphs in the speech
    :param speech:
    :param zones:
    :param tools:
    :return: the updated speech
    """
    all_paragraphs = []
    fulltext = ""
    if "_parsed" not in speech:
        return speech
    # perform an extraction on each zone
    for z in zones:
        zone = Zone(**z)
        for field in zone.fields:
            if field not in speech["_parsed"]:
                continue
            doc = speech["_parsed"][field].get("doc")
            if doc:
                fulltext += doc["text"] + "\n\n"
            para = speech["_parsed"][field].get("paragraphs")
            if zone.speaker:
                for p in para:
                    if not p["speaking"]:
                        p["speaking"] = zone.speaker
            if para:
                all_paragraphs.extend(para)
    categorize_paragraphs(all_paragraphs, fulltext, tools.howler)
    return speech
