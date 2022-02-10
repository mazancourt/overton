from howler.deep import SentenceBuilder
import logging

logger = logging.getLogger(__name__)


def align_sentences(transcript, sentences):
    """
    Aligns sentences with verbatims found in the speech. Adds appx start and duration for each sentence

    :param transcript: timestamped text elements that yield to the (rebuilt) sentences
    :param sentences: the list of rebuilt sentences from the input text
    :return: None
    """

    # The algorithm works on the simple assumption that each transcript part should be exactly a part of the
    # "depunctuated" text and that transcripts follow each other in sequence.
    # We use the texts with no spaces and no added puncutation and match the characters from the transcript with the
    # character from the sentences
    # weakness: if transcript parts are lost, the algorithm stops aligning

    text_block = ""
    char_index = []

    # create an index of sentences per character position in the (unpunctuated) text
    for sentence_id, s in enumerate(sentences):
        unpunctuated = SentenceBuilder.depunctuate(s["text"])
        sentence_chars = unpunctuated.replace(" ", "")
        # map chars position range to the current sentence id
        char_index.extend([sentence_id for _ in sentence_chars])
        text_block += sentence_chars
    timestamped_sentence = [False] * len(sentences)

    start_prev_chunk = 0
    duration_prev_chunk = 0
    pos_in_text = 0
    # Now match the transcript items simply by looking at character blocks.
    for chunk in transcript:
        transcript_block = SentenceBuilder.depunctuate(chunk["text"]).replace(" ", "")
        if text_block[pos_in_text:pos_in_text+len(transcript_block)] == transcript_block:
            sentence_id = char_index[pos_in_text]
            if not timestamped_sentence[sentence_id]:
                timestamped_sentence[sentence_id] = True
                sentences[sentence_id]["start"] = start_prev_chunk
                sentences[sentence_id]["duration"] = duration_prev_chunk + chunk["duration"]
            else:
                sentences[sentence_id]["duration"] += chunk["duration"]
            start_prev_chunk = chunk["start"]
            duration_prev_chunk = chunk["duration"]
            pos_in_text += len(transcript_block)
        else:
            # we're lost
            logger.warning("bad alignment between sentences and transcript. Some timestamps will be missing")
            break
