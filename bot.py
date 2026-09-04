#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YouTube Music Bot - မြန်မာသီချင်းတွေကို အလိုအလျောက် ရှာဖွေပြီး ချန်နယ်မှာ တင်ပေးမယ့် Bot
"""

import os
import sys
import asyncio
import logging
import traceback
from datetime import datetime

# ============ Logging Setup ============
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# ============ Main Function ============
def main():
    try:
        logger.info("🚀 Starting YouTube Music Bot...")
        
        # ---- 1. Config ----
        from config import (
            BOT_TOKEN,
            YOUTUBE_API_KEY,
            CHANNEL_ID,
            ADMIN_IDS,
            MONGODB_URI,
            SEARCH_QUERY,
            MAX_RESULTS_PER_SEARCH,
            SEARCH_INTERVAL_MINUTES,
            DOWNLOAD_PATH,
            MAX_FILE_SIZE_MB,
            DATABASE_NAME
        )
        logger.info("✅ Config loaded successfully!")
        
        # ---- 2. Database ----
        from database import init_db, client, db, test_connection, get_stats
        logger.info("📊 Initializing database...")
        init_db()
        
        if not test_connection():
            logger.error("❌ MongoDB connection failed!")
            sys.exit(1)
        logger.info("✅ Database connected successfully!")
        
        # ---- 3. YouTube API ----
        from youtube_api import search_youtube_music, extract_video_id
        logger.info("✅ YouTube API loaded successfully!")
        
        # ---- 4. Converter ----
        from converter import (
            download_audio_from_youtube,
            convert_mp4_to_mp3,
            get_file_size_mb,
            zg2uni,
            cleanup_temp_files
        )
        logger.info("✅ Converter loaded successfully!")
        
        # ---- 5. Handlers ----
        from handlers import start, search_command, button_handler
        logger.info("✅ Handlers loaded successfully!")
        
        # ---- 6. Telegram Imports ----
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import (
            Application,
            CommandHandler,
            MessageHandler,
            CallbackQueryHandler,
            ContextTypes,
            filters
        )
        logger.info("✅ Telegram imports loaded successfully!")
        
        # ---- 7. Create Download Path ----
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)
        logger.info(f"📁 Download path: {DOWNLOAD_PATH}")
        
        # ---- 8. Bot Handlers ----
        async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """ချန်နယ်မှာ ဖိုင်အသစ်တင်ရင် အလုပ်လုပ်မယ်"""
            post = update.channel_post
            if not post:
                return
            
            logger.info(f"📩 New channel post: {post.message_id}")
            
            if post.audio:
                audio = post.audio
                title = audio.title or "ခေါင်းစဉ်မသတ်မှတ်ရသေး"
                performer = audio.performer or "အဆိုတော်မသတ်မှတ်ရသေး"
                file_id = audio.file_id
                
                logger.info(f"🎵 Audio: {title} - {performer}")
                
                title_uni = zg2uni(title)
                performer_uni = zg2uni(performer)
                
                # Save to database
                from database import save_content, content_exists
                if not content_exists(""):
                    save_content(
                        category_id=1,
                        title=title_uni,
                        performer=performer_uni,
                        album="မြန်မာသီချင်းများ",
                        file_id=file_id,
                        file_type="audio",
                        youtube_url=""
                    )
                    logger.info(f"💾 Saved to database: {title_uni}")
                
                # Send player message
                await send_player_message(context, title_uni, performer_uni, file_id)
        
        async def send_player_message(context, title, performer, file_id):
            """Player Message ကို ချန်နယ်မှာ ပို့မယ်"""
            keyboard = [
                [
                    InlineKeyboardButton("▶️ နားဆင်ရန်", callback_data=f"play_{file_id}"),
                    InlineKeyboardButton("⬇️ ဒေါင်းလုဒ်", callback_data=f"download_{file_id}")
                ],
                [
                    InlineKeyboardButton("📋 အယ်လ်ဘမ်အားလုံး", callback_data="albums")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"🎵 **သီချင်းအသစ် ရောက်ရှိပါပြီ**\n\n"
                     f"📌 **ခေါင်းစဉ်:** {title}\n"
                     f"🎤 **အဆိုတော်:** {performer}\n\n"
                     f"⬇️ နားဆင်ရန် အောက်ပါခလုတ်ကို နှိပ်ပါ။",
                reply_markup=reply_markup
            )
            logger.info(f"✅ Player message sent: {title}")
        
        async def auto_search_task(context: ContextTypes.DEFAULT_TYPE):
            """အလိုအလျောက် ရှာဖွေပြီး သီချင်းအသစ်တွေကို တင်ပေးမယ်"""
            logger.info("🔍 Auto-search running...")
            try:
                results = await asyncio.to_thread(search_youtube_music)
                if not results:
                    logger.info("ℹ️ No new songs found")
                    return
                
                from database import content_exists, save_content
                new_count = 0
                for video in results:
                    if not content_exists(video['url']):
                        logger.info(f"🎵 New: {video['title']}")
                        # Download and send
                        audio_path, title, performer = await asyncio.to_thread(
                            download_audio_from_youtube, video['url'], DOWNLOAD_PATH
                        )
                        if audio_path:
                            with open(audio_path, 'rb') as f:
                                msg = await context.bot.send_audio(
                                    chat_id=CHANNEL_ID,
                                    audio=f,
                                    title=zg2uni(title or "ခေါင်းစဉ်မသတ်မှတ်ရသေး"),
                                    performer=zg2uni(performer or "အဆိုတော်မသတ်မှတ်ရသေး")
                                )
                            if msg.audio:
                                save_content(1, zg2uni(title), zg2uni(performer), "မြန်မာသီချင်းများ", 
                                           msg.audio.file_id, "audio", video['url'])
                                await send_player_message(context, zg2uni(title), zg2uni(performer), msg.audio.file_id)
                            cleanup_temp_files([audio_path])
                            new_count += 1
                            await asyncio.sleep(2)
                
                logger.info(f"✅ Added {new_count} new songs")
            except Exception as e:
                logger.error(f"❌ Auto-search error: {e}")
                traceback.print_exc()
        
        async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """/status Command"""
            user_id = update.effective_user.id
            if ADMIN_IDS and user_id not in ADMIN_IDS:
                await update.message.reply_text("⛔ သင်သည် Bot Admin မဟုတ်ပါ။")
                return
            
            stats = get_stats()
            await update.message.reply_text(
                f"🤖 **Bot Status**\n\n"
                f"📊 **Database Statistics**\n"
                f"• စုစုပေါင်း: {stats['total']}\n"
                f"• မြန်မာသီချင်း: {stats['music']}\n"
                f"• ဓမ္မတရား: {stats['dhamma']}\n"
                f"• အခြား: {stats['others']}\n\n"
                f"🔄 Auto-Search: {SEARCH_INTERVAL_MINUTES} min\n"
                f"⏰ Server Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        # ---- 9. Build Application ----
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Commands
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("search", search_command))
        application.add_handler(CommandHandler("status", status_command))
        
        # Callback
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Channel Post
        application.add_handler(MessageHandler(
            filters.AUDIO | filters.VIDEO | filters.Document.ALL,
            channel_post_handler
        ))
        
        # Auto-Search Job
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(
                auto_search_task,
                interval=SEARCH_INTERVAL_MINUTES * 60,
                first=10
            )
            logger.info(f"🔄 Auto-search scheduled every {SEARCH_INTERVAL_MINUTES} minutes")
        
        # ---- 10. Run Bot ----
        logger.info("✅ Bot is ready!")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
