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
import threading
from datetime import datetime

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

# ============ Flask Web Server ============
app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ Bot is running!", 200

@app.route('/ping')
def ping():
    return "pong", 200

@app.route('/status')
def status():
    return {"status": "healthy", "time": datetime.now().isoformat()}, 200

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
        from converter import (
            download_audio_from_youtube,
            get_file_size_mb,
            zg2uni,
            cleanup_temp_files
        )
        logger.info("✅ Converter loaded successfully!")
        
        # ---- 5. Handlers ----
        from handlers import (
            start,
            search_command,
            status_command,
            stats_command,
            add_category,
            add_song,
            delete_song,
            broadcast,
            restart_command,
            button_handler
        )
        logger.info("✅ Handlers loaded successfully!")
        
        # ---- 6. Telegram Imports ----
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import (
            Application,
            CommandHandler,
            MessageHandler,
            CallbackQueryHandler,
            filters
        )
        logger.info("✅ Telegram imports loaded successfully!")
        
        # ---- 7. Create Download Path ----
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)
        logger.info(f"📁 Download path: {DOWNLOAD_PATH}")
        
        # ============ Bot Handlers ============
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
            save_content(
                category_id=1,
                title=title_uni,
                performer=performer_uni,
                album="မြန်မာသီချင်းများ",
                file_id=file_id,
                file_type="audio",
                youtube_url="",
                metadata=""
            )
            logger.info(f"💾 Saved to database: {title_uni}")
            
            await send_player_message(context, title_uni, performer_uni, file_id)
        
        async def auto_search_task(context):
            """အလိုအလျောက် ရှာဖွေပြီး သီချင်းအသစ်တွေကို တင်ပေးမယ်"""
            logger.info("🔍 Auto-search task STARTED!")
            
            try:
                logger.info("🔍 Searching YouTube...")
                results = await asyncio.to_thread(search_youtube_music)
                logger.info(f"📊 Found {len(results)} results from YouTube")
                
                if not results:
                    logger.info("ℹ️ No new songs found")
                    return
                
                from database import content_exists, save_content
                new_count = 0
                failed_count = 0
                
                for index, video in enumerate(results):
                    # Check if already exists
                    if content_exists(video['url']):
                        logger.info(f"⏩ Already exists: {video['title']}")
                        continue
                    
                    logger.info(f"🎵 Processing [{index+1}/{len(results)}]: {video['title']}")
                    
                    try:
                        # Download audio
                        audio_path, title, performer = await asyncio.to_thread(
                            download_audio_from_youtube,
                            video['url'],
                            DOWNLOAD_PATH
                        )
                        
                        if not audio_path:
                            logger.error(f"❌ Download failed: {video['url']}")
                            failed_count += 1
                            continue
                        
                        # Check file size
                        file_size_mb = get_file_size_mb(audio_path)
                        logger.info(f"📊 File size: {file_size_mb:.2f}MB")
                        
                        if file_size_mb > MAX_FILE_SIZE_MB:
                            logger.warning(f"⚠️ File too large: {file_size_mb:.2f}MB")
                            cleanup_temp_files([audio_path])
                            failed_count += 1
                            continue
                        
                        # Send to Telegram
                        with open(audio_path, 'rb') as f:
                            msg = await context.bot.send_audio(
                                chat_id=CHANNEL_ID,
                                audio=f,
                                title=zg2uni(title or "ခေါင်းစဉ်မသတ်မှတ်ရသေး"),
                                performer=zg2uni(performer or "အဆိုတော်မသတ်မှတ်ရသေး"),
                                duration=180  # 3 minutes default
                            )
                        
                        if msg and msg.audio:
                            # Save to database
                            save_content(
                                category_id=1,
                                title=zg2uni(title),
                                performer=zg2uni(performer),
                                album="မြန်မာသီချင်းများ",
                                file_id=msg.audio.file_id,
                                file_type="audio",
                                youtube_url=video['url'],
                                metadata=""
                            )
                            # Send player message
                            await send_player_message(
                                context,
                                zg2uni(title),
                                zg2uni(performer),
                                msg.audio.file_id
                            )
                            new_count += 1
                            logger.info(f"✅ Posted: {title}")
                        else:
                            logger.error(f"❌ Failed to send audio")
                            failed_count += 1
                        
                        cleanup_temp_files([audio_path])
                        
                        # Wait between downloads
                        await asyncio.sleep(5)
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing {video['title']}: {e}")
                        traceback.print_exc()
                        failed_count += 1
                        continue
                    
                    # Progress update every 5 songs
                    if (index + 1) % 5 == 0:
                        logger.info(f"📊 Progress: {index + 1}/{len(results)} songs processed")
                
                logger.info(f"✅ Added {new_count} new songs, {failed_count} failed")
                
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
            
            # Check download path
            download_files = os.listdir(DOWNLOAD_PATH) if os.path.exists(DOWNLOAD_PATH) else []
            download_count = len([f for f in download_files if f.endswith('.mp3')])
            
            await update.message.reply_text(
                f"🤖 **Bot Status**\n\n"
                f"📊 **Database Statistics**\n"
                f"• စုစုပေါင်း: {stats['total']}\n"
                f"• မြန်မာသီချင်း: {stats['music']}\n"
                f"• ဓမ္မတရား: {stats['dhamma']}\n"
                f"• အခြား: {stats['others']}\n\n"
                f"📁 **Download Queue**\n"
                f"• ဒေါင်းလုဒ်လုပ်ထားသော MP3: {download_count}\n\n"
                f"🔄 **Auto-Search**\n"
                f"• Interval: {SEARCH_INTERVAL_MINUTES} min\n"
                f"• Query: {SEARCH_QUERY}\n\n"
                f"⏰ **Server Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        # ---- Build Application ----
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Public Commands
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("search", search_command))
        application.add_handler(CommandHandler("status", status_command))
        
        # Admin Commands
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("addcategory", add_category))
        application.add_handler(CommandHandler("addsong", add_song))
        application.add_handler(CommandHandler("deletesong", delete_song))
        application.add_handler(CommandHandler("broadcast", broadcast))
        application.add_handler(CommandHandler("restart", restart_command))
        
        # Callback Handler
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Channel Post Handler
        application.add_handler(MessageHandler(
            filters.AUDIO | filters.VIDEO | filters.Document.ALL,
            channel_post_handler
        ))
        
        # Auto-Search Job
        job_queue = application.job_queue
        if job_queue:
            logger.info("✅ JobQueue is available!")
            job_queue.run_repeating(
                auto_search_task,
                interval=SEARCH_INTERVAL_MINUTES * 60,
                first=10
            )
            logger.info(f"🔄 Auto-search scheduled every {SEARCH_INTERVAL_MINUTES} minutes")
        else:
            logger.error("❌ JobQueue is NOT available! Auto-search will not work.")
        
        # ---- Run Bot ----
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
