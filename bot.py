import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

try:
    from config import BOT_TOKEN, YOUTUBE_API_KEY, CHANNEL_ID, ADMIN_IDS, MONGODB_URI
    from database import init_db
    logger.info("✅ All imports successful!")

    # MongoDB ချိတ်ဆက်မှု စမ်းသပ်ပါ
    from pymongo import MongoClient
    client = MongoClient(MONGODB_URI)
    db = client['music_catalog_db']
    db.list_collection_names()
    logger.info("✅ MongoDB connection successful!")

    def main():
        logger.info("🚀 Starting bot...")
        # ... ကျန်တဲ့ Bot Code ...
        
except Exception as e:
    logger.error(f"❌ Fatal error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
