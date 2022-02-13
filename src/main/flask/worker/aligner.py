from howler.deep import SentenceBuilder
import logging

logger = logging.getLogger(__name__)


def align_sentences(transcript, sentences):
    """
    Aligns sentences with verbatims found in the speech. Adds appx start and duration for each sentence

    :param transcript: timestamped text elements that yield to the (rebuilt) sentences
    :param sentences: the list of rebuilt sentences from the input text
    :return: True if all sentences were aligned
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

    start_prev_chunk = transcript[0].get("start", 0)
    duration_prev_chunk = 0
    pos_in_text = 0
    alignment_ok = True
    chunk_id = 0
    transcript_length = len(transcript)
    # Now match the transcript items simply by looking at character blocks.
    while chunk_id < transcript_length:
        chunk = transcript[chunk_id]
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
            chunk_id += 1
        else:
            # we're lost... try to catchup
            logger.warning("bad alignment between sentences and transcript. Some timestamps will be wrong")
            for n in range(chunk_id+1, min(chunk_id+10, transcript_length-1)):
                candidate = transcript[n]
                candidate_block = SentenceBuilder.depunctuate(candidate["text"]).replace(" ", "")
                pos = text_block.find(candidate_block, pos_in_text)
                # verify that we're not matching a chunk miles away and that the next chunk is coherent
                candidate_next_block = SentenceBuilder.depunctuate(transcript[n+1]["text"]).replace(" ", "")
                if pos > 0 and pos - pos_in_text < 2000 and \
                        text_block[pos+len(candidate_block):].startswith(candidate_next_block):
                    logger.info(f"Catch up: forward {chunk_id} to {n}")
                    pos_in_text = pos
                    chunk_id = n
                    break
            else:
                alignment_ok = False
                break
    # Catchup for sentences that were found inside a transcript chunk and thus not timestamped
    num_sentences = 0
    aligned_sentences = 0
    start_prev_sentence = 0
    duration_prev_sentence = 0
    for s in sentences:
        num_sentences += 1
        if "start" not in s:
            s["start"] = start_prev_sentence
            s["duration"] = duration_prev_sentence
        else:
            aligned_sentences += 1
            start_prev_sentence = s["start"]
            duration_prev_sentence = s["duration"]

    return alignment_ok, num_sentences, aligned_sentences
