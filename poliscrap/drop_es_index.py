from elasticsearch import Elasticsearch

index_name = "speech-rn"

es = Elasticsearch(hosts=['overton.mazancourt.com'], port=8881, use_ssl=True,
        http_auth=('elastic', 'mi3hmBVuKQ9fWTRquBDJ'))
es.indices.close(index_name)
es.indices.delete(index_name)
