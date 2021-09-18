from elasticsearch import Elasticsearch

es = Elasticsearch(hosts=['my.elasticsearch.server'], port=8881, use_ssl=True)
es.indices.close("speech-vie-publique")
es.indices.delete("speech-vie-publique")
