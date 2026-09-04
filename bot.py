import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config import BOT_TOKEN, CHANNEL_ID, SEARCH_INTERVAL_MINUTES
from database import init_db
from youtube_api import search_youtube_music
from handlers import start, search_command, stats_command, latest_command, button_handler
from handlers import process_new_video, content_exists_by_url

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ခေတ္တဖိုင်တွဲ ဖန်တီးပါ
os.makedirs("downloads", exist_ok=True)

async def auto_search_task(context: ContextTypes.DEFAULT_TYPE):
    """အလိုအလျောက် ရှာဖွေပြီး သီချင်းအသစ်တွေကို တင်ပေးမယ်"""
    logger.info("🔄 Auto-search running...")
    try:
        results = await asyncio.to_thread(search_youtube_music)
        if results:
            new_count = 0
            for video in results:
                if not content_exists_by_url(video['url']):
                    await process_new_video(video, context)
                    new_count += 1
                    await asyncio.sleep(2)  # Rate limit အတွက်
            if new_count > 0:
                logger.info(f"✅ Found {new_count} new songs")
            else:
                logger.info("ℹ️ No new songs found")
    except Exception as e:
        logger.error(f"❌ Auto-search error: {e}")

async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ချန်နယ်မှာ ဖိုင်အသစ်တင်ရင် အလုပ်လုပ်မယ်"""
    post = update.channel_post
    if not post:
        return
    
    # Audio ဖိုင်အတွက်
    if post.audio:
        audio = post.audio
        title = audio.title or "ခေါင်းစဉ်မသတ်မှတ်ရသေး"
        performer = audio.performer or "အဆိုတော်မသတ်မှတ်ရသေး"
        file_id = audio.file_id
        
        # Database ထဲ ရှိပြီးသားလား စစ်ပါ
        if content_exists_by_file_id(file_id):
            return
        
        # ဇော်ဂျီကနေ ယူနီကုဒ်ပြောင်းမယ်
        from rabbit import Rabbit
        title_uni = Rabbit.zg2uni(title)
        performer_uni = Rabbit.zg2uni(performer)
        
        # Database ထဲ သိမ်းမယ် (MongoDB)
        from database import save_content
        content_id = save_content(
            1, title_uni, performer_uni, "မြန်မာသီချင်းများ", 
            file_id, "audio", "", ""
        )
        
        if content_id:
            logger.info(f"✅ Saved from channel post: {title_uni}")
            # Player Message ပို့မယ်
            from handlers import send_player_message
            await send_player_message(context, title_uni, performer_uni, file_id, content_id)

def main():
    # Database ကို စတင်ဆောက်လုပ်ပါ (MongoDB)
    try:
        init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return
    
    # Application ကို စတင်ပါ
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers များ
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("latest", latest_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # ချန်နယ်ပို့စ်တွေကို စောင့်ကြည့်မယ်
    application.add_handler(MessageHandler(filters.AUDIO, channel_post_handler))
    
    # အလိုအလျောက် ရှာဖွေတဲ့ Task
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(
            auto_search_task,
            interval=SEARCH_INTERVAL_MINUTES * 60,  # စက္ကန့်ပုံစံ
            first=10  # Bot စဖွင့်တာ ၁၀ စက္ကန့်အကြာမှ စမယ်
        )
        logger.info(f"✅ Auto-search scheduled every {SEARCH_INTERVAL_MINUTES} minutes")
    
    # Bot ကို Run ပါ
    logger.info("🚀 Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
