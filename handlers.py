import os
from config import ADMIN_IDS
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from rabbit import Rabbit
from config import CHANNEL_ID, ADMIN_ID, DOWNLOAD_PATH, MAX_FILE_SIZE_MB
from database import (
    save_content, content_exists_by_url, get_content_by_id, 
    get_content_by_file_id, get_all_contents, search_contents,
    get_contents_by_category, count_contents
)
from youtube_api import search_youtube_music, extract_video_id
from converter import download_audio_from_youtube, get_file_size_mb

# Admin ဟုတ်မဟုတ် စစ်ဆေးရန်
def is_admin(user_id):
    return ADMIN_ID is None or user_id == ADMIN_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start Command"""
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ သင်သည် Bot Admin မဟုတ်ပါ။")
        return
    
    total_songs = count_contents()
    
    await update.message.reply_text(
        "🤖 **YouTube Music Bot**\n\n"
        "ဒီ Bot က YouTube ကနေ မြန်မာသီချင်းတွေကို ရှာဖွေပြီး ချန်နယ်မှာ အလိုအလျောက် တင်ပေးမှာပါ။\n\n"
        f"📊 **စုစုပေါင်းသီချင်း:** {total_songs}\n\n"
        "📌 **Commands:**\n"
        "/search - သီချင်းအသစ်တွေကို ရှာဖွေမယ်\n"
        "/stats - စာရင်းအင်းကြည့်မယ်\n"
        "/latest - နောက်ဆုံးသီချင်း ၁၀ ပုဒ်ကြည့်မယ်"
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/search Command - YouTube မှာ သီချင်းအသစ်တွေကို ရှာဖွေမယ်"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ သင်သည် Bot Admin မဟုတ်ပါ။")
        return
    
    await update.message.reply_text("🔍 YouTube မှာ မြန်မာသီချင်းအသစ်တွေကို ရှာဖွေနေပါပြီ...")
    
    results = await asyncio.to_thread(search_youtube_music)
    
    if not results:
        await update.message.reply_text("❌ သီချင်းအသစ်မတွေ့ပါ။")
        return
    
    found_new = 0
    for video in results:
        if not content_exists_by_url(video['url']):
            found_new += 1
            await process_new_video(video, context)
            await asyncio.sleep(2)  # Rate limit အတွက်
    
    if found_new == 0:
        await update.message.reply_text("✅ သီချင်းအသစ်မရှိပါ။ အားလုံးက Database ထဲမှာ ရှိပြီးသားပါ။")
    else:
        await update.message.reply_text(f"✅ သီချင်းအသစ် {found_new} ပုဒ်ကို ချန်နယ်မှာ တင်ပြီးပါပြီ။")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stats Command - စာရင်းအင်းကြည့်မယ်"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ သင်သည် Bot Admin မဟုတ်ပါ။")
        return
    
    total = count_contents()
    await update.message.reply_text(
        f"📊 **စာရင်းအင်း**\n\n"
        f"📌 စုစုပေါင်းသီချင်း: {total}\n"
        f"🎵 အမျိုးအစား: Music\n"
        f"📁 ဒေတာဘေ့စ်: MongoDB"
    )

async def latest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/latest Command - နောက်ဆုံးသီချင်း ၁၀ ပုဒ်ကြည့်မယ်"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ သင်သည် Bot Admin မဟုတ်ပါ။")
        return
    
    contents = get_all_contents(limit=10)
    if not contents:
        await update.message.reply_text("❌ သီချင်းမရှိသေးပါ။")
        return
    
    message = "📋 **နောက်ဆုံးသီချင်း ၁၀ ပုဒ်**\n\n"
    for i, content in enumerate(contents, 1):
        title = content.get('title', 'ခေါင်းစဉ်မသတ်မှတ်ရသေး')
        performer = content.get('performer', 'အဆိုတော်မသတ်မှတ်ရသေး')
        message += f"{i}. {title} - {performer}\n"
    
    await update.message.reply_text(message)

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
        title_uni = Rabbit.zg2uni(title) if title else "ခေါင်းစဉ်မသတ်မှတ်ရသေး"
        performer_uni = Rabbit.zg2uni(performer) if performer else "အဆိုတော်မသတ်မှတ်ရသေး"
        
        # ၄။ Telegram ကို Audio ဖိုင် ပို့မယ်
        with open(audio_path, 'rb') as audio_file:
            message = await context.bot.send_audio(
                chat_id=CHANNEL_ID,
                audio=audio_file,
                title=title_uni,
                performer=performer_uni,
                caption=f"🎵 **{title_uni}**\n🎤 {performer_uni}"
            )
        
        # ၅။ Database ထဲ သိမ်းမယ် (MongoDB)
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
        
        if content_id:
            print(f"✅ Saved to MongoDB: {title_uni}")
        else:
            print(f"⚠️ Failed to save to MongoDB: {title_uni}")
        
        # ၆။ Player Message ကို ချန်နယ်မှာ ပို့မယ်
        await send_player_message(context, title_uni, performer_uni, file_id, content_id)
        
        # ၇။ ခေတ္တဖိုင်ကို ရှင်းမယ်
        os.remove(audio_path)
        
    except Exception as e:
        print(f"Error processing video: {e}")

async def send_player_message(context, title, performer, file_id, content_id=None):
    """Inline Keyboard ပါတဲ့ Player Message ကို ချန်နယ်မှာ ပို့မယ်"""
    keyboard = [
        [
            InlineKeyboardButton("▶️ နားဆင်ရန်", callback_data=f"play_{content_id if content_id else file_id}"),
            InlineKeyboardButton("⬇️ ဒေါင်းလုဒ်", callback_data=f"download_{content_id if content_id else file_id}")
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

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline Keyboard ခလုတ်တွေကို ကိုင်တွယ်မယ်"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("play_"):
        content_id = data.replace("play_", "")
        # content_id က ObjectId လား file_id လား စစ်ဆေးပါ
        content = get_content_by_id(content_id)
        if not content:
            # content_id က file_id ဖြစ်နိုင်တယ်
            content = get_content_by_file_id(content_id)
        
        if content:
            file_id = content.get('file_id')
            title = content.get('title', 'သီချင်း')
            await context.bot.send_audio(
                chat_id=update.effective_chat.id,
                audio=file_id,
                caption=f"▶️ {title}"
            )
        else:
            await query.edit_message_text("❌ သီချင်းကို ရှာမတွေ့ပါ။")
    
    elif data.startswith("download_"):
        content_id = data.replace("download_", "")
        content = get_content_by_id(content_id)
        if not content:
            content = get_content_by_file_id(content_id)
        
        if content:
            file_id = content.get('file_id')
            title = content.get('title', 'သီချင်း')
            await context.bot.send_audio(
                chat_id=update.effective_chat.id,
                audio=file_id,
                caption=f"⬇️ {title}"
            )
        else:
            await query.edit_message_text("❌ သီချင်းကို ရှာမတွေ့ပါ။")
    
    elif data == "albums":
        await query.edit_message_text(
            "📋 **အယ်လ်ဘမ်များ**\n\n"
            "🎵 မြန်မာသီချင်းများ\n"
            "📿 ဓမ္မစကားများ\n"
            "🎭 အသံဇာတ်လမ်းများ\n"
            "📚 အသံဝတ္ထုများ\n"
            "🎤 စာပေဟောပြောပွဲများ\n\n"
            "နောက်ထပ် အယ်လ်ဘမ်များ ထပ်တိုးနေပါပြီ။"
        )
    
