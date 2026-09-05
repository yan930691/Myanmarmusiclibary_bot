import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None

# ADMIN_ID ကို ကော်မာနဲ့ခြားပြီး ထည့်ထားရင် စာရင်းအဖြစ် ပြောင်းပါ
admin_ids_str = os.getenv("ADMIN_ID", "")
if admin_ids_str:
    # ကော်မာ ဒါမှမဟုတ် နေရာလွတ်တွေနဲ့ ခြားထားတဲ့ ID တွေကို ခွဲထုတ်ပြီး int စာရင်းအဖြစ် ပြောင်းပါ
    ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.replace(",", " ").split() if id.strip().isdigit()]
else:
    ADMIN_IDS = []

MONGODB_URI = os.getenv("MONGODB_URI")

# YouTube ရှာဖွေမှု သတ်မှတ်ချက်များ
SEARCH_QUERY = "မြန်မာသီချင်း"
MAX_RESULTS_PER_SEARCH = 5
SEARCH_INTERVAL_MINUTES = 60

# Download Settings
DOWNLOAD_PATH = "downloads"
MAX_FILE_SIZE_MB = 50

# Database Name
DATABASE_NAME = "music_catalog_db"
