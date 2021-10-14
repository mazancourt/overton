# Extract sub-corpus from vie-publique.fr crawled website
from pathlib import Path
from tqdm import tqdm
from elasticsearch_dsl import Q
from politexts.elasticsearch import Polindex, Speech
from politexts.nlp import Nlp, text_to_id
from dotenv import load_dotenv

load_dotenv()

user = u"Emmanuel Macron "

Polindex.connect()
s = Speech.search(using=Polindex.es, index="speech-vie-publique")
s = s.query("nested", path="persons", query=Q('term', persons__name=user)).filter("range", published={"gt": "now-1M"})
s = s.doc_type(Speech)
results = s.execute()

speakers = set()
nlp = Nlp()
root = Path(text_to_id(user))
problems = root / Path("problems") / Path("fr")
problems.mkdir(parents=True, exist_ok=True)
solutions = root / Path("solutions") / Path("fr")
solutions.mkdir(parents=True, exist_ok=True)

for speech in results:
    fname = speech.meta.id + ".txt"
    pb = open(problems / fname, "w")
    sol = open(solutions / fname, "w")
    speakers.update([p.name for p in speech.persons])
    for sent in tqdm(nlp.split_sentences(speech.fulltext), unit="sentence", desc=str(speech.published)):
        cat = nlp.classify(sent)[0]
        if cat.startswith("Pro"):
            pb.write(sent + "\n")
        elif cat.startswith("Sol"):
            sol.write(sent + "\n")
    pb.close()
    sol.close()

with open(root / "stopwords.txt", "w") as stopwords:
    for word in speakers:
        stopwords.write(word)
        stopwords.write("\n")
