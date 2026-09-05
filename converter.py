#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Converter Module - YouTube Download, MP4 to MP3, Zawgyi-Unicode Conversion
"""

import os
import re
import subprocess
import tempfile
import logging
from pathlib import Path

import imageio_ffmpeg
from moviepy.editor import VideoFileClip

from config import DOWNLOAD_PATH, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)

# ============ FFmpeg Path Setup ============
# Render မှာ ffmpeg ကို ရှာတွေ့အောင် သတ်မှတ်ပါ
os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()

# ============ Zawgyi to Unicode Converter ============
# ဇော်ဂျီနဲ့ ယူနီကုဒ် ကွာခြားတဲ့ စာလုံးတွေကို Mapping
ZAWGYI_TO_UNICODE_MAP = {
    # ဗျည်းများ
    'က္': 'က္', 'ဂ္': 'ဂ္', 'င္': 'င္', 'စ္': 'စ္', 'ဇ္': 'ဇ္',
    'ည္': 'ည္', 'ဋ္': 'ဋ္', 'ဌ္': 'ဌ္', 'ဍ္': 'ဍ္', 'ဏ္': 'ဏ္',
    'တ္': 'တ္', 'ထ္': 'ထ္', 'ဒ္': 'ဒ္', 'န္': 'န္', 'ပ္': 'ပ္',
    'ဗ္': 'ဗ္', 'ဘ္': 'ဘ္', 'မ္': 'မ္', 'ယ္': 'ယ္', 'ရ္': 'ရ္',
    'လ္': 'လ္', 'ဝ္': 'ဝ္', 'သ္': 'သ္', 'ဟ္': 'ဟ္', 'ဠ္': 'ဠ္',
    'အ': 'အ', 'ဣ': 'ဣ', 'ဤ': 'ဤ', 'ဥ': 'ဥ', 'ဦ': 'ဦ',
    'ဧ': 'ဧ', 'ဨ': 'ဨ', 'ဩ': 'ဩ', 'ဪ': 'ဪ',
    # သင်္ကေတများ
    '၏': '၏', '၊': '၊', '။': '။',
    '္': '်', 'ျ': 'ျ', 'ွ': 'ွ', 'ှ': 'ှ', 'ဿ': 'ဿ',
    '၍': 'ရ', '၌': 'နှ', 'ႏ': 'န်', '႐': 'ရ', '႑': 'ဒ',
}

# မြန်မာစာလုံးများအတွက် ပုံမှန်မဟုတ်တဲ့ ဇော်ဂျီပုံစံများ
ZAWGYI_SPECIAL_CASES = {
    'ေက': 'ကေ',
    'ေခ': 'ခေ',
    'ေဂ': 'ဂေ',
    'ေင': 'ငေ',
    'ေစ': 'စေ',
    'ေဆ': 'ဆေ',
    'ေဇ': 'ဇေ',
    'ေဈ': 'ဈေ',
    'ေည': 'ညေ',
    'ေဋ': 'ဋေ',
    'ေဌ': 'ဌေ',
    'ေဍ': 'ဍေ',
    'ေဎ': 'ဎေ',
    'ေဏ': 'ဏေ',
    'ေတ': 'တေ',
    'ေထ': 'ထေ',
    'ေဒ': 'ဒေ',
    'ေဓ': 'ဓေ',
    'ေန': 'နေ',
    'ေပ': 'ပေ',
    'ေဖ': 'ဖေ',
    'ေဗ': 'ဗေ',
    'ေဘ': 'ဘေ',
    'ေမ': 'မေ',
    'ေယ': 'ယေ',
    'ေရ': 'ရေ',
    'ေလ': 'လေ',
    'ေဝ': 'ဝေ',
    'ေသ': 'သေ',
    'ေဟ': 'ဟေ',
    'ေဠ': 'ဠေ',
    'ေအ': 'အေ',
}

def zg2uni(text):
    """
    ဇော်ဂျီ ကနေ ယူနီကုဒ် ပြောင်းမယ်
    """
    if not text or not isinstance(text, str):
        return text
    
    result = text
    
    # ပထမအဆင့်: ဇော်ဂျီပုံစံများကို ပြောင်းပါ
    for zg, uni in ZAWGYI_SPECIAL_CASES.items():
        result = result.replace(zg, uni)
    
    # ဒုတိယအဆင့်: ကျန်တဲ့ စာလုံးတွေကို ပြောင်းပါ
    for zg, uni in ZAWGYI_TO_UNICODE_MAP.items():
        result = result.replace(zg, uni)
    
    # နောက်ဆုံး သန့်စင်ခြင်း
    # ဥပမာ - "ေက" ကို "ကေ" လို့ ပြောင်းပြီးသား
    result = result.replace('ေက', 'ကေ')
    result = result.replace('ေခ', 'ခေ')
    
    return result

def is_zawgyi(text):
    """
    စာသားက ဇော်ဂျီဟုတ်မဟုတ် စစ်ဆေးမယ်
    """
    if not text:
        return False
    
    # ဇော်ဂျီမှာပါတဲ့ ထူးခြားတဲ့ စာလုံးတွေ
    zawgyi_patterns = ['္', 'ႏ', '႐', '၍', '၌', 'ေက', 'ေခ']
    
    for pattern in zawgyi_patterns:
        if pattern in text:
            return True
    
    # ယူနီကုဒ်မှာမပါတဲ့ ဇော်ဂျီစာလုံးတွေ
    zawgyi_chars = ['္', 'ႏ', '႐', '၍', '၌']
    for char in zawgyi_chars:
        if char in text:
            return True
    
    return False

def clean_filename(filename):
    """
    ဖိုင်နာမည်ကို သန့်ရှင်းအောင်လုပ်မယ်
    """
    # မလိုအပ်တဲ့ စာလုံးတွေကို ဖယ်ရှားပါ
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', ' ', filename).strip()
    
    # ရှည်လွန်းရင် ဖြတ်ပါ
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename

# ============ YouTube Download Functions ============

def download_audio_from_youtube(youtube_url, output_path=None):
    """
    YouTube ဗီဒီယိုကနေ MP3 ကို yt-dlp သုံးပြီး ဒေါင်းလုဒ်လုပ်မယ်
    ရလဒ်: (audio_file_path, title, performer)
    """
    if not output_path:
        output_path = DOWNLOAD_PATH
    
    # ဖိုင်တွဲ မရှိရင် ဖန်တီးပါ
    os.makedirs(output_path, exist_ok=True)
    
    # yt-dlp အတွက် Command
    cmd = [
        'yt-dlp',
        '--extract-audio',
        '--audio-format', 'mp3',
        '--audio-quality', '5',
        '--add-metadata',
        '--no-playlist',
        '--output', os.path.join(output_path, '%(title)s.%(ext)s'),
        youtube_url
    ]
    
    logger.info(f"📥 Downloading: {youtube_url}")
    
    try:
        # Run the download
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=300  # 5 minutes timeout
        )
        
        logger.info(f"✅ Download completed for: {youtube_url}")
        
        # ဒေါင်းလုဒ်လုပ်ထားတဲ့ ဖိုင်ကို ရှာမယ်
        for file in os.listdir(output_path):
            if file.endswith('.mp3'):
                file_path = os.path.join(output_path, file)
                title = os.path.splitext(file)[0]
                performer = "Unknown"
                
                # ဖိုင်နာမည်ကို သန့်ရှင်းအောင်လုပ်ပါ
                title = clean_filename(title)
                
                logger.info(f"📁 Downloaded file: {file_path}")
                return file_path, title, performer
        
        logger.error(f"❌ No MP3 file found for: {youtube_url}")
        return None, None, None
        
    except subprocess.TimeoutExpired:
        logger.error(f"❌ Download timeout for: {youtube_url}")
        return None, None, None
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Download error for {youtube_url}: {e.stderr}")
        return None, None, None
    except Exception as e:
        logger.error(f"❌ Unexpected download error: {e}")
        return None, None, None

def download_audio_from_youtube_with_info(youtube_url, output_path=None):
    """
    YouTube ဗီဒီယိုကနေ MP3 ကို ဒေါင်းလုဒ်လုပ်ပြီး
    သီချင်းအချက်အလက်တွေကိုပါ ပြန်ပေးမယ်
    ရလဒ်: (audio_file_path, title, performer, duration)
    """
    if not output_path:
        output_path = DOWNLOAD_PATH
    
    os.makedirs(output_path, exist_ok=True)
    
    # ပထမဆုံး Video Info ကို ယူပါ
    try:
        info_cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-playlist',
            youtube_url
        ]
        
        info_result = subprocess.run(
            info_cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        
        import json
        video_info = json.loads(info_result.stdout)
        
        title = video_info.get('title', 'Unknown')
        uploader = video_info.get('uploader', 'Unknown')
        duration = video_info.get('duration', 0)
        
        # ခေါင်းစဉ်ကို သန့်ရှင်းအောင်လုပ်ပါ
        title = clean_filename(title)
        
    except Exception as e:
        logger.warning(f"⚠️ Could not get video info: {e}")
        title = "Unknown"
        uploader = "Unknown"
        duration = 0
    
    # ဒေါင်းလုဒ်လုပ်ပါ
    audio_path, _, _ = download_audio_from_youtube(youtube_url, output_path)
    
    if audio_path:
        return audio_path, title, uploader, duration
    else:
        return None, None, None, None

def convert_mp4_to_mp3(video_path, output_path=None):
    """
    MP4 ဗီဒီယိုကို MP3 အသံအဖြစ် ပြောင်းမယ်
    ရလဒ်: (output_file_path, error_message)
    """
    if not output_path:
        output_path = DOWNLOAD_PATH
    
    os.makedirs(output_path, exist_ok=True)
    
    try:
        video = VideoFileClip(video_path)
        if video.audio is None:
            logger.warning(f"⚠️ No audio track in: {video_path}")
            return None, "No audio track found"
        
        # Output file name
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_file = os.path.join(output_path, f"{base_name}.mp3")
        
        # Convert to MP3
        video.audio.write_audiofile(
            output_file,
            codec='mp3',
            bitrate="192k",
            verbose=False,
            logger=None
        )
        video.close()
        
        logger.info(f"✅ Converted: {video_path} -> {output_file}")
        return output_file, None
        
    except Exception as e:
        logger.error(f"❌ Conversion error: {e}")
        return None, str(e)

def get_file_size_mb(file_path):
    """ဖိုင်ရဲ့ အရွယ်အစား (MB) ကို ယူမယ်"""
    if os.path.exists(file_path):
        try:
            size_bytes = os.path.getsize(file_path)
            return size_bytes / (1024 * 1024)
        except Exception:
            return 0
    return 0

def get_file_size_bytes(file_path):
    """ဖိုင်ရဲ့ အရွယ်အစား (Bytes) ကို ယူမယ်"""
    if os.path.exists(file_path):
        try:
            return os.path.getsize(file_path)
        except Exception:
            return 0
    return 0

def cleanup_temp_files(file_paths):
    """ခေတ္တဖိုင်တွေကို ရှင်းပစ်မယ်"""
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                logger.debug(f"🗑️ Cleaned up: {path}")
            except Exception as e:
                logger.warning(f"⚠️ Cleanup error for {path}: {e}")

def cleanup_directory(directory_path, pattern=None):
    """ဖိုင်တွဲထဲက ဖိုင်တွေကို ရှင်းပစ်မယ်"""
    if not os.path.exists(directory_path):
        return
    
    try:
        for file in os.listdir(directory_path):
            file_path = os.path.join(directory_path, file)
            if pattern and not re.search(pattern, file):
                continue
            if os.path.isfile(file_path):
                os.remove(file_path)
                logger.debug(f"🗑️ Cleaned up: {file_path}")
    except Exception as e:
        logger.warning(f"⚠️ Directory cleanup error: {e}")

def get_download_path():
    """Download ဖိုင်တွဲရဲ့ လမ်းကြောင်းကို ယူမယ်"""
    return DOWNLOAD_PATH

def ensure_download_directory():
    """Download ဖိုင်တွဲ ရှိမရှိ စစ်ဆေးပြီး မရှိရင် ဖန်တီးမယ်"""
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    return DOWNLOAD_PATH

def get_ffmpeg_version():
    """ffmpeg ဗားရှင်းကို ယူမယ်"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.split('\n')[0]
        else:
            return "Unknown"
    except Exception:
        return "Not found"
