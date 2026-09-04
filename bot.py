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

# Telegram Library
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ============ Logging Setup ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# ============ Import Config & Modules ============
try:
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
    
    from database import (
        init_db,
        save_content,
        content_exists,
        get_content_by_id,
        get_content_by_file_id,
        get_all_contents,
        search_contents,
        get_stats,
        get_categories,
        delete_content,
        client as mongo_client,
        db as mongo_db
    )
    logger.info("✅ Database module loaded successfully!")
    
    from youtube_api import search_youtube_music, extract_video_id
    logger.info("✅ YouTube API module loaded successfully!")
    
    from converter import (
        download_audio_from_youtube,
        convert_mp4_to_mp3,
        get_file_size_mb,
        zg2uni,
        cleanup_temp_files
    )
    logger.info("✅ Converter module loaded successfully!")
    
    from handlers import start, search_command, button_handler
    logger.info("✅ Handlers loaded successfully!")
    
except Exception as e:
    logger.error(f"❌ Import error: {e}")
    traceback.print_exc()
    sys.exit(1)

# ============ MongoDB Connection Test ============
def test_mongodb_connection():
    """MongoDB ချိတ်ဆက်မှုကို စမ်းသပ်မယ်"""
    try:
        # Ping command ကို သုံးပြီး ချိတ်ဆက်မှု စစ်ဆေးပါ
        mongo_client.admin.command('ping')
        logger.info("✅ MongoDB connection successful!")
        
        # Database ကို စစ်ဆေးပါ
        collections = mongo_db.list_collection_names()
        logger.info(f"📊 Collections in database: {collections}")
        return True
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        return False

# ============ Channel Post Handler ============
async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ချန်နယ်မှာ ဖိုင်အသစ်တင်ရင် အလုပ်လုပ်မယ်
    """
    post = update.channel_post
    if not post:
        return
    
    logger.info(f"📩 New channel post received: {post.message_id}")
    
    # Audio ဖိုင်အတွက်
    if post.audio:
        audio = post.audio
        title = audio.title or "ခေါင်းစဉ်မသတ်မှတ်ရသေး"
        performer = audio.performer or "အဆိုတော်မသတ်မှတ်ရသေး"
        file_id = audio.file_id
        file_name = audio.file_name or f"{title}.mp3"
        
        logger.info(f"🎵 Audio detected: {title} - {performer}")
        
        # ဇော်ဂျီကနေ ယူနီကုဒ်ပြောင်းမယ်
        title_uni = zg2uni(title)
        performer_uni = zg2uni(performer)
        
        # Database ထဲ သိမ်းပြီးပြီလား စစ်ပါ
        existing = get_content_by_file_id(file_id)
        if existing:
            logger.info(f"⏩ Content already exists in database: {title_uni}")
            return
        
        # Database ထဲ သိမ်းမယ်
        try:
            content_id = save_content(
                category_id=1,
                title=title_uni,
                performer=performer_uni,
                album="မြန်မာသီချင်းများ",
                file_id=file_id,
                file_type="audio",
                youtube_url="",
                metadata=""
            )
            logger.info(f"💾 Content saved to database: {content_id}")
        except Exception as e:
            logger.error(f"❌ Failed to save to database: {e}")
            return
        
        # Player Message ပို့မယ်
        try:
            await send_player_message(context, title_uni, performer_uni, file_id)
            logger.info(f"✅ Player message sent for: {title_uni}")
        except Exception as e:
            logger.error(f"❌ Failed to send player message: {e}")
    
    # Video ဖိုင်အတွက် (MP4 to MP3)
    elif post.video:
        video = post.video
        title = post.caption or "ဗီဒီယိုဖိုင်"
        file_id = video.file_id
        
        logger.info(f"🎬 Video detected: {title}")
        
        # Video ကို Download လုပ်ပြီး MP3 ပြောင်းမယ်
        # Note: ဒီအပိုင်းက နောက်ထပ် ရေးဖို့ လိုပါတယ်
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text="🎬 **ဗီဒီယိုဖိုင် တွေ့ရှိပါပြီ**\n\n"
                 "MP3 အဖြစ် ပြောင်းလဲခြင်းကို လက်ရှိ ပံ့ပိုးမထားသေးပါဘူး။"
        )
        logger.warning("⚠️ Video to MP3 conversion not implemented yet")

# ============ Send Player Message ============
async def send_player_message(context: ContextTypes.DEFAULT_TYPE, title: str, performer: str, file_id: str):
    """
    Inline Keyboard ပါတဲ့ Player Message ကို ချန်နယ်မှာ ပို့မယ်
    """
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
    
    message_text = (
        f"🎵 **သီချင်းအသစ် ရောက်ရှိပါပြီ**\n\n"
        f"📌 **ခေါင်းစဉ်:** {title}\n"
        f"🎤 **အဆိုတော်:** {performer}\n\n"
        f"⬇️ နားဆင်ရန် အောက်ပါခလုတ်ကို နှိပ်ပါ။"
    )
    
    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=message_text,
        reply_markup=reply_markup
    )

# ============ Auto Search Task ============
async def auto_search_task(context: ContextTypes.DEFAULT_TYPE):
    """
    အလိုအလျောက် ရှာဖွေပြီး သီချင်းအသစ်တွေကို တင်ပေးမယ်
    """
    logger.info("🔍 Auto-search task started...")
    
    try:
        # YouTube မှာ ရှာဖွေပါ
        results = await asyncio.to_thread(search_youtube_music)
        
        if not results:
            logger.info("ℹ️ No new songs found from YouTube")
            return
        
        logger.info(f"📊 Found {len(results)} results from YouTube")
        
        new_songs_count = 0
        for video in results:
            # Database ထဲ ရှိပြီးသားလား စစ်ပါ
            if not content_exists(video['url']):
                logger.info(f"🎵 New song found: {video['title']}")
                await process_new_video(video, context)
                new_songs_count += 1
                await asyncio.sleep(2)  # Rate limit အတွက်
        
        if new_songs_count > 0:
            logger.info(f"✅ {new_songs_count} new songs processed and posted!")
        else:
            logger.info("ℹ️ No new songs found in database")
            
    except Exception as e:
        logger.error(f"❌ Auto-search task error: {e}")
        traceback.print_exc()

# ============ Process New Video ============
async def process_new_video(video: dict, context: ContextTypes.DEFAULT_TYPE):
    """
    Video အသစ်ကို ဒေါင်းလုဒ်လုပ်ပြီး ချန်နယ်မှာ တင်မယ်
    """
    try:
        logger.info(f"📥 Processing video: {video['title']}")
        
        # ၁။ YouTube ကနေ Audio ဒေါင်းလုဒ်လုပ်မယ်
        audio_path, title, performer = await asyncio.to_thread(
            download_audio_from_youtube, video['url'], DOWNLOAD_PATH
        )
        
        if not audio_path:
            logger.error(f"❌ Download failed for: {video['url']}")
            return
        
        logger.info(f"✅ Audio downloaded: {audio_path}")
        
        # ၂။ ဖိုင်အရွယ်အစား စစ်ဆေးမယ်
        file_size_mb = get_file_size_mb(audio_path)
        if file_size_mb > MAX_FILE_SIZE_MB:
            logger.warning(f"⚠️ File too large: {file_size_mb:.2f}MB (max {MAX_FILE_SIZE_MB}MB)")
            cleanup_temp_files([audio_path])
            return
        
        # ၃။ ဇော်ဂျီကနေ ယူနီကုဒ်ပြောင်းမယ်
        title_uni = zg2uni(title) if title else "ခေါင်းစဉ်မသတ်မှတ်ရသေး"
        performer_uni = zg2uni(performer) if performer else "အဆိုတော်မသတ်မှတ်ရသေး"
        
        # ၄။ Telegram ကို Audio ဖိုင် ပို့မယ်
        with open(audio_path, 'rb') as audio_file:
            message = await context.bot.send_audio(
                chat_id=CHANNEL_ID,
                audio=audio_file,
                title=title_uni,
                performer=performer_uni,
                caption=f"🎵 **{title_uni}**\n🎤 {performer_uni}"
            )
        
        logger.info(f"📤 Audio sent to channel: {title_uni}")
        
        # ၅။ Database ထဲ သိမ်းမယ်
        if message.audio:
            file_id = message.audio.file_id
            content_id = save_content(
                category_id=1,
                title=title_uni,
                performer=performer_uni,
                album="မြန်မာသီချင်းများ",
                file_id=file_id,
                file_type="audio",
                youtube_url=video['url']
            )
            logger.info(f"💾 Content saved to database: {content_id}")
        
        # ၆။ Player Message ကို ချန်နယ်မှာ ပို့မယ်
        await send_player_message(context, title_uni, performer_uni, file_id)
        
        # ၇။ ခေတ္တဖိုင်ကို ရှင်းမယ်
        cleanup_temp_files([audio_path])
        logger.info(f"🗑️ Temporary file cleaned up: {audio_path}")
        
    except Exception as e:
        logger.error(f"❌ Error processing video: {e}")
        traceback.print_exc()

# ============ Status Command ============
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/status Command - Bot အခြေအနေ ကြည့်မယ်"""
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ သင်သည် Bot Admin မဟုတ်ပါ။")
        return
    
    # Database စာရင်းအင်း
    stats = get_stats()
    
    # MongoDB ချိတ်ဆက်မှု အခြေအနေ
    db_status = "✅ Connected" if mongo_client is not None else "❌ Disconnected"
    
    # Bot အချက်အလက်
    status_text = (
        f"🤖 **Bot Status**\n\n"
        f"📊 **Database Statistics**\n"
        f"• စုစုပေါင်း သီချင်း: {stats['total']}\n"
        f"• မြန်မာသီချင်း: {stats['music']}\n"
        f"• ဓမ္မတရား: {stats['dhamma']}\n"
        f"• အခြား: {stats['others']}\n\n"
        f"🔗 **MongoDB**: {db_status}\n"
        f"🔄 **Auto-Search**: {SEARCH_INTERVAL_MINUTES} minutes\n"
        f"📡 **Channel ID**: {CHANNEL_ID}\n"
        f"👤 **Admin IDs**: {ADMIN_IDS}\n\n"
        f"⏰ **Server Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    await update.message.reply_text(status_text)

# ============ Main Function ============
def main():
    """Bot ကို စတင်မယ်"""
    logger.info("🚀 Starting YouTube Music Bot...")
    
    # ၁။ Database ကို စတင်ဆောက်လုပ်ပါ
    logger.info("📊 Initializing database...")
    init_db()
    
    # ၂။ MongoDB ချိတ်ဆက်မှု စမ်းသပ်ပါ
    if not test_mongodb_connection():
        logger.error("❌ MongoDB connection failed! Bot will exit.")
        sys.exit(1)
    
    # ၃။ ခေတ္တဖိုင်တွဲ ဖန်တီးပါ
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    logger.info(f"📁 Download path created: {DOWNLOAD_PATH}")
    
    # ၄။ Application ကို စတင်ပါ
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ၅။ Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # ၆။ Callback Query Handler (Inline Keyboard)
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # ၇။ Channel Post Handler (Audio, Video, Document)
    application.add_handler(MessageHandler(
        filters.AUDIO | filters.VIDEO | filters.Document.ALL,
        channel_post_handler
    ))
    
    # ၈။ Auto-Search Job Queue
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(
            auto_search_task,
            interval=SEARCH_INTERVAL_MINUTES * 60,  # စက္ကန့်ပုံစံ
            first=10  # Bot စဖွင့်တာ ၁၀ စက္ကန့်အကြာမှ စမယ်
        )
        logger.info(f"🔄 Auto-search scheduled every {SEARCH_INTERVAL_MINUTES} minutes")
    else:
        logger.warning("⚠️ JobQueue is not available! Auto-search will not work.")
    
    # ၉။ Bot ကို Run ပါ
    logger.info("✅ Bot is ready and running!")
    logger.info(f"📡 Bot username: @{application.bot.username}" if hasattr(application.bot, 'username') else "📡 Bot is running")
    
    try:
        # Webhook မပါဘဲ Polling နည်းလမ်းနဲ့ Run ပါ
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        traceback.print_exc()
        sys.exit(1)

# ============ Entry Point ============
if __name__ == "__main__":
    main()
