import re
import os
from datetime import datetime

import scrapy
from scrapy import Request
from scrapy.linkextractors import LinkExtractor
from poliscrap.items import PoliscrapItem

class ViePubliqueSpider(scrapy.Spider):
    name = 'vie_publique'
    allowed_domains = ['vie-publique.fr']
    start_urls = [os.environ.get("START_URL", 'https://www.vie-publique.fr/discours')]
    custom_settings = {
        'DEPTH_LIMIT': os.environ.get("DEPTH_LIMIT", 0)
    }
    link_extractor = LinkExtractor(restrict_css='div .teaserSimple--content')

    def parse(self, response):
        self.logger.info('Parsing from page %s', response.url)
        # Sur une page, on va chercher les discours référencés
        for link in self.link_extractor.extract_links(response):
            yield Request(link.url, callback=self.parse_speech)
        # crawl de la page suivante
        next_page = response.css('a[rel="next"]::attr(href)').get()
        if next_page:
            next_page = response.urljoin(next_page)
            yield scrapy.Request(next_page, callback=self.parse)

    def parse_speech(self, response):
        raw_text = response.css(".field--name-field-texte-integral").get()
        raw_text = re.sub(r"^<span.*?>\s*", "", raw_text)
        raw_text = re.sub(r"\s*</span>$", "", raw_text)
        raw_text = raw_text.strip().replace("\xA0", " ")

        speech = PoliscrapItem()
        speech["index"] = "speech-vie-publique"
        speech["url"] = response.url
        speech["title"] = response.css("h1::text").get().strip()
        speech["fulltext"] = raw_text
        cat = speech["title"].lower().split(" ")
        if "interview" in cat:
            speech["category"] = "itw"
        elif cat[0] == "conseil":
            speech["category"] = "cm"
        else:
            speech["category"] = "com"
        when = response.xpath("//time/@datetime").get()
        speech["published"] = datetime.strptime(when, "%Y-%m-%dT%H:%M:%S%z")
        speech["description"] = response.css(".discour--desc > h2::text").get().strip()
        speech["keywords"] = [tag.strip() for tag in response.css(".btn-tag::text").getall()]
        speech["roles"] = [re.sub(r"^[- \n]*", "", r.strip())
                           for r in response.css("ul.line-intervenant").css("li::text").getall()]
        speech["persons"] = [p.strip() for p in response.css("ul.line-intervenant").css("li").css("a::text").getall()]
        circumstance = response.css(".field--name-field-circonstance::text").get()
        if circumstance:
            circumstance = circumstance.strip()
        speech["circumstance"] = circumstance
        speech["speaking"] = self.speaking(speech["persons"], speech["roles"], speech["published"])
        speech["flags"] = [os.environ.get("SPEECH_VIE_PUBLIQUE_FLAGS", "")]
        yield speech

    @staticmethod
    def speaking(persons, roles, published):
        when = published.replace(tzinfo=None)
        for r in roles:
            if re.match(r"pr.+sident de la r.+publique", r.lower()):
                return "PR"
        for pers in persons:
            p = pers.lower()
            if (re.match(r"emmanuel macron", p) and when >= datetime(2017, 5, 14)) or \
                (re.match(r"fran.+ois hollande", p) and datetime(2012, 5, 15) <= when < datetime(2017, 5, 14)) or \
                (re.match(r"nicolas sarkozy", p) and datetime(2007, 5, 16) <= when < datetime(2012, 5, 15)) or \
                (re.match(r"jacques chirac", p) and datetime(1995, 5, 17) <= when < datetime(2007, 5, 16)) or \
                (re.match(r"fran.+ois mitterrand", p) and datetime(1981, 5, 21) <= when < datetime(1995, 5, 17)) or \
                (re.match(r"val.+ry giscard d.+estaing", p) and datetime(1974, 5, 27) <= when < datetime(1981, 5, 21)):
                return "PR"
        else:
            return "UNK"

