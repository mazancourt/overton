import csv
import json
from operator import itemgetter
from pathlib import Path
from gensim.models import KeyedVectors
from nltk.tokenize import word_tokenize
from tqdm import tqdm

model = KeyedVectors.load_word2vec_format("../frWac_non_lem_no_postag_no_phrase_500_skip_cut200.bin", binary=True,
                                          unicode_errors="ignore")
with open("categories.json", encoding="utf8") as categories:
    cat = json.load(categories)
    allterms = []
    for c in cat:
        for sc in cat[c]:
            allterms.extend([{"key": w, "words": word_tokenize(w, language="french"), "subcat": sc, "cat": c}
                             for w in cat[c][sc]])


def pretty_term(term):
    return term["cat"] + "/" + term["subcat"] + "/" + term["key"]

root = Path("corpus/montebourg_2022")
categorized = open("categorized.csv", "w", encoding="utf8")
writer = csv.writer(categorized)
for extract in root.glob("*/*.tsv"):
    with open(extract, encoding="utf8") as terms:
        for line in tqdm(terms.readlines()):
            if line.startswith("#"):
                continue
            data = line.split("\t")
            form = data[2]
            spec = data[4]
            match = [(term, model.wmdistance(word_tokenize(form, language="french"), term["words"])) for term in allterms]
            best = [m for m in match if m[1] < 1]
            top = None
            if best:
                best.sort(key=itemgetter(1))
                if best[0][1] < 0.1:
                    top = [best[0]]
                elif len(best) > 15: # too ambiguous
                    top = []
                else:
                    top = best
            if top:
                writer.writerow([form, spec, top[0][1], top[0][0]["cat"], top[0][0]["subcat"], len(best),
                                 [(pretty_term(t[0]), t[1]) for t in best[0:min(20, len(best))]]])
            else:
                writer.writerow([form, spec, 0, "notfound", "notfound", len(best),
                                 [(pretty_term(t[0]), t[1]) for t in best[0:min(20, len(best))]]])

categorized.flush()
categorized.close()

