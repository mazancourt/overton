# Extract sub-corpus from vie-publique.fr crawled website
from pathlib import Path
from tqdm import tqdm
from elasticsearch_dsl import Q
from dotenv import load_dotenv
from politexts.elasticsearch import Polindex, Speech
from politexts.nlp import Nlp, text_to_id

load_dotenv()

USER = u"Emmanuel Macron "

Polindex.connect()
s = Speech.search(using=Polindex.es, index="speech-vie-publique")
s = s.query("nested", path="persons", query=Q('term', persons__name=USER)).\
    filter("range", published={"gt": "now-1M"})
s = s.doc_type(Speech)
results = s.execute()

speakers = set()
nlp = Nlp()
root = Path(text_to_id(USER))
problems = root / Path("problems") / Path("fr")
problems.mkdir(parents=True, exist_ok=True)
solutions = root / Path("solutions") / Path("fr")
solutions.mkdir(parents=True, exist_ok=True)

for speech in results:
    fname = speech.meta.id + ".txt"
    pb = open(problems / fname, "w", encoding="utf8")
    sol = open(solutions / fname, "w", encoding="utf8")
    speakers.update([p.name for p in speech.persons])
    for sent in tqdm(nlp.split_sentences(speech.fulltext),
                     unit="sentence",
                     desc=str(speech.published)):
        cat = nlp.classify(sent)[0]
        if cat.startswith("Pro"):
            pb.write(sent + "\n")
        elif cat.startswith("Sol"):
            sol.write(sent + "\n")
    pb.close()
    sol.close()

with open(root / "stopwords.txt", "w", encoding="utf8") as stopwords:
    for word in speakers:
        stopwords.write(word)
        stopwords.write("\n")
