import os
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from pathlib import Path

es_settings = dict()
es_servers = os.environ.get('ELASTICSEARCH_SERVER', 'localhost')
es_settings["hosts"] = es_servers if isinstance(es_servers, list) else [es_servers]
es_settings["port"] = os.environ.get("ELASTICSEARCH_PORT", 8881)
es_settings["use_ssl"] = True
es_settings['http_auth'] = (os.environ.get('ELASTICSEARCH_USERNAME'),
                                os.environ.get('ELASTICSEARCH_PASSWORD'))
es_settings['timeout'] = os.environ.get('ELASTICSEARCH_TIMEOUT', 60)

client = Elasticsearch(**es_settings)

s = Search(using=client, index="speech-rn")
#s = s.query("match", fulltext="immigration")
s = s.filter("range", **{'published': {'gte': '2011-01-01', 'lt': '2015-12-31'}})
response = s.execute()
corpus = "rn-2011-2015"
root = Path(corpus)
if not root.exists():
    root.mkdir()
count = 0
for r in s.scan():
    # when = r["published"]
    path = corpus / Path("/speech-%03d.txt" % count)
    count += 1
    with open(path, "w") as txt:
        txt.write(r["title"])
        txt.write("\n\n")
        txt.write(r["fulltext"])
    if count >= 1000:
        break

print(s.count())
