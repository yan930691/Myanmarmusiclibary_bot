#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import asyncio
import logging
import traceback
import threading
from datetime import datetime

# Flask for health check / port binding
from flask import Flask

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

# ============ Flask Web Server (to satisfy Render port requirement) ============
app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ Bot is running!", 200

@app.route('/ping')
def ping():
    return "pong", 200

def run_web_server():
    """Run a simple web server for Render health checks"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ============ Main Bot Function ============
async def main():
    try:
        logger.info("🚀 Starting YouTube Music Bot...")
        
        # Start web server in background thread
        thread = threading.Thread(target=run_web_server, daemon=True)
        thread.start()
        logger.info(f"✅ Web server started on port {os.environ.get('PORT', 10000)}")
        
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
        from database import init_db, test_connection, get_stats
        logger.info("📊 Initializing database...")
        init_db()
        
        if not test_connection():
            logger.error("❌ MongoDB connection failed!")
            sys.exit(1)
        logger.info("✅ Database connected successfully!")
        
        # ---- 3. YouTube API ----
        from youtube_api import search_youtube_music
        logger.info("✅ YouTube API loaded successfully!")
        
        # ---- 4. Converter ----
        from converter import download_audio_from_youtube, get_file_size_mb, zg2uni, cleanup_temp_files
        logger.info("✅ Converter loaded successfully!")
        
        # ---- 5. Handlers ----
        from handlers import start, search_command, button_handler
        logger.info("✅ Handlers loaded successfully!")
        
        # ---- 6. Telegram Imports ----
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
        
        # ---- 7. Create Download Path ----
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)
        logger.info(f"📁 Download path: {DOWNLOAD_PATH}")
        
        # ============ Bot Handlers ============
        async def channel_post_handler(update: Update, context):
            """ချန်နယ်မှာ ဖိုင်အသစ်တင်ရင် အလုပ်လုပ်မယ်"""
            post = update.channel_post
            if not post or not post.audio:
                return
            
            audio = post.audio
            title = audio.title or "ခေါင်းစဉ်မသတ်မှတ်ရသေး"
            performer = audio.performer or "အဆိုတော်မသတ်မှတ်ရသေး"
            file_id = audio.file_id
            
            logger.info(f"🎵 Audio: {title} - {performer}")
            
            title_uni = zg2uni(title)
            performer_uni = zg2uni(performer)
            
            from database import save_content
            save_content(1, title_uni, performer_uni, "မြန်မာသီချင်းများ", file_id, "audio", "")
            
            await send_player_message(context, title_uni, performer_uni, file_id)
        
        async def send_player_message(context, title, performer, file_id):
            """Player Message ကို ချန်နယ်မှာ ပို့မယ်"""
            keyboard = [
                [
                    InlineKeyboardButton("▶️ နားဆင်ရန်", callback_data=f"play_{file_id}"),
                    InlineKeyboardButton("⬇️ ဒေါင်းလုဒ်", callback_data=f"download_{file_id}")
                ],
                [InlineKeyboardButton("📋 အယ်လ်ဘမ်အားလုံး", callback_data="albums")]
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
        
        async def auto_search_task(context):
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
        
        async def status_command(update: Update, context):
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
        
        # ============ Build Application ============
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("search", search_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.AUDIO, channel_post_handler))
        
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(auto_search_task, interval=SEARCH_INTERVAL_MINUTES * 60, first=10)
            logger.info(f"🔄 Auto-search scheduled every {SEARCH_INTERVAL_MINUTES} minutes")
        
        # ============ Run Bot ============
        logger.info("✅ Bot is ready!")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user")
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)

# ============ Entry Point ============
if __name__ == "__main__":
    asyncio.run(main())
