import os
from dotenv import load_dotenv

load_dotenv()  # carga .env desde la raíz

HF_ENDPOINT = os.getenv("HF_ENDPOINT_URL")
HF_TOKEN    = os.getenv("HF_TOKEN")

CAL_API_KEY = os.getenv("CAL_API_KEY")
CAL_EVENT_TYPE_ID = os.getenv("CAL_EVENT_TYPE_ID")
CAL_USERNAME = os.getenv("CAL_USERNAME")
CAL_EVENT_TYPE_SLUG = os.getenv("CAL_EVENT_TYPE_SLUG")
CAL_TZ = os.getenv("CAL_TIMEZONE", "America/Argentina/Buenos_Aires")

MP_TOKEN = os.getenv("MP_ACCESS_TOKEN")
PUBLIC_BASE = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
