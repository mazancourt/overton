# config for TS Server
import os

from dotenv import load_dotenv

load_dotenv()

TS_CMD = os.environ.get("TS_WRAPPER", "ts_wrapper.sh")
