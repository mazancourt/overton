import os

from elasticsearch import Elasticsearch
from elasticsearch_dsl import analyzer, InnerDoc, Keyword, Text, Document, Date, Nested, token_filter

# definition of the token filter/analyser for our index
# see: https://jolicode.com/blog/construire-un-bon-analyzer-francais-pour-elasticsearch

# This analyzer intentionally avoids any stemming in order to perform precise linguistically-oriented queries
# to the index.
# An evolution could implement parallel text fields (title/text) with stemming, in order to get advantage of
# stemming, while keeping original ones for precise queries.

french_elision = token_filter("french_elision", type="elision", articles_case=True,
                              articles=["l", "m", "t", "qu", "n", "s", "j", "d", "c", "jusqu", "quoiqu", "lorsqu",
                                        "puisqu"])
french_analyzer = analyzer('french_analyzer',
                           tokenizer="icu_tokenizer",
                           filter=[french_elision, "icu_folding"])

# Person, Kw (keyword) and Speech are the basic elements of our index

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
    circumstance = Text(analyzer=french_analyzer)
    category = Keyword()
    keywords = Nested(Kw)
    persons = Nested(Person)


class Polindex:
    # ElasticSearch connection
    es = None
    # default index
    index = None

    @classmethod
    def connect(cls, servers=None, port=None, username=None, password=None):
        """
        Connects to the ES server

        Singleton holding the connexion to ES. Get connection through Polindex.es when connexion is made.

        :param servers: server or list of servers
        :param port: port to be used (defaults to 8881)
        :param username: username accessing ES
        :param password: password for username
        :return: None.
        """
        es_settings = dict()
        es_servers = servers if servers else os.environ.get('ELASTICSEARCH_SERVER', 'localhost')
        es_settings["hosts"] = es_servers if isinstance(es_servers, list) else [es_servers]
        es_settings["port"] = port if port else os.environ.get("ELASTICSEARCH_PORT", 8881)
        es_settings["use_ssl"] = True
        es_settings['http_auth'] = (username if password else os.environ.get('ELASTICSEARCH_USERNAME'),
                                    password if password else os.environ.get('ELASTICSEARCH_PASSWORD'))
        es_settings['timeout'] = os.environ.get('ELASTICSEARCH_TIMEOUT', 60)

        cls.es = Elasticsearch(**es_settings)

    @classmethod
    def create_index(cls, index_name):
        """
        Create an index with French mapping

        :param index_name: name of the index
        :return: None
        """
        Speech.init(index=index_name, using=cls.es)

    @classmethod
    def drop_index(cls, index_name):
        """
        Removes the index from ES. This destroys all related documents. Handle with care!

        :param index_name: Name of the index
        :return: None
        """
        cls.es.indices.close(index_name)
        cls.es.indices.delete(index_name)
