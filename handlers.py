import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from rabbit import Rabbit
from config import CHANNEL_ID, ADMIN_ID, DOWNLOAD_PATH, MAX_FILE_SIZE_MB, TEXTS
from database import save_content, content_exists, get_content_by_id, get_content_count
from youtube_api import search_youtube_music
from converter import download_audio_from_youtube, get_file_size_mb

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot ကို စတင်ခြင်း"""
    user_id = update.effective_user.id
    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text(TEXTS["only_admin"])
        return
    
    await update.message.reply_text(TEXTS["start"])

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """YouTube မှာ သီချင်းအသစ်တွေကို ရှာဖွေခြင်း"""
    user_id = update.effective_user.id
    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text(TEXTS["only_admin"])
        return
    
    await update.message.reply_text(TEXTS["searching"])
    
    results = await asyncio.to_thread(search_youtube_music)
    
    if not results:
        await update.message.reply_text(TEXTS["no_new_songs"])
        return
    
    found_new = False
    for video in results:
        if not content_exists(video['url']):
            found_new = True
            await process_new_video(video, context)
    
    if not found_new:
        await update.message.reply_text(TEXTS["no_new_songs_found"])
    else:
        await update.message.reply_text(TEXTS["new_songs_posted"])

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot အခြေအနေ ကြည့်ရှုခြင်း"""
    user_id = update.effective_user.id
    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text(TEXTS["only_admin"])
        return
    
    from config import SEARCH_INTERVAL_MINUTES, MAX_RESULTS_PER_SEARCH
    
    song_count = get_content_count()
    
    status_text = f"{TEXTS['status_title']}\n\n"
    status_text += f"📢 {TEXTS['status_channel']}: {CHANNEL_ID}\n"
    status_text += f"⏱️ {TEXTS['status_interval']}: {SEARCH_INTERVAL_MINUTES} မိနစ်\n"
    status_text += f"🎵 {TEXTS['status_songs']}: {song_count} ပုဒ်\n"
    status_text += f"🔍 တစ်ခါရှာလျှင် အများဆုံး: {MAX_RESULTS_PER_SEARCH} ပုဒ်"
    
    await update.message.reply_text(status_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """အကူအညီ"""
    help_text = (
        "📖 **အကူအညီ**\n\n"
        "📌 **အမိန့်များ:**\n"
        "/start - Bot ကို စတင်မည်\n"
        "/search - သီချင်းအသစ်များ ရှာဖွေမည်\n"
        "/status - Bot အခြေအနေ ကြည့်မည်\n"
        "/help - အကူအညီ\n\n"
        "❓ **အကြံပြုချက်**\n"
        "ဤ Bot သည် YouTube မှ မြန်မာသီချင်းအသစ်များကို အလိုအလျောက် ရှာဖွေပြီး\n"
        "သင့်ချန်နယ်သို့ တင်ပေးပါမည်။\n"
        "သီချင်းတစ်ပုဒ် ပေါ်လာပါက အောက်ပါခလုတ်များဖြင့် နားဆင်နိုင်ပါသည်။\n"
        "- ▶️ နားဆင်ရန်\n"
        "- ⬇️ ဒေါင်းလုဒ်\n"
        "- 📋 အယ်လ်ဘမ်အားလုံး"
    )
    await update.message.reply_text(help_text)

async def process_new_video(video, context):
    """Video အသစ်ကို ဒေါင်းလုဒ်လုပ်ပြီး ချန်နယ်မှာ တင်မယ်"""
    try:
        # ၁။ YouTube ကနေ Audio ဒေါင်းလုဒ်လုပ်မယ်
        audio_path, title, performer = await asyncio.to_thread(
            download_audio_from_youtube, video['url'], DOWNLOAD_PATH
        )
        
        if not audio_path:
            print(f"Download failed for {video['url']}")
            return
        
        # ၂။ ဖိုင်အရွယ်အစား စစ်ဆေးမယ်
        file_size_mb = get_file_size_mb(audio_path)
        if file_size_mb > MAX_FILE_SIZE_MB:
            os.remove(audio_path)
            print(f"File too large: {file_size_mb}MB")
            return
        
        # ၃။ ဇော်ဂျီကနေ ယူနီကုဒ်ပြောင်းမယ်
        title_uni = Rabbit.zg2uni(title) if title else TEXTS["new_song_title"]
        performer_uni = Rabbit.zg2uni(performer) if performer else TEXTS["new_song_performer"]
        
        # ၄။ Telegram ကို Audio ဖိုင် ပို့မယ်
        with open(audio_path, 'rb') as audio_file:
            message = await context.bot.send_audio(
                chat_id=CHANNEL_ID,
                audio=audio_file,
                title=title_uni,
                performer=performer_uni,
                caption=f"🎵 **{title_uni}**\n🎤 {performer_uni}"
            )
        
        # ၅။ Database ထဲ သိမ်းမယ်
        file_id = message.audio.file_id
        save_content(
            category_id=1,
            title=title_uni,
            performer=performer_uni,
            album="မြန်မာသီချင်းများ",
            file_id=file_id,
            file_type="audio",
            youtube_url=video['url']
        )
        
        # ၆။ Player Message ကို ချန်နယ်မှာ ပို့မယ်
        await send_player_message(context, title_uni, performer_uni, file_id)
        
        # ၇။ ခေတ္တဖိုင်ကို ရှင်းမယ်
        os.remove(audio_path)
        
    except Exception as e:
        print(f"Error processing video: {e}")

async def send_player_message(context, title, performer, file_id):
    """Inline Keyboard ပါတဲ့ Player Message ကို ချန်နယ်မှာ ပို့မယ်"""
    keyboard = [
        [
            InlineKeyboardButton(TEXTS["player_listen_btn"], callback_data=f"play_{file_id}"),
            InlineKeyboardButton(TEXTS["player_download_btn"], callback_data=f"download_{file_id}")
        ],
        [
            InlineKeyboardButton(TEXTS["player_albums_btn"], callback_data="albums")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=f"{TEXTS['player_title']}\n\n"
             f"{TEXTS['player_title_label']} {title}\n"
             f"{TEXTS['player_performer_label']} {performer}\n\n"
             f"⬇️ နားဆင်ရန် အောက်ပါခလုတ်ကို နှိပ်ပါ။",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline Keyboard ခလုတ်တွေကို ကိုင်တွယ်မယ်"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("play_"):
        file_id = data.replace("play_", "")
        await context.bot.send_audio(
            chat_id=update.effective_chat.id,
            audio=file_id,
            caption=TEXTS["playing"]
        )
    
    elif data.startswith("download_"):
        file_id = data.replace("download_", "")
        await context.bot.send_audio(
            chat_id=update.effective_chat.id,
            audio=file_id,
            caption=TEXTS["downloading"]
        )
    
    elif data == "albums":
        await query.edit_message_text(
            f"{TEXTS['player_albums_title']}\n\n"
            f"{TEXTS['player_albums_list']}"
        )
