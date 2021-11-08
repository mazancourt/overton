import os
import re
from datetime import datetime

import scrapy
from scrapy import Request
from scrapy.linkextractors import LinkExtractor
from poliscrap.items import PoliscrapItem
from youtube_transcript_api import YouTubeTranscriptApi


class ViePubliqueSpider(scrapy.Spider):
    name = 'rn'
    allowed_domains = ['rassemblementnational.fr']
    start_urls = ['https://rassemblementnational.fr']
    custom_settings = {
        'DEPTH_LIMIT': os.environ.get("DEPTH_LIMIT", 0),
    }

    def parse(self, response):
        categories = LinkExtractor(restrict_css='ul#menu-actualites.menu')
        # Get pages for each category
        for link in categories.extract_links(response):
            yield scrapy.Request(url=link.url, callback=self.parse_category)
        # Check for a YT video (linked videos underneath the main one are not captured)
        for video in set(response.css(".video-container").xpath("//iframe").xpath("@src").getall()):
            path = video.split("/")
            if "www.youtube.com" in path:
                video_id = path[-1]
                yield self.parse_video(response, video, video_id)

    def parse_category(self, response):
        # Extract linked articles article list
        for url in response.css("a.fusion-read-more::attr(href)").getall():
            yield Request(url, callback=self.parse_speech)
        # crawl de la page suivante
        next_page = response.css('a[rel="next"]::attr(href)').get()
        if next_page:
            next_page = response.urljoin(next_page)
            yield scrapy.Request(next_page, callback=self.parse_category)

    def parse_speech(self, response):
        speech = PoliscrapItem()
        speech["index"] = "speech-rn"
        speech["url"] = response.url
        title = response.css("h1::text").get()
        if title:
            title = title.replace("\xA0", " ").strip()
        speech["title"] = title
        raw_text = response.css(".post-content").get()
        if raw_text:
            raw_text = raw_text.replace("\xA0", " ").strip()
            raw_text = re.sub(r"^<div.*?>\s+", "", raw_text)
            raw_text = re.sub(r"\s+</div>$", "", raw_text)
        speech["fulltext"] = raw_text
        who = response.css('a[rel="author"]::text').get()
        when = response.css('span.updated::text').get()
        if when and "T" in when:
            speech["published"] = datetime.strptime(when.split("T")[0], "%Y-%m-%d")
        else:
            return  # Don't care about pages without dates
        speech["category"] = response.css('a[rel="category tag"]::text').get()
        speech["description"] = ""
        speech["keywords"] = []
        speech["roles"] = []
        speech["persons"] = [who]
        speech["circumstance"] = ""
        speech["speaking"] = "UNK"
        speech["flags"] = [os.environ.get("SPEECH_RN_FLAGS", "")]
        yield speech

    def parse_video(self, response, video_url, video_id):
        speech = PoliscrapItem()
        speech["index"] = "speech-rn"
        speech["url"] = video_url
        speech["category"] = "video"
        speech["title"] = ""
        raw_text = ""
        for chunk in YouTubeTranscriptApi.get_transcript(video_id, languages=['fr']):
            raw_text += chunk["text"] + "\n"
        speech["fulltext"] = raw_text
        speech["published"] = datetime.now()
        speech["description"] = ""
        speech["keywords"] = []
        speech["roles"] = []
        speech["persons"] = []
        speech["circumstance"] = ""
        speech["speaking"] = "UNK"
        speech["flags"] = [os.environ.get("SPEECH_RN_FLAGS", "")]
        return speech
