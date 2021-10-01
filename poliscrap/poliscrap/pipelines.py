# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

# useful for handling different item types with a single interface
import logging
import types

from itemadapter import ItemAdapter
from elasticsearch_dsl import connections, analyzer, InnerDoc, Keyword, Text, Document, Date, Nested, token_filter
from collections import deque

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
    circumstance = Text(analyzer=french_analyzer)
    category = Keyword()
    keywords = Nested(Kw)
    persons = Nested(Person)


class PoliscrapPipeline:
    @classmethod
    def from_crawler(cls, crawler):
        ext = cls()
        es_settings = dict()
        es_servers = crawler.settings.get('ELASTICSEARCH_SERVERS', 'localhost')
        es_settings["hosts"] = es_servers if isinstance(es_servers, list) else [es_servers]
        es_settings["port"] = crawler.settings.get("ELASTICSEARCH_PORT", 8881)
        es_settings["use_ssl"] = True
        if 'ELASTICSEARCH_USERNAME' in crawler.settings:
            es_settings['http_auth'] = (crawler.settings['ELASTICSEARCH_USERNAME'],
                                        crawler.settings['ELASTICSEARCH_PASSWORD'])
        es_settings['timeout'] = crawler.settings.get('ELASTICSEARCH_TIMEOUT', 60)

        connections.create_connection(**es_settings)
        return ext

    def process_item(self, item, spider):
        if isinstance(item, types.GeneratorType) or isinstance(item, list):
            for each in item:
                self.process_item(each, spider)
        else:
            self.index_item(item)
            logging.debug('Item sent to Elastic Search %s' % item.get('url'))
            return item

    def index_item(self, item):
        s = Speech.search(index=item["index"]).query("match", url=item["url"])
        response = s.execute()
        if response.hits.total.value == 0:
            speech = Speech(url=item["url"], title=item["title"], published=item["published"],
                            fulltext=item["fulltext"],
                            description=item["description"], category=item["category"],
                            circumstance=item["circumstance"])
            speech.keywords = [Kw(kw=k.strip()) for k in item["keywords"]]
            q = deque(item["roles"])
            speech.persons = []
            for n in item["persons"]:
                person = Person(name=n, role="")
                if q:
                    person.role = q.popleft()
                speech.persons.append(person)
            speech.save(index=item["index"])
            logging.info(f"Saved speech with url {item['url']}")
        else:
            logging.info(f"Already indexed {item['url']}")
