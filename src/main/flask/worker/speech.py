import time

from celery.utils.log import get_task_logger
from worker.pipelines import transcript_pipeline, raw_text_pipeline, punctuated_text_pipeline, formatted_text_pipeline

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

    if content_type == "transcript":
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
