from elasticsearch_dsl import connections, analyzer, InnerDoc, Keyword, Text, Document, Date, Nested, token_filter
import datetime
import json
import re

connections.create_connection(hosts=['overton.mazancourt.com'], port=8881, use_ssl=True,
                              http_auth=('elastic', 'mi3hmBVuKQ9fWTRquBDJ'))

# see: https://jolicode.com/blog/construire-un-bon-analyzer-francais-pour-elasticsearch
french_elision = token_filter("french_elision", type="elision", articles_case=True,
                              articles=["l", "m", "t", "qu", "n", "s", "j", "d", "c", "jusqu", "quoiqu", "lorsqu",
                                        "puisqu"])
french_analyzer = analyzer('french_analyzer',
                           tokenizer="icu_tokenizer",
                           filter=[french_elision, "icu_folding"])


class Person(InnerDoc):
    name = Keyword()
    role = Text()


class Kw(InnerDoc):
    kw = Text(analyzer=french_analyzer)


class Speech(Document):
    url = Keyword()
    title = Text(analyzer=french_analyzer)
    published = Date()
    fulltext = Text(analyzer=french_analyzer)
    description = Text(analyzer=french_analyzer)
    category = Keyword()
    keywords = Nested(Kw)
    persons = Nested(Person)

    class Index:
        name = "speech-vie-publique"

# Only at creation of index.
Speech.init()

count = 0
with open("vie-publique.json", "r") as vpl:
    for line in vpl.readlines():
        count += 1
        #if count >= 100:
        #    break
        data = json.loads(line)
        title = data["title"].strip()
        category = title.split(" ")[0].lower()
        url = data["url"].strip()
        if not False:  # check if url already present
            if category == "interview":
                cat = "itw"
            elif category == "conseil":
                cat = "cm"
            else:
                cat = "com"
            when = datetime.datetime.strptime(data["date"], "%Y-%m-%dT%H:%M:%S%z")
            raw_text = data["raw_text"].strip().replace("\xA0", " ")
            desc = data["desc"].strip()
            speech = Speech(
                url=url,
                title=title,
                fulltext=raw_text,
                published=when,
                category=cat,
                description=desc,
                keywords=[],
                persons=[])
            for p in zip(data["persons"]["names"], data["persons"]["roles"]):
                name = p[0].strip()
                role = re.sub(r"^[- \n]*", "", p[1]).strip()
                speech.persons.append(Person(name=name, role=role))
            for k in data["keywords"]:
                kw = k.strip()
                speech.keywords.append(Kw(kw=kw))
            speech.save()
