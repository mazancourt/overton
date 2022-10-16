from dotenv import load_dotenv
from hedwige_es.schema import HedwigeIndex, HedwigeDocument

load_dotenv()

amd_v3 = HedwigeIndex("amendement-document-an-v3")
amd_para_v3 = HedwigeIndex("amendement-paragraph-an-v3")

meta = {}

for index in ["amendement-document-an-v3", "amendement-paragraph-an-v3", "question-document-an-v3",
              "question-paragraph-an-v3", "cr-document-an-v3", "cr-paragraph-an-v3"]:
    idx = HedwigeIndex(index)
    is_paragraph = "paragraph" in index
    if not is_paragraph:
        meta = {}
    idx.connect()
    to_delete = []
    correct = 0
    catchable = 0
    s = HedwigeDocument.search(using=idx.es, index=idx.index)
    s = s.query("range", published={"gte": "2022-06-22"})
    for doc in s.scan():
        if not is_paragraph:
            if not doc.speaking and not is_paragraph:
                to_delete.append(doc.meta.id)
            else:
                meta[doc.meta.id] = {"speaking": doc.speaking, "published": doc.published}
                correct += 1
        else:   # paragraph
            if not doc.speaking:
                if doc.belongs_to in meta:
                    doc.speaking = meta[doc.belongs_to]["speaking"]
                    doc.published = meta[doc.belongs_to]["published"]
                    doc.save(using=idx.es, index=idx.index)
                    catchable += 1
                else:
                    to_delete.append(doc.meta.id)
    for d in to_delete:
        s = HedwigeDocument.get(d, using=idx.es, index=idx.index)
        s.delete(using=idx.es, index=idx.index)
    print("%s: %d deleted, %d caught up, %d to keep" % (idx.index, len(to_delete), catchable, correct))
