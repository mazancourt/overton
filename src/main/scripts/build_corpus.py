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
        vid = d["video_id"]
        if "sentences" in d:
            problem = corpus / who / vid / "problem" / "fr"
            problem.mkdir(parents=True, exist_ok=True)
            solution = corpus / who / vid / "solution" / "fr"
            solution.mkdir(parents=True, exist_ok=True)
            all_dir = corpus / who / vid / "all" / "fr"
            all_dir.mkdir(parents=True, exist_ok=True)
            pbm_txt = open(problem / "problems.txt", "w", encoding="utf8")
            sol_txt = open(solution / "solutions.txt", "w", encoding="utf8")
            all_txt = open(all / "all.txt", "w", encoding="utf8")

            for s in d["sentences"]:
                text = s["text"].capitalize() + "\n"
                all_txt.write(text)
                if s["type"] == "problem":
                    pbm_txt.write(text)
                elif s["type"] == "solution":
                    sol_txt.write(text)
            all_txt.flush()
            all_txt.close()
            pbm_txt.flush()
            pbm_txt.close()
            sol_txt.flush()
            sol_txt.close()
