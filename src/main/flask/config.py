import os
from dotenv import load_dotenv

load_dotenv()

CELERY_BACKEND = 'redis://default:nlp4tf1@localhost:6379'

HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
# WORD_EMBEDDINGS = os.environ.get("WORD_EMBEDDINGS")
CATEGORIES_JSON = os.environ.get("CATEGORIES_JSON")
KILL_LIST = os.environ.get("KILL_LIST")

# Disable cpu-intensive tasks, esp. in absence of GPU
ENABLE_DEEP_PSO = os.environ.get("ENABLE_DEEP_PSO", "yes") == "yes"
ENABLE_DEEP_SENTENCE_BUILDER = os.environ.get("ENABLE_DEEP_SENTENCE_BUILDER", "yes") == "yes"
ENABLE_DEEP_CATEGORIZER = os.environ.get("ENABLE_DEEP_CATEGORIZER", "yes") == "yes"
