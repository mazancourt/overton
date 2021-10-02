import re
from datetime import datetime

import scrapy
from scrapy import Request
from scrapy.linkextractors import LinkExtractor
from poliscrap.items import PoliscrapItem

class ViePubliqueSpider(scrapy.Spider):
    name = 'vie_publique'
    allowed_domains = ['vie-publique.fr']
    start_urls = ['https://www.vie-publique.fr/discours']
    custom_settings = {
        'DEPTH_LIMIT': os.environ.get("DEPTH_LIMIT", 0)
    }
    link_extractor = LinkExtractor(restrict_css='div .teaserSimple--content')

    def parse(self, response):
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
        raw_text = re.sub(r"^<span.*?>\s+", "", raw_text)
        raw_text = re.sub(r"\s+</span>$", "", raw_text)
        raw_text = raw_text.strip().replace("\xA0", " ")

        speech = PoliscrapItem()
        speech["index"] = "speech-vie-publique"
        speech["url"] = response.url
        speech["title"] = response.css("h1::text").get().strip()
        speech["fulltext"] = raw_text
        cat = speech["title"].split(" ")[0].lower()
        if cat == "interview":
            speech["category"] = "itw"
        elif cat == "conseil":
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
        yield speech
