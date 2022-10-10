# reconstitutes video paragraphs and "documents" from the "bysentence" tweets
import datetime
import re

from dotenv import load_dotenv

from hedwige_es.schema import HedwigeIndex, Tweet, HParagraph, YT
from icecream import ic
import logging

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s'")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
load_dotenv()

start = datetime.datetime(2007, 8, 30)
increment = datetime.timedelta(days=1)
last = datetime.datetime(2022, 9, 23, 20, 0, 0)
yt_v1 = HedwigeIndex("speech-youtube-v2")
yt_v1.connect()

yt_v3 = HedwigeIndex("speech-document-youtube-v3")
yt_v3.connect()
yt_para_v3 = HedwigeIndex("speech-paragraph-youtube-v3")
yt_para_v3.connect()

# Collect videos per day, rebuild the "paragraphs" index.
while start < last:
    end = start + increment
    s = YT.search(using=yt_v1.es, index=yt_v1.index)
    s = s.query("match_all").filter("range", published={"gte": start, "lt": end})
    r = s.execute()
    logger.info("Collecting %d videos between %s and %s", r.hits.total.value, start, end)
    start = end

    all_videos = dict()
    for yt in s.scan():
        match = re.match(r"(.*)_(\d+)$", yt.meta.id)
        vid = match.group(1)
        n = match.group(2)
        para_num = int(yt["chunk_id"])
        if not all_videos.get(vid):
            all_videos[vid] = dict()
        if not all_videos[vid].get(para_num):
            all_videos[vid][para_num] = {"video": yt, "sentences": {}, "terms": set(), "categories": set()}
        all_videos[vid][para_num]["sentences"][n] = yt.sentence
        if "verbatim" in yt:
            all_videos[vid][para_num]["terms"].update([v["word"] for v in yt.verbatim])
        if "category" in yt:
            all_videos[vid][para_num]["categories"].update(yt.category)

    # Rebuild videos, one "document" per paragraph (ie per chunk_id)
    for vid in all_videos:
        for para_num in all_videos[vid]:
            old_yt = all_videos[vid][para_num]["video"]
            old_yt_dict = old_yt.to_dict()
            all_sentences_dict = all_videos[vid][para_num]["sentences"]
            new_yt = YT(**old_yt_dict)
            new_yt.sentence = " ".join([all_sentences_dict[s] for s in sorted(list(all_sentences_dict.keys()))])
            if not new_yt.speaking:
                new_yt.speaking = old_yt.candidat

            # Attention: le username peut parfois être le nom propre du candidat, pas son twitter-id
            new_yt.meta.id = f"{vid}_{para_num}"
            new_yt.save(using=yt_v3.es, index=yt_v3.index)
            logger.info("saved video %s in %s", new_yt, yt_v3.index)
            # Create corresponding paragraphs - unless no sentences, which means that paragraphs already exist in v3
            if not all_videos[vid][para_num]["sentences"]:
                continue
            para = HParagraph()
            para.fulltext = new_yt.sentence
            para.published = new_yt.published
            para.title = new_yt.snippet.title
            para.url = new_yt.url
            para.belongs_to = new_yt.video_id
            para.speaking = new_yt.speaking
            para.chunk_id = new_yt.chunk_id
            para.source = None  # to be fixed in Airflow
            para.type = "para"
            para.field = "transcript"
            para.meta.id = f"{new_yt.meta.id}#{para.field}-{para.chunk_id}"
            para.relevant_terms = list(all_videos[vid][para_num]["terms"])
            para.all_terms = para.relevant_terms
            para.classification = list(all_videos[vid][para_num]["categories"])
            para.save(using=yt_para_v3.es, index=yt_para_v3.index)
            logger.info("saved paragraph %s in %s", para.meta.id, yt_para_v3.index)

#    if r.hits.total.value > 0:
#        break
logging.info("Finished re-import")
