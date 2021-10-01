from elasticsearch_dsl import connections, analyzer, InnerDoc, Keyword, Text, Document, Date, Nested, token_filter

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
    category = Keyword()
    keywords = Nested(Kw)
    persons = Nested(Person)

    class Index:
        name = "speech-vie-publique"
