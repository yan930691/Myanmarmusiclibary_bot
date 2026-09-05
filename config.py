import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # SoundCloud အတွက် မလိုတော့ဘူး
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None

admin_ids_str = os.getenv("ADMIN_ID", "")
if admin_ids_str:
    ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.replace(",", " ").split() if id.strip().isdigit()]
else:
    ADMIN_IDS = []

MONGODB_URI = os.getenv("MONGODB_URI")

# SoundCloud အတွက် Search Query
SEARCH_QUERY = "မြန်မာသီချင်း"
MAX_RESULTS_PER_SEARCH = 5
SEARCH_INTERVAL_MINUTES = 60  # ၁ နာရီတစ်ခါ

DOWNLOAD_PATH = "downloads"
MAX_FILE_SIZE_MB = 50
DATABASE_NAME = "music_catalog_db"
