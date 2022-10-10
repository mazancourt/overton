# Some "para" videos don't have any published date - fix it using video's date
import logging

from dotenv import load_dotenv
from hedwige_es.schema import HedwigeIndex, HParagraph, YT

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s'")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
load_dotenv()

yt_para_v3 = HedwigeIndex("speech-paragraph-youtube-v3")
yt_v3 = HedwigeIndex("speech-document-youtube-v3")

yt_para_v3.connect()
yt_v3.connect()

s = HParagraph.search(using=yt_para_v3.es, index=yt_para_v3.index).query("match_all")

date_per_doc = {}
for para in s.scan():
    if not para.published:
        # logger.warning("%s (%s) has no date", para.meta.id, para.belongs_to)
        if para.belongs_to not in date_per_doc:
            doc = YT.get(para.belongs_to + "_0", using=yt_v3.es, index=yt_v3.index, ignore=404)
            if doc:
                date_per_doc[para.belongs_to] = doc.published
        if para.belongs_to not in date_per_doc:
            logger.error("Date not found for %s", para.belongs_to)
        else:
            para.published = date_per_doc[para.belongs_to]
            para.save(using=yt_para_v3.es, index=yt_para_v3.index)
