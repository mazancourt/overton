import os
from pathlib import Path

from tqdm import tqdm
import json
import requests
import dotenv

dotenv.load_dotenv()

API_URL = "https://api-inference.huggingface.co/models/lincoln/flaubert-mlsum-topic-classification"
headers = {"Authorization": "Bearer " + os.getenv("HF_API_TOKEN"), "charset": "utf8"}


def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()


def get_topics(text, n_topics=2):
    extract = text
    if len(extract) > 512:
        i = extract.rfind(" ", 512)
        extract = text[0:i]
    output = query({"inputs": extract, 'parameters': {'truncation': 'only_first'}})
    if "error" in output:
        raise RuntimeError(output)
    else:
        topics = sorted(output[0], key=lambda item: item["score"], reverse=True)
        return topics[0:n_topics]


def topicalize_jsons(path_in, path_out):
    for source in path_in.glob("*.json"):
        file = source.name

        with open(source, "r", encoding="utf8") as t:
            data = json.loads(t.read())

        for d in tqdm(data, desc="topicalizing " + file):
            if "sentences" in d and d["sentences"]:
                full_text = []
                for sent in d["sentences"]:
                    sent["topics"] = get_topics(sent["text"], 5)
                    full_text.append(sent["text"])
                d["topics"] = get_topics("\n".join(full_text), 5)

        with open(path_out / file, "w", encoding="utf8") as out:
            json.dump(data, out)


if __name__ == '__main__':
    dir_in = Path("augmented")
    dir_out = Path("topicalized")
    dir_out.mkdir(exist_ok=True)
    topicalize_jsons(dir_in, dir_out)
