import json
from pathlib import Path

root = Path("augmented")
corpus = Path("corpus")
corpus.mkdir(exist_ok=True)

for f in root.glob("*json"):
    who = f.stem
    with open(f, "r", encoding="utf8") as transcripts:
        data = json.load(transcripts)
    for d in data:
        id = d["video_id"]
        if "sentences" in d:
            problem = corpus / who / id / "problem" / "fr"
            problem.mkdir(parents=True, exist_ok=True)
            solution = corpus / who / id / "solution" / "fr"
            solution.mkdir(parents=True, exist_ok=True)
            pbm_txt = open(problem / "problems.txt", "w", encoding="utf8")
            sol_txt = open(solution / "solutions.txt", "w", encoding="utf8")

            for s in d["sentences"]:
                if s["type"] == "problem":
                    pbm_txt.write(s["text"] + "\n")
                elif s["type"] == "solution":
                    sol_txt.write(s["text"] + "\n")
            pbm_txt.flush()
            pbm_txt.close()
            sol_txt.flush()
            sol_txt.close()
