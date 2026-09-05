#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Handlers for YouTube Music Bot
"""

import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import CHANNEL_ID, ADMIN_IDS
from database import get_stats, get_categories, get_all_contents, delete_content
from converter import zg2uni
from youtube_api import search_youtube_music

logger = logging.getLogger(__name__)

# ============ Helper Functions ============
def is_admin(user_id):
    """User က Admin ဟုတ်မဟုတ် စစ်ဆေးပါ"""
    if not ADMIN_IDS:
        return True  # ADMIN_IDS မထည့်ထားရင် အားလုံးကို Admin လို့ သတ်မှတ်
    return user_id in ADMIN_IDS

# ============ Public Commands ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start Command"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
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
        "/status - Bot အခြေအနေ ကြည့်မယ်\n"
        "/stats - အသေးစိတ်စာရင်းအင်း (Admin)\n"
        "/addcategory - Category အသစ်ထည့်ရန် (Admin)\n"
        "/addsong - သီချင်းအသစ်ထည့်ရန် (Admin)\n"
        "/deletesong - သီချင်းဖျက်ရန် (Admin)\n"
        "/broadcast - ကြော်ငြာစာပို့ရန် (Admin)"
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/search Command - YouTube မှာ သီချင်းအသစ်တွေကို ရှာဖွေမယ်"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ သင်သည် Bot Admin မဟုတ်ပါ။")
        return

    msg = await update.message.reply_text("🔍 YouTube မှာ မြန်မာသီချင်းအသစ်တွေကို ရှာဖွေနေပါပြီ...")

    try:
        results = await asyncio.to_thread(search_youtube_music)
        if not results:
            await msg.edit_text("❌ သီချင်းအသစ်မတွေ့ပါ။")
            return

        # Database ထဲ ရှိပြီးသား သီချင်းတွေကို စစ်ပါ
        from database import content_exists
        new_songs = []
        for video in results:
            if not content_exists(video['url']):
                new_songs.append(video)

        if not new_songs:
            await msg.edit_text("✅ သီချင်းအသစ်မရှိပါ။ အားလုံးက Database ထဲမှာ ရှိပြီးသားပါ။")
            return

        # ပထမဆုံး သီချင်း ၅ ပုဒ်ကိုပဲ ပြပါ
        song_list = "\n".join([f"• {s['title']} ({s['channel_name']})" for s in new_songs[:5]])
        await msg.edit_text(
            f"🎵 **သီချင်းအသစ်များ တွေ့ရှိပါပြီ**\n\n"
            f"{song_list}\n\n"
            f"📌 စုစုပေါင်း: {len(new_songs)} ပုဒ်\n"
            f"🔄 Auto-search က ပုံမှန်အလုပ်လုပ်နေပါပြီ။"
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        await msg.edit_text(f"❌ ရှာဖွေရာမှာ အဆင်မပြေပါ: {e}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/status Command"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ သင်သည် Bot Admin မဟုတ်ပါ။")
        return

    stats = get_stats()
    categories = get_categories()

    category_text = "\n".join([f"• {cat['name']}" for cat in categories]) if categories else "အမျိုးအစားမရှိသေးပါ"

    await update.message.reply_text(
        f"🤖 **Bot Status**\n\n"
        f"📊 **Database Statistics**\n"
        f"• စုစုပေါင်း: {stats['total']}\n"
        f"• မြန်မာသီချင်း: {stats['music']}\n"
        f"• ဓမ္မတရား: {stats['dhamma']}\n"
        f"• အခြား: {stats['others']}\n\n"
        f"📂 **Categories**\n"
        f"{category_text}\n\n"
        f"👤 **Admins**: {ADMIN_IDS}\n"
        f"📡 **Channel ID**: {CHANNEL_ID}"
    )

# ============ Admin Commands ============
async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Category အသစ်ထည့်ရန်"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ သင်သည် Admin မဟုတ်ပါ။")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "❗ **/addcategory [Category Name]**\n\n"
            "ဥပမာ: `/addcategory ရော့ခ်သီချင်းများ`"
        )
        return

    category_name = " ".join(args)

    try:
        from database import add_category as db_add_category
        result = db_add_category(category_name)

        if result:
            await update.message.reply_text(f"✅ Category `{category_name}` ကို အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။")
        else:
            await update.message.reply_text("❌ Category ထည့်သွင်းရာမှာ အဆင်မပြေပါ။ (ရှိပြီးသားလား စစ်ပါ)")
    except Exception as e:
        logger.error(f"Add category error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

async def add_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: သီချင်းအသစ်ထည့်ရန်"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ သင်သည် Admin မဟုတ်ပါ။")
        return

    args = context.args
    if len(args) < 4:
        await update.message.reply_text(
            "❗ **/addsong [Category_ID] [Title] [Performer] [File_ID]**\n\n"
            "ဥပမာ: `/addsong 1 ယန်းတိုင်းမှုငံ့ပါ့မယ် ဟော်မားနဝင်း CQACAg...`"
        )
        return

    try:
        category_id = int(args[0])
        title = zg2uni(" ".join(args[1:-1]))
        performer = zg2uni(args[-2])
        file_id = args[-1]

        from database import save_content
        result = save_content(
            category_id=category_id,
            title=title,
            performer=performer,
            album="မြန်မာသီချင်းများ",
            file_id=file_id,
            file_type="audio",
            youtube_url="",
            metadata=""
        )

        if result:
            await update.message.reply_text(
                f"✅ သီချင်းကို အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။\n"
                f"📌 **ခေါင်းစဉ်:** {title}\n"
                f"🎤 **အဆိုတော်:** {performer}"
            )
        else:
            await update.message.reply_text("❌ သီချင်းထည့်သွင်းရာမှာ အဆင်မပြေပါ။")
    except Exception as e:
        logger.error(f"Add song error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

async def delete_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: သီချင်းတစ်ပုဒ်ကို ဖျက်ရန်"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ သင်သည် Admin မဟုတ်ပါ။")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "❗ **/deletesong [Song_ID]**\n\n"
            "သီချင်း ID ကို /stats command မှာ ကြည့်ပါ။"
        )
        return

    song_id = args[0]

    try:
        # Delete from database
        result = delete_content(song_id)

        if result:
            await update.message.reply_text(f"✅ သီချင်း ID `{song_id}` ကို အောင်မြင်စွာ ဖျက်ပြီးပါပြီ။")
        else:
            await update.message.reply_text("❌ သီချင်းဖျက်ရာမှာ အဆင်မပြေပါ။ (ID မှားနေလား စစ်ပါ)")
    except Exception as e:
        logger.error(f"Delete song error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Channel ထဲမှာ ကြော်ငြာစာပို့ရန်"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ သင်သည် Admin မဟုတ်ပါ။")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "❗ **/broadcast [Message]**\n\n"
            "ဥပမာ: `/broadcast မင်္ဂလာပါ အားလုံး! သီချင်းအသစ်များ ရောက်ရှိပါပြီ။`"
        )
        return

    message = " ".join(args)

    try:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"📢 **ကြော်ငြာ**\n\n{message}"
        )
        await update.message.reply_text("✅ ကြော်ငြာစာကို အောင်မြင်စွာ ပို့ပြီးပါပြီ။")
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await update.message.reply_text(f"❌ ကြော်ငြာစာပို့ရာမှာ အဆင်မပြေပါ: {e}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: အသေးစိတ်စာရင်းအင်းကြည့်ရန်"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ သင်သည် Admin မဟုတ်ပါ။")
        return

    try:
        stats = get_stats()
        contents = get_all_contents(limit=20)

        content_list = "\n".join([
            f"• ID: `{c['id']}` - {c['title']} ({c['performer']})"
            for c in contents
        ]) if contents else "သီချင်းမရှိသေးပါ"

        await update.message.reply_text(
            f"📊 **Detailed Statistics**\n\n"
            f"📌 **Total**: {stats['total']}\n"
            f"🎵 **Music**: {stats['music']}\n"
            f"📿 **Dhamma**: {stats['dhamma']}\n"
            f"📚 **Others**: {stats['others']}\n\n"
            f"📋 **Recent Songs (Last 20)**:\n"
            f"{content_list}"
        )
    except Exception as e:
        logger.error(f"Stats error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Bot ကို ပြန်လည်စတင်ရန်"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ သင်သည် Admin မဟုတ်ပါ။")
        return

    await update.message.reply_text("🔄 Bot ကို ပြန်လည်စတင်နေပါပြီ...")

    import sys
    import os
    # Restart the bot
    os.execv(sys.executable, ['python'] + sys.argv)

# ============ Inline Keyboard Handlers ============
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline Keyboard ခလုတ်တွေကို ကိုင်တွယ်မယ်"""
    query = update.callback_query
    await query.answer()
    data = query.data

    try:
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
                text += "\n📌 သီချင်းတစ်ပုဒ်ကို ရွေးရန် /stats ကိုသုံးပါ။"
            else:
                text = "📋 **အယ်လ်ဘမ်များ**\n\nအယ်လ်ဘမ်မရှိသေးပါဘူး။"

            await query.edit_message_text(text)

        else:
            await query.edit_message_text("❌ မသိသော ခလုတ်ဖြစ်ပါသည်။")

    except Exception as e:
        logger.error(f"Button handler error: {e}")
        await query.edit_message_text(f"❌ Error: {e}")
