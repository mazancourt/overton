# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

# useful for handling different item types with a single interface
import logging
import types
from collections import deque

from politexts.elasticsearch import Polindex, Speech, Person, Kw


class PoliscrapPipeline:
    @classmethod
    def from_crawler(cls, crawler):
        ext = cls()
        Polindex.connect(servers=crawler.settings.get('ELASTICSEARCH_SERVERS', 'localhost'),
                         port=crawler.settings.get("ELASTICSEARCH_PORT", 8881),
                         username=crawler.settings["ELASTICSEARCH_USERNAME"],
                         password=crawler.settings["ELASTICSEARCH_PASSWORD"])
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
        s = Speech.search(index=item["index"], using=Polindex.es).query("match", url=item["url"])
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
