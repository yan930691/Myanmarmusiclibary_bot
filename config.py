import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None
ADMIN_ID = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None

# YouTube ရှာဖွေမှု သတ်မှတ်ချက်များ
SEARCH_QUERY = "မြန်မာသီချင်း"  # ဒါကို ပြောင်းလို့ရပါတယ်
MAX_RESULTS_PER_SEARCH = 5  # တစ်ခါရှာရင် ဘယ်နှစ်ပုဒ်ယူမလဲ
SEARCH_INTERVAL_MINUTES = 30  # ဘယ်နှစ်မိနစ်တစ်ခါ ရှာမလဲ

# Database
DATABASE_FILE = "music_catalog.db"

# Download Settings
DOWNLOAD_PATH = "downloads"
MAX_FILE_SIZE_MB = 50  # Telegram ရဲ့ ကန့်သတ်ချက်
