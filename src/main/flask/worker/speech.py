import time
from dataclasses import dataclass

from celery.utils.log import get_task_logger
from worker.pipelines import transcript_pipeline, raw_text_pipeline, punctuated_text_pipeline, formatted_text_pipeline, \
    transcript_hot_pipeline, formatted_text_hot_pipeline, politics_pipeline
from worker.utils import Zone, Tools

logger = get_task_logger(__name__)

def enhance(speech, pso, punct, categorizer, namer):
    start = time.time()
    sentences_split = speech.get("sentences_split")
    transcript = speech.get("transcript")
    fulltext = speech.get("text")
    content_type = speech.get("content-type")

    if not content_type:
        if transcript and not fulltext:
            content_type = "transcript"
        elif fulltext:
            if sentences_split:
                content_type = "text/punctuated"
            else:
                content_type = "text/raw"
        else:
            content_type = "empty"
    if "content-type" in speech:
        del speech["content-type"]
    speech["meta"] = dict()
    speech["meta"]["content-type"] = content_type

    if content_type == "transcript":        # videos
        transcript_pipeline(speech, pso, punct, categorizer, namer)
    elif content_type == "text/raw":
        raw_text_pipeline(speech, pso, punct, categorizer, namer)
    elif content_type == "text/punctuated":
        punctuated_text_pipeline(speech, pso, categorizer, namer)
    elif content_type == "text/formatted":
        formatted_text_pipeline(speech, pso, categorizer, namer)
    else:
        logger.warning("Unknown content-type: %s", content_type)
    if content_type == "empty":
        logger.warning("Skipping empty content")
        pass

    speech["meta"]["classification_version"] = categorizer.classification_version()
    speech["meta"]["elapsed"] = time.time() - start
    return speech


def hot_parse(speech, tools: Tools):
    """
    Parses the speech to produce necessary data for indexing. The tasks to perform are declared in meta.zones
    :param speech: the json data
    :param tools: the instanciated set of tools
    :return: the updated speech (side-effect on input data)
    """
    zones = speech["meta"]["zones"]
    for z in zones:
        zone = Zone(**z)
        if zone.content_type == "transcript" or zone.content_type == "video/transcript":   # video
            transcript_hot_pipeline(speech, tools, zone)
        elif zone.content_type == "text/formatted":
            formatted_text_hot_pipeline(speech, tools, zone)
        elif zone.content_type == "text/raw" or zone.content_type == "text/punctuated":
            logger.warning("Content-type %s not supported in hot parse" % zone.content_type)
        elif zone.content_type == "empty":
            logger.warning("Skipping empty content")
        else:
            logger.warning("Unknown content-type: %s", zone.content_type)
    return speech

def politics_parse(speech, tools: Tools):
    zones = speech["meta"]["zones"]
    politics_pipeline(speech, zones, tools)
    return speech
