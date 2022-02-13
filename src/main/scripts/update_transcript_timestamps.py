import json
import re
import logging
import csv

from dotenv import load_dotenv
from google.cloud import storage
from hedwige_es.schema import YT, HedwigeIndex
from datetime import date, timedelta
from worker.aligner import align_sentences

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level='WARNING')

hedwige = HedwigeIndex("speech-bysentence-youtube-v1")
hedwige.connect()

gcs = storage.Client()
bucket_name = "ecureuil"
bucket = gcs.get_bucket(bucket_name)
video_prefixes = ["youtube_speech_catchup_yearly",
                  "youtube_speech_catchup_monthly",
                  "youtube_speech_catchup_daily",
                  "youtube_speech_hot"]

# First, create a map from video_id to GCS Blobs, for further download
id_to_blob = dict()
for prefix in video_prefixes:
    for blob in gcs.list_blobs(bucket, prefix=prefix):
        m = re.match(".*?/3-tagged-transcripts/.*?/(.*?).json", blob.name)
        if m:
            id_to_blob[m[1]] = blob
with open("update-timestamps.csv", "w") as upd:
    writer = csv.writer(upd)

    start = date.fromisoformat('2011-01-01')
    end = date.fromisoformat('2022-02-14')
    increment = timedelta(days=30)
    while start < end:
        print(start)
        s = YT.search(using=hedwige.es, index=hedwige.index)
        # Search for videos in the time range
        s = s.filter("range", published={"gte": start, "lt": start+increment})
        timestamped_sentences = dict()
        misaligned_sentences = dict()
        lost_video = dict()
        start += increment
        for yt in s.scan():
            video_id = yt.video_id
            if video_id not in timestamped_sentences and video_id not in misaligned_sentences:
                if video_id in id_to_blob:
                    logger.info(f"fetching video {video_id}")
                    video = json.loads(id_to_blob[video_id].download_as_text())
                    filtered_transcript = [t for t in video["transcript"] if not re.match(r"\[\w+]", t["text"])]
                    video_sentences = video["sentences"]
                    ok, aligned, total = align_sentences(filtered_transcript, video_sentences)
                    if ok:
                        timestamped_sentences[video_id] = video_sentences
                        logger.info(f"Video {video_id} from {yt.candidat} is correctly aligned")
                        writer.writerow(["CORRECT", video_id, id_to_blob[video_id].name])
                    else:
                        misaligned_sentences[video_id] = video
                        logger.warning(f"{video_id} has transcription errors")
                        writer.writerow(["WRONG", video_id, id_to_blob[video_id].name])
                else:
                    if video_id not in lost_video:
                        logger.warning(f"Cannot find video for {video_id}")
                        writer.writerow(["NOTFOUND", video_id])
                        lost_video[video_id] = True
                    continue
            if video_id in timestamped_sentences:
                m = re.match(r".*_(\d+)$", str(yt.meta.id))
                pos = int(m[1])
                if pos < len(timestamped_sentences[video_id]) and \
                        timestamped_sentences[video_id][pos]["text"] == yt.sentence and \
                        "start" in timestamped_sentences[video_id][pos]:
                    yt.start_time = timestamped_sentences[video_id][pos]["start"]
                    yt.duration = timestamped_sentences[video_id][pos]["duration"]
                    yt.save(using=hedwige.es, index=hedwige.index)
                else:
                    logger.warning(f"There's something wrong on {yt.meta.id}")

