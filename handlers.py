import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import CHANNEL_ID, ADMIN_IDS
from database import get_stats, get_categories
from converter import zg2uni

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ သင်သည် Bot Admin မဟုတ်ပါ။")
        return

    stats = get_stats()
    await update.message.reply_text(
        f"🤖 **SoundCloud Music Bot**\n\n"
        "ဒီ Bot က SoundCloud ကနေ သီချင်းတွေကို ရှာဖွေပြီး ချန်နယ်မှာ အလိုအလျောက် တင်ပေးမှာပါ။\n\n"
        f"📊 **စာရင်းအင်း**\n"
        f"• စုစုပေါင်း သီချင်း: {stats['total']}\n"
        f"• မြန်မာသီချင်း: {stats['music']}\n"
        f"• ဓမ္မတရား: {stats['dhamma']}\n"
        f"• အခြား: {stats['others']}\n\n"
        "📌 **Commands:**\n"
        "/search - သီချင်းအသစ်တွေကို ရှာဖွေမယ်\n"
        "/status - Bot အခြေအနေ ကြည့်မယ်"
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ သင်သည် Bot Admin မဟုတ်ပါ။")
        return

    msg = await update.message.reply_text("🔍 SoundCloud မှာ သီချင်းအသစ်တွေကို ရှာဖွေနေပါပြီ...")

    try:
        from youtube_api import search_youtube_music
        results = await asyncio.to_thread(search_youtube_music)
        
        if not results:
            await msg.edit_text("❌ သီချင်းအသစ်မတွေ့ပါ။")
            return

        from database import content_exists
        new_songs = []
        for video in results:
            if not content_exists(video['url']):
                new_songs.append(video)

        if not new_songs:
            await msg.edit_text("✅ သီချင်းအသစ်မရှိပါ။ အားလုံးက Database ထဲမှာ ရှိပြီးသားပါ။")
            return

        song_list = "\n".join([f"• {s['title'][:50]}... ({s['channel_name']})" for s in new_songs[:5]])
        await msg.edit_text(
            f"🎵 **သီချင်းအသစ်များ တွေ့ရှိပါပြီ**\n\n"
            f"{song_list}\n\n"
            f"📌 စုစုပေါင်း: {len(new_songs)} ပုဒ်\n"
            f"🔄 Auto-search က ပုံမှန်အလုပ်လုပ်နေပါပြီ။"
        )
    except Exception as e:
        await msg.edit_text(f"❌ ရှာဖွေရာမှာ အဆင်မပြေပါ: {e}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        f"🎵 **Source**: SoundCloud\n"
        f"🔄 **Auto-Search**: 60 min\n"
        f"⏰ **Server Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("play_"):
        file_id = data.replace("play_", "")
        await context.bot.send_audio(
            chat_id=update.effective_chat.id,
            audio=file_id,
            caption="▶️ **နားဆင်နေပါပြီ...**"
        )
    
    elif data.startswith("download_"):
        file_id = data.replace("download_", "")
        await context.bot.send_audio(
            chat_id=update.effective_chat.id,
            audio=file_id,
            caption="⬇️ **ဒေါင်းလုဒ်လုပ်နေပါပြီ...**"
        )
    
    elif data == "albums":
        categories = get_categories()
        if categories:
            text = "📋 **အယ်လ်ဘမ်များ**\n\n"
            for cat in categories:
                text += f"• {cat['name']}\n"
        else:
            text = "📋 **အယ်လ်ဘမ်များ**\n\nအယ်လ်ဘမ်မရှိသေးပါဘူး။"
        await query.edit_message_text(text)
