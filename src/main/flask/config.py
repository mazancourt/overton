import os
from dotenv import load_dotenv

load_dotenv()

CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'

HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
WORD_EMBEDDINGS = os.environ.get("WORD_EMBEDDINGS")
CATEGORIES_JSON = os.environ.get("CATEGORIES_JSON")
KILL_LIST = os.environ.get("KILL_LIST")
