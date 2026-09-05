#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import logging
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import CHANNEL_ID, ADMIN_IDS
from database import get_stats, get_categories, save_content, content_exists, delete_content
from converter import zg2uni, download_audio_from_url, get_file_size_mb, cleanup_temp_files
from soundcloud_api import search_soundcloud_music, search_soundcloud_by_url

logger = logging.getLogger(__name__)

# ============ Public Commands ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ သင်သည် Bot Admin မဟုတ်ပါ။")
        return

    stats = get_stats()
    await update.message.reply_text(
        f"🤖 **SoundCloud Music Bot**\n\n"
        "ဒီ Bot က SoundCloud ကနေ သီချင်းတွေကို ရှာဖွေပြီး ချန်နယ်မှာ တင်ပေးမှာပါ။\n\n"
        f"📊 **စာရင်းအင်း**\n"
        f"• စုစုပေါင်း သီချင်း: {stats['total']}\n\n"
        "📌 **Commands:**\n"
        "/search - သီချင်းအသစ်တွေကို ရှာဖွေမယ်\n"
        "/status - Bot အခြေအနေ ကြည့်မယ်\n"
        "/menu - Menu ကိုဖွင့်မယ်\n"
        "/addalbum [Album_URL] - SoundCloud Album တစ်ခုလုံးကို ဒေါင်းလုဒ်လုပ်မယ် (Admin)"
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ သင်သည် Bot Admin မဟုတ်ပါ။")
        return

    msg = await update.message.reply_text("🔍 SoundCloud မှာ သီချင်းအသစ်တွေကို ရှာဖွေနေပါပြီ...")

    try:
        results = await asyncio.to_thread(search_soundcloud_music)
        if not results:
            await msg.edit_text("❌ သီချင်းအသစ်မတွေ့ပါ။")
            return

        new_songs = []
        for video in results:
            if not content_exists(video['url']):
                new_songs.append(video)

        if not new_songs:
            await msg.edit_text("✅ သီချင်းအသစ်မရှိပါ။")
            return

        song_list = "\n".join([f"• {s['title'][:50]}..." for s in new_songs[:5]])
        await msg.edit_text(
            f"🎵 **သီချင်းအသစ်များ တွေ့ရှိပါပြီ**\n\n"
            f"{song_list}\n\n"
            f"📌 စုစုပေါင်း: {len(new_songs)} ပုဒ်"
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        await msg.edit_text(f"❌ ရှာဖွေရာမှာ အဆင်မပြေပါ: {e}")

# ============ Menu Command ============

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu ကိုပြမယ်"""
    keyboard = [
        [InlineKeyboardButton("🔍 ရှာဖွေရန်", callback_data="menu_search")],
        [InlineKeyboardButton("📊 အခြေအနေ", callback_data="menu_status")],
        [InlineKeyboardButton("📂 သီချင်းများ", callback_data="menu_songs")],
        [InlineKeyboardButton("ℹ️ အကြောင်းအရာ", callback_data="menu_about")]
    ]
    if ADMIN_IDS and update.effective_user.id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="menu_admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📋 **Menu**\n\nအောက်ပါခလုတ်များမှ ရွေးချယ်ပါ။",
        reply_markup=reply_markup
    )

# ============ Admin Commands ============

async def add_album_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin: SoundCloud Album/Playlist တစ်ခုလုံးကို ဒေါင်းလုဒ်လုပ်မယ်
    50 MB ကျော်ရင် Chat Message ထဲ ပို့မယ်
    """
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ သင်သည် Admin မဟုတ်ပါ။")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "❗ **/addalbum [SoundCloud_Album_URL]**\n\n"
            "ဥပမာ: `/addalbum https://soundcloud.com/artist/sets/album-name`\n\n"
            "📌 50 MB ကျော်တဲ့ သီချင်းတွေကို Chat Message ထဲကို ပို့ပေးပါမယ်။"
        )
        return

    album_url = args[0]
    msg = await update.message.reply_text("📥 Album ကို စတင်ဒေါင်းလုဒ်လုပ်နေပါပြီ...")

    try:
        # Album ထဲက Track တွေကို ရယူပါ
        tracks = await get_album_tracks(album_url)
        
        if not tracks:
            await msg.edit_text("❌ Album ကို ရှာမတွေ့ပါ သို့မဟုတ် Track တွေ မရှိပါ။")
            return

        total_tracks = len(tracks)
        await msg.edit_text(f"📊 Album ထဲမှာ {total_tracks} ပုဒ်ရှိပါတယ်။ ဒေါင်းလုဒ်လုပ်နေပါပြီ...")

        success_count = 0
        failed_count = 0
        chat_sent_count = 0
        
        for index, track_info in enumerate(tracks, 1):
            try:
                # Progress update
                if index % 5 == 0 or index == total_tracks:
                    await msg.edit_text(f"📊 ဒေါင်းလုဒ်လုပ်နေပါပြီ... ({index}/{total_tracks})")
                
                # Track ကို ဒေါင်းလုဒ်လုပ်ပါ
                audio_path, title, performer = await asyncio.to_thread(
                    download_audio_from_url, track_info['url'], "downloads"
                )

                if not audio_path:
                    failed_count += 1
                    continue

                # ဖိုင်အရွယ်အစား စစ်ဆေးပါ
                file_size = get_file_size_mb(audio_path)
                
                if file_size > 50:
                    # 50 MB ကျော်ရင် Chat Message ထဲ ပို့ပါ
                    chat_sent_count += 1
                    with open(audio_path, 'rb') as f:
                        await context.bot.send_audio(
                            chat_id=update.effective_chat.id,
                            audio=f,
                            title=zg2uni(title or "ခေါင်းစဉ်မသတ်မှတ်ရသေး"),
                            performer=zg2uni(performer or "အဆိုတော်မသတ်မှတ်ရသေး"),
                            caption=f"📌 **{zg2uni(title)}** ({file_size:.1f}MB)\n🎤 {zg2uni(performer)}\n\n⚠️ ဖိုင်အရွယ်အစားကြီးလို့ Chat ထဲ ပို့ပေးပါတယ်။"
                        )
                    cleanup_temp_files([audio_path])
                    success_count += 1
                    continue

                # 50 MB အောက်ဆိုရင် ချန်နယ်မှာ တင်ပါ
                with open(audio_path, 'rb') as f:
                    sent_msg = await context.bot.send_audio(
                        chat_id=CHANNEL_ID,
                        audio=f,
                        title=zg2uni(title or "ခေါင်းစဉ်မသတ်မှတ်ရသေး"),
                        performer=zg2uni(performer or "အဆိုတော်မသတ်မှတ်ရသေး"),
                        caption=f"🎵 **{zg2uni(title)}**\n🎤 {zg2uni(performer)}"
                    )

                if sent_msg and sent_msg.audio:
                    # Database ထဲ သိမ်းပါ
                    save_content(
                        category_id=1,
                        title=zg2uni(title),
                        performer=zg2uni(performer),
                        album="SoundCloud သီချင်းများ",
                        file_id=sent_msg.audio.file_id,
                        file_type="audio",
                        youtube_url=track_info['url'],
                        metadata=""
                    )
                    success_count += 1
                
                cleanup_temp_files([audio_path])
                
                # Rate limit ကိုရှောင်ဖို့
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Track error: {e}")
                failed_count += 1
                continue

        # ပြီးဆုံးကြောင်း အကြောင်းကြားပါ
        result_msg = (
            f"✅ **Album ဒေါင်းလုဒ် ပြီးဆုံးပါပြီ**\n\n"
            f"📊 စုစုပေါင်း: {total_tracks} ပုဒ်\n"
            f"✅ အောင်မြင်သွားတဲ့သီချင်း: {success_count} ပုဒ်\n"
            f"❌ မအောင်မြင်တဲ့သီချင်း: {failed_count} ပုဒ်\n"
            f"💬 Chat ထဲ ပို့ထားတဲ့သီချင်း: {chat_sent_count} ပုဒ် (50MB ကျော်လို့)\n\n"
            f"📌 ချန်နယ်မှာ တင်ထားတဲ့သီချင်းတွေကို နားဆင်နိုင်ပါပြီ။"
        )
        await msg.edit_text(result_msg)

    except Exception as e:
        logger.error(f"Add album error: {e}")
        await msg.edit_text(f"❌ Album ဒေါင်းလုဒ်လုပ်ရာမှာ အဆင်မပြေပါ: {e}")

async def get_album_tracks(album_url):
    """SoundCloud Album ထဲက Track တွေကို ယူမယ်"""
    import subprocess
    import json
    
    cmd = [
        'yt-dlp',
        '--dump-json',
        '--no-playlist',
        '--flat-playlist',
        album_url
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False
        )
        
        if result.returncode != 0:
            logger.error(f"❌ Failed to get album tracks: {result.stderr[:200]}")
            return []
        
        tracks = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                url = data.get('url', '')
                if url and 'soundcloud' in url:
                    tracks.append({
                        'title': data.get('title', 'Unknown'),
                        'url': url,
                        'duration': data.get('duration', 0)
                    })
            except json.JSONDecodeError:
                continue
        
        return tracks
    except Exception as e:
        logger.error(f"Error getting album tracks: {e}")
        return []

async def add_song_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: SoundCloud URL ကနေ သီချင်းတစ်ပုဒ်ထည့်ရန်"""
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ သင်သည် Admin မဟုတ်ပါ။")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "❗ **/addsong [SoundCloud_URL]**\n\n"
            "ဥပမာ: `/addsong https://soundcloud.com/artist/track-name`"
        )
        return

    url = args[0]
    msg = await update.message.reply_text(f"📥 ဒေါင်းလုဒ်လုပ်နေပါပြီ...")

    try:
        info = await asyncio.to_thread(search_soundcloud_by_url, url)
        if not info:
            await msg.edit_text("❌ မှားယွင်းသော URL ဖြစ်ပါသည်။")
            return

        audio_path, title, performer = await asyncio.to_thread(
            download_audio_from_url, url, "downloads"
        )

        if not audio_path:
            await msg.edit_text("❌ ဒေါင်းလုဒ်မအောင်မြင်ပါ။")
            return

        file_size = get_file_size_mb(audio_path)
        if file_size > 50:
            # 50 MB ကျော်ရင် Chat ထဲ ပို့ပါ
            with open(audio_path, 'rb') as f:
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=f,
                    title=zg2uni(title or "ခေါင်းစဉ်မသတ်မှတ်ရသေး"),
                    performer=zg2uni(performer or "အဆိုတော်မသတ်မှတ်ရသေး"),
                    caption=f"📌 **{zg2uni(title)}** ({file_size:.1f}MB)\n🎤 {zg2uni(performer)}\n\n⚠️ ဖိုင်အရွယ်အစားကြီးလို့ Chat ထဲ ပို့ပေးပါတယ်။"
                )
            cleanup_temp_files([audio_path])
            await msg.edit_text(f"✅ **{zg2uni(title)}** ကို Chat ထဲ ပို့ပြီးပါပြီ။ ({file_size:.1f}MB)")
            return

        with open(audio_path, 'rb') as f:
            sent_msg = await context.bot.send_audio(
                chat_id=CHANNEL_ID,
                audio=f,
                title=zg2uni(title or "ခေါင်းစဉ်မသတ်မှတ်ရသေး"),
                performer=zg2uni(performer or "အဆိုတော်မသတ်မှတ်ရသေး"),
                caption=f"🎵 **{zg2uni(title)}**\n🎤 {zg2uni(performer)}"
            )

        if sent_msg and sent_msg.audio:
            save_content(
                category_id=1,
                title=zg2uni(title),
                performer=zg2uni(performer),
                album="SoundCloud သီချင်းများ",
                file_id=sent_msg.audio.file_id,
                file_type="audio",
                youtube_url=url,
                metadata=""
            )
            await msg.edit_text(f"✅ **သီချင်းထည့်သွင်းပြီးပါပြီ**\n\n📌 {zg2uni(title)}")
        
        cleanup_temp_files([audio_path])

    except Exception as e:
        logger.error(f"Add song error: {e}")
        await msg.edit_text(f"❌ အဆင်မပြေပါ: {e}")

async def delete_song_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: သီချင်းဖျက်ရန်"""
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ သင်သည် Admin မဟုတ်ပါ။")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "❗ **/deletesong [Song_ID]**\n\n"
            "သီချင်း ID ကို /status command မှာ ကြည့်ပါ။"
        )
        return

    song_id = args[0]
    result = delete_content(song_id)
    if result:
        await update.message.reply_text(f"✅ သီချင်း ID `{song_id}` ကို ဖျက်ပြီးပါပြီ။")
    else:
        await update.message.reply_text("❌ သီချင်းဖျက်ရာမှာ အဆင်မပြေပါ။")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: ကြော်ငြာစာပို့ရန်"""
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ သင်သည် Admin မဟုတ်ပါ။")
        return

    args = context.args
    if not args:
        await update.message.reply_text("❗ /broadcast [Message]")
        return

    message = " ".join(args)
    try:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"📢 **ကြော်ငြာ**\n\n{message}"
        )
        await update.message.reply_text("✅ ကြော်ငြာစာ ပို့ပြီးပါပြီ။")
    except Exception as e:
        await update.message.reply_text(f"❌ ပို့ရာမှာ အဆင်မပြေပါ: {e}")

# ============ Button Handler ============

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

    elif data == "menu_search":
        await query.edit_message_text("🔍 ရှာဖွေရန်\n\n/search command ကိုသုံးပါ။")

    elif data == "menu_status":
        stats = get_stats()
        await query.edit_message_text(
            f"📊 **အခြေအနေ**\n\n"
            f"• စုစုပေါင်း သီချင်း: {stats['total']}\n"
            f"• မြန်မာသီချင်း: {stats['music']}"
        )

    elif data == "menu_songs":
        await query.edit_message_text(
            "📂 **သီချင်းများ**\n\n"
            "သီချင်းများကို ကြည့်ရန် /search ကိုသုံးပါ။"
        )

    elif data == "menu_about":
        await query.edit_message_text(
            "ℹ️ **အကြောင်းအရာ**\n\n"
            "ဒီ Bot က SoundCloud ကနေ သီချင်းတွေကို ရယူပြီး ချန်နယ်မှာ တင်ပေးပါတယ်။"
        )

    elif data == "menu_admin" and update.effective_user.id in ADMIN_IDS:
        keyboard = [
            [InlineKeyboardButton("📂 Album တစ်ခုလုံးထည့်", callback_data="admin_add_album")],
            [InlineKeyboardButton("➕ သီချင်းတစ်ပုဒ်ထည့်", callback_data="admin_add_song")],
            [InlineKeyboardButton("➖ သီချင်းဖျက်", callback_data="admin_delete")],
            [InlineKeyboardButton("📢 ကြော်ငြာစာပို့", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔙 ပြန်သွား", callback_data="menu_back")]
        ]
        await query.edit_message_text(
            "⚙️ **Admin Panel**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "admin_add_album":
        await query.edit_message_text(
            "📂 **Album တစ်ခုလုံးထည့်ရန်**\n\n"
            "/addalbum [SoundCloud_Album_URL] ကိုသုံးပါ။\n\n"
            "ဥပမာ: `/addalbum https://soundcloud.com/artist/sets/album-name`\n\n"
            "📌 50 MB ကျော်တဲ့ သီချင်းတွေကို Chat ထဲ ပို့ပေးပါမယ်။"
        )

    elif data == "admin_add_song":
        await query.edit_message_text(
            "➕ **သီချင်းတစ်ပုဒ်ထည့်ရန်**\n\n"
            "/addsong [SoundCloud_URL] ကိုသုံးပါ။\n\n"
            "ဥပမာ: `/addsong https://soundcloud.com/artist/track-name`"
        )

    elif data == "admin_delete":
        await query.edit_message_text(
            "➖ **သီချင်းဖျက်ရန်**\n\n"
            "/deletesong [Song_ID] ကိုသုံးပါ။\n\n"
            "သီချင်း ID ကို /status command မှာ ကြည့်ပါ။"
        )

    elif data == "admin_broadcast":
        await query.edit_message_text(
            "📢 **ကြော်ငြာစာပို့ရန်**\n\n"
            "/broadcast [Message] ကိုသုံးပါ။\n\n"
            "ဥပမာ: `/broadcast မင်္ဂလာပါ အားလုံး!`"
        )

    elif data == "menu_back":
        keyboard = [
            [InlineKeyboardButton("🔍 ရှာဖွေရန်", callback_data="menu_search")],
            [InlineKeyboardButton("📊 အခြေအနေ", callback_data="menu_status")],
            [InlineKeyboardButton("📂 သီချင်းများ", callback_data="menu_songs")],
            [InlineKeyboardButton("ℹ️ အကြောင်းအရာ", callback_data="menu_about")]
        ]
        if update.effective_user.id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="menu_admin")])
        
        await query.edit_message_text(
            "📋 **Menu**\n\nအောက်ပါခလုတ်များမှ ရွေးချယ်ပါ။",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    else:
        await query.edit_message_text("❌ မသိသော ခလုတ်ဖြစ်ပါသည်။")
