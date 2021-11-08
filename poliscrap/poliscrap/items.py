# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy import Field


class PoliscrapItem(scrapy.Item):
    index = Field()
    url = Field()
    title = Field()
    fulltext = Field()
    category = Field()
    published = Field()
    description = Field()
    keywords = Field()
    persons = Field()
    roles = Field()
    circumstance = Field()
    speaking = Field()
    flags = Field()

