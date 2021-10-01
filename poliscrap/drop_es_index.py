from elasticsearch import Elasticsearch

index_name = "speech-rn"

es = Elasticsearch(hosts=ELASTICSEARCH_SERVERS, port=8881, use_ssl=True,
        http_auth=(ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD))
es.indices.close(index_name)
es.indices.delete(index_name)
