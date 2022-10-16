# reconstitutes video paragraphs and "documents" from the "bysentence" tweets
import datetime
import re

from dotenv import load_dotenv

from hedwige_es.schema import HedwigeIndex, Tweet, HParagraph, YT, Speech
from icecream import ic
import logging

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
load_dotenv()

start = datetime.datetime(2022, 6, 1)
increment = datetime.timedelta(days=1)
last = datetime.datetime(2022, 9, 14, 23, 30, 0)
press_v1 = HedwigeIndex("article-document-press-v1")
press_v1.connect()

press_v3 = HedwigeIndex("article-document-press-v3")
press_v3.connect()
press_para_v3 = HedwigeIndex("article-paragraph-press-v3")
press_para_v3.connect()

while start < last:
    end = start + increment
    s = Speech.search(using=press_v1.es, index=press_v1.index)
    s = s.query("match_all").filter("range", published={"gte": start, "lt": end})
    r = s.execute()
    logger.info("Collecting %d articles between %s and %s", r.hits.total.value, start, end)
    start = end

    all_paragraphs = {}
    for article in s.scan():
        article_id = article.meta.id

        if article.analysis:
            for sentence in article.analysis.sentences:
                chunk_id = int(sentence["chunk_id"])
                if not all_paragraphs.get(article_id):
                    all_paragraphs[article_id] = dict()
                if chunk_id not in all_paragraphs[article_id]:
                    all_paragraphs[article_id][chunk_id] = {"article": article, "terms": set(), "categories": set(),
                                                            "sentence": [], "speaking": set()}
                all_paragraphs[article_id][chunk_id]["sentence"].append(sentence.text)
                if "mapping" in sentence:
                    all_paragraphs[article_id][chunk_id]["terms"].update([v["value"] for v in sentence.mapping])
                if "cats" in sentence:
                    all_paragraphs[article_id][chunk_id]["categories"].update(c["value"] for c in sentence.cats)
                if "attribution" in sentence:
                    all_paragraphs[article_id][chunk_id]["speaking"].add(sentence.attribution["name"])
        else:
            logger.warning("No analysis for %s", article.url)
        article.analysis = None
        article.save(using=press_v3.es, index=press_v3.index)

    for article_id in all_paragraphs:
        for chunk_id in all_paragraphs[article_id]:
            article_data = all_paragraphs[article_id][chunk_id]
            article = article_data["article"]
            para = HParagraph()
            para.source = "PRESS"
            para.fulltext = " ".join(article_data["sentence"])
            para.published = article.published
            para.title = article.title
            para.url = article.url
            para.belongs_to = article_id
            para.speaking = list(article_data["speaking"])
            para.chunk_id = chunk_id
            para.type = "para"
            para.field = "text"
            para.meta.id = f"{article.meta.id}#{para.field}-{para.chunk_id}"
            para.relevant_terms = list(article_data["terms"])
            para.all_terms = list(article_data["terms"])
            para.classification = list(article_data["categories"])
            para.featured = False
            para.belongs_to = article_id
            para.save(using=press_para_v3.es, index=press_para_v3.index)
logger.info("Finished update.")
