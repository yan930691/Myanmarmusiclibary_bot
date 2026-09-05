import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import CHANNEL_ID, ADMIN_IDS
from database import get_stats
from converter import zg2uni

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ သင်သည် Bot Admin မဟုတ်ပါ။")
        return

    stats = get_stats()
    await update.message.reply_text(
        f"🤖 **YouTube Music Bot**\n\n"
        "ဒီ Bot က YouTube ကနေ မြန်မာသီချင်းတွေကို ရှာဖွေပြီး ချန်နယ်မှာ အလိုအလျောက် တင်ပေးမှာပါ။\n\n"
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

    await update.message.reply_text("🔍 YouTube မှာ မြန်မာသီချင်းအသစ်တွေကို ရှာဖွေနေပါပြီ...")
    await update.message.reply_text("✅ Auto-search က ပုံမှန်အလုပ်လုပ်နေပါပြီ။")

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
        await query.edit_message_text(
            "📋 **အယ်လ်ဘမ်များ**\n\n"
            "မြန်မာသီချင်းများ - သီချင်းအသစ်များ\n"
            "နောက်ထပ် အယ်လ်ဘမ်များ ထပ်တိုးနေပါပြီ။"
        )
