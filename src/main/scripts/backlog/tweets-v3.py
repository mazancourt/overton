# reconstitutes full-tweets from the "bysentence" tweets
import datetime
from dotenv import load_dotenv

from hedwige_es.schema import HedwigeIndex, Tweet, HParagraph
from icecream import ic
import logging

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s'")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
load_dotenv()

start = datetime.datetime(2009, 3, 24)
increment = datetime.timedelta(days=1)
end = start + datetime.timedelta(days=1)
last = datetime.datetime(2022, 9, 23, 20, 0, 0)
tweets_v1 = HedwigeIndex("speech-bysentence-twitter-v1")
tweets_v1.connect()

tweets_v3 = HedwigeIndex("speech-document-twitter-v3")
tweets_v3.connect()
tweets_para_v3 = HedwigeIndex("speech-paragraph-twitter-v3")
tweets_para_v3.connect()

# Collect tweets per day, rebuild the "paragraph" = 1 tweet for each.
while start < last:
    end = start + increment
    s = Tweet.search(using=tweets_v1.es, index=tweets_v1.index)
    #s = s.query("match_all").filter("range", published={"gte": start.strftime("%Y-%m-%d"), "lt": end.strftime("%Y-%m-%d")})
    s = s.query("match_all").filter("range", published={"gte": start, "lt": end})
    r = s.execute()
    logger.info("Collecting %d tweets between %s and %s", r.hits.total.value, start, end)
    start = end

    all_tweets = dict()
    for tweet in s.scan():
        tweet_id, n = tweet.meta.id.split("_")
        num = int(n)
        if not all_tweets.get(tweet_id):
            all_tweets[tweet_id] = {"tweet": tweet, "sentences": {}, "terms": set(), "categories": set()}
        all_tweets[tweet_id]["sentences"][n] = tweet.sentence
        if "verbatim" in tweet:
            all_tweets[tweet_id]["terms"].update([v["word"] for v in tweet.verbatim])
        if "category" in tweet:
            all_tweets[tweet_id]["categories"].update(tweet.category)

    for tweet_id in all_tweets:
        old_tweet = all_tweets[tweet_id]["tweet"]
        old_tweet_dict = old_tweet.to_dict()
        all_sentences_dict = all_tweets[tweet_id]["sentences"]
        new_tweet = Tweet(**old_tweet_dict)
        new_tweet.fulltext = " ".join([all_sentences_dict[s] for s in sorted(list(all_sentences_dict.keys()))])
        if not new_tweet.speaking:
            new_tweet.speaking = old_tweet.username
        if not new_tweet.speaking:
            new_tweet.speaking = old_tweet.candidat
        if not new_tweet.username:
            new_tweet.username = old_tweet.candidat
        # Attention: le username peut parfois être le nom propre du candidat, pas son twitter-id
        new_tweet.url = f"https://twitter.com/{new_tweet.username}/status/{tweet_id}"
        new_tweet.meta.id = tweet_id
        new_tweet.save(using=tweets_v3.es, index=tweets_v3.index)

        # Create corresponding paragraph
        para = HParagraph()
        para.fulltext = new_tweet.fulltext
        para.published = new_tweet.published
        para.title = ""
        para.url = new_tweet.url
        para.belongs_to = new_tweet.meta.id
        para.speaking = new_tweet.speaking
        para.chunk_id = 0
        para.source = None  # to be fixed in Airflow
        para.type = "para"
        para.field = "text"
        para.meta.id = f"{new_tweet.meta.id}-{para.field}#{para.chunk_id}"
        para.relevant_terms = list(all_tweets[tweet_id]["terms"])
        para.all_terms = para.relevant_terms
        para.classification = list(all_tweets[tweet_id]["categories"])
        para.save(using=tweets_para_v3.es, index=tweets_para_v3.index)

logging.info("Finished re-import")