#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import asyncio
import logging
import traceback
import threading
from datetime import datetime

from flask import Flask

# ============ Logging Setup ============
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler('bot.log')]
)
logger = logging.getLogger(__name__)

# ============ Flask Web Server ============
app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ Bot is running!", 200

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ============ Main Bot Function ============
async def main():
    try:
        logger.info("🚀 Starting YouTube Music Bot...")
        
        # Start web server
        thread = threading.Thread(target=run_web_server, daemon=True)
        thread.start()
        logger.info(f"✅ Web server started on port {os.environ.get('PORT', 10000)}")
        
        # ---- Config ----
        from config import (
            BOT_TOKEN, YOUTUBE_API_KEY, CHANNEL_ID, ADMIN_IDS,
            MONGODB_URI, SEARCH_QUERY, MAX_RESULTS_PER_SEARCH,
            SEARCH_INTERVAL_MINUTES, DOWNLOAD_PATH, MAX_FILE_SIZE_MB, DATABASE_NAME
        )
        logger.info("✅ Config loaded")
        
        # ---- Database ----
        from database import init_db, test_connection, get_stats
        logger.info("📊 Initializing database...")
        init_db()
        if not test_connection():
            logger.error("❌ MongoDB connection failed!")
            sys.exit(1)
        logger.info("✅ Database connected")
        
        # ---- YouTube API ----
        from youtube_api import search_youtube_music
        logger.info("✅ YouTube API loaded")
        
        # ---- Converter ----
        from converter import (
            download_audio_from_youtube,
            get_file_size_mb,
            zg2uni,
            cleanup_temp_files
        )
        logger.info("✅ Converter loaded")
        
        # ---- Handlers ----
        from handlers import (
            start, search_command, status_command, stats_command,
            add_category, add_song, delete_song, broadcast,
            restart_command, button_handler
        )
        logger.info("✅ Handlers loaded")
        
        # ---- Telegram Imports ----
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import (
            Application, CommandHandler, MessageHandler,
            CallbackQueryHandler, filters
        )
        
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)
        logger.info(f"📁 Download path: {DOWNLOAD_PATH}")
        
        # ---- Channel Post Handler ----
        async def send_player_message(context, title, performer, file_id):
            keyboard = [
                [
                    InlineKeyboardButton("▶️ နားဆင်ရန်", callback_data=f"play_{file_id}"),
                    InlineKeyboardButton("⬇️ ဒေါင်းလုဒ်", callback_data=f"download_{file_id}")
                ],
                [InlineKeyboardButton("📋 အယ်လ်ဘမ်အားလုံး", callback_data="albums")]
            ]
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"🎵 **သီချင်းအသစ် ရောက်ရှိပါပြီ**\n\n📌 **ခေါင်းစဉ်:** {title}\n🎤 **အဆိုတော်:** {performer}\n\n⬇️ နားဆင်ရန် အောက်ပါခလုတ်ကို နှိပ်ပါ။",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            logger.info(f"✅ Player message sent: {title}")
        
        async def channel_post_handler(update: Update, context):
            post = update.channel_post
            if not post or not post.audio:
                return
            
            audio = post.audio
            title = zg2uni(audio.title or "ခေါင်းစဉ်မသတ်မှတ်ရသေး")
            performer = zg2uni(audio.performer or "အဆိုတော်မသတ်မှတ်ရသေး")
            file_id = audio.file_id
            
            from database import save_content
            save_content(1, title, performer, "မြန်မာသီချင်းများ", file_id, "audio", "")
            await send_player_message(context, title, performer, file_id)
        
        async def auto_search_task(context):
            logger.info("🔍 Auto-search running...")
            try:
                results = await asyncio.to_thread(search_youtube_music)
                if not results:
                    logger.info("ℹ️ No new songs")
                    return
                
                from database import content_exists, save_content
                new_count = 0
                
                for video in results:
                    if content_exists(video['url']):
                        continue
                    
                    logger.info(f"🎵 Processing: {video['title']}")
                    
                    try:
                        audio_path, title, performer = await asyncio.to_thread(
                            download_audio_from_youtube, video['url'], DOWNLOAD_PATH
                        )
                        
                        if not audio_path:
                            logger.error(f"❌ Download failed: {video['url']}")
                            continue
                        
                        file_size_mb = get_file_size_mb(audio_path)
                        logger.info(f"📊 File size: {file_size_mb:.2f}MB")
                        
                        if file_size_mb > MAX_FILE_SIZE_MB:
                            logger.warning(f"⚠️ File too large")
                            cleanup_temp_files([audio_path])
                            continue
                        
                        with open(audio_path, 'rb') as f:
                            msg = await context.bot.send_audio(
                                chat_id=CHANNEL_ID,
                                audio=f,
                                title=zg2uni(title or "ခေါင်းစဉ်မသတ်မှတ်ရသေး"),
                                performer=zg2uni(performer or "အဆိုတော်မသတ်မှတ်ရသေး")
                            )
                        
                        if msg and msg.audio:
                            save_content(1, zg2uni(title), zg2uni(performer), "မြန်မာသီချင်းများ",
                                       msg.audio.file_id, "audio", video['url'])
                            await send_player_message(context, zg2uni(title), zg2uni(performer), msg.audio.file_id)
                            new_count += 1
                            logger.info(f"✅ Posted: {title}")
                        else:
                            logger.error(f"❌ Failed to send audio")
                        
                        cleanup_temp_files([audio_path])
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing {video['title']}: {e}")
                        traceback.print_exc()
                        continue
                
                logger.info(f"✅ Added {new_count} new songs")
            except Exception as e:
                logger.error(f"❌ Auto-search error: {e}")
                traceback.print_exc()
        
        # ---- Build Application ----
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("search", search_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("addcategory", add_category))
        application.add_handler(CommandHandler("addsong", add_song))
        application.add_handler(CommandHandler("deletesong", delete_song))
        application.add_handler(CommandHandler("broadcast", broadcast))
        application.add_handler(CommandHandler("restart", restart_command))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.AUDIO, channel_post_handler))
        
        if application.job_queue:
            application.job_queue.run_repeating(
                auto_search_task,
                interval=SEARCH_INTERVAL_MINUTES * 60,
                first=10
            )
            logger.info(f"🔄 Auto-search scheduled every {SEARCH_INTERVAL_MINUTES} minutes")
        
        # ---- Run Bot ----
        logger.info("✅ Bot is ready!")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped")
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
