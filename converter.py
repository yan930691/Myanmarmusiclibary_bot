#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Converter Module - YouTube Download, MP4 to MP3, Zawgyi-Unicode Conversion
"""

import os
import re
import subprocess
import logging
import time
import imageio_ffmpeg

logger = logging.getLogger(__name__)

# ============ FFmpeg Path Setup ============
try:
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
    os.environ["IMAGEIO_FFMPEG_EXE"] = FFMPEG_PATH
    os.environ["FFMPEG_BINARY"] = FFMPEG_PATH
    logger.info(f"✅ FFmpeg found at: {FFMPEG_PATH}")
except Exception as e:
    logger.warning(f"⚠️ FFmpeg error: {e}")
    FFMPEG_PATH = "ffmpeg"

# ============ Zawgyi to Unicode ============
def zg2uni(text):
    """ဇော်ဂျီ ကနေ ယူနီကုဒ် ပြောင်းမယ်"""
    if not text or not isinstance(text, str):
        return text
    
    mapping = {
        '္': '်', 'ျ': 'ျ', 'ွ': 'ွ', 'ှ': 'ှ', 'ဿ': 'ဿ',
        '၍': 'ရ', '၌': 'နှ', 'ႏ': 'န်', '႐': 'ရ', '႑': 'ဒ',
        'ေက': 'ကေ', 'ေခ': 'ခေ', 'ေဂ': 'ဂေ', 'ေင': 'ငေ',
        'ေစ': 'စေ', 'ေဆ': 'ဆေ', 'ေဇ': 'ဇေ', 'ေဈ': 'ဈေ',
        'ေည': 'ညေ', 'ေဋ': 'ဋေ', 'ေဌ': 'ဌေ', 'ေဍ': 'ဍေ',
        'ေဎ': 'ဎေ', 'ေဏ': 'ဏေ', 'ေတ': 'တေ', 'ေထ': 'ထေ',
        'ေဒ': 'ဒေ', 'ေဓ': 'ဓေ', 'ေန': 'နေ', 'ေပ': 'ပေ',
        'ေဖ': 'ဖေ', 'ေဗ': 'ဗေ', 'ေဘ': 'ဘေ', 'ေမ': 'မေ',
        'ေယ': 'ယေ', 'ေရ': 'ရေ', 'ေလ': 'လေ', 'ေဝ': 'ဝေ',
        'ေသ': 'သေ', 'ေဟ': 'ဟေ', 'ေဠ': 'ဠေ', 'ေအ': 'အေ',
    }
    result = text
    for zg, uni in mapping.items():
        result = result.replace(zg, uni)
    return result

def clean_filename(filename):
    """ဖိုင်နာမည်ကို သန့်ရှင်းအောင်လုပ်မယ်"""
    if not filename:
        return "unknown"
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', ' ', filename).strip()
    if len(filename) > 200:
        filename = filename[:200]
    return filename or "unknown"

# ============ YouTube Download ============

def download_audio_from_youtube(youtube_url, output_path="downloads"):
    """
    YouTube ဗီဒီယိုကနေ MP3 ကို yt-dlp သုံးပြီး ဒေါင်းလုဒ်လုပ်မယ်
    ရလဒ်: (audio_file_path, title, performer)
    """
    if not output_path:
        output_path = "downloads"
    
    os.makedirs(output_path, exist_ok=True)
    
    # ffmpeg အလုပ်လုပ်လား စမ်းသပ်ပါ
    try:
        subprocess.run([FFMPEG_PATH, '-version'], capture_output=True, check=True)
        logger.info("✅ FFmpeg is working")
    except Exception as e:
        logger.error(f"❌ FFmpeg not working: {e}")
        return None, None, None
    
    # Visitor Data (YouTube ကို ခွင့်ပြုချက်ရအောင်)
    visitor_data = "CgtwUlZzV25LUmllOCiQvuG7BjIHCgVnZW5lcg%3D%3D"
    
    # yt-dlp အတွက် Command (အကောင်းဆုံး Options များ)
    cmd = [
        'yt-dlp',
        '--ffmpeg-location', FFMPEG_PATH,
        '--extractor-args', f'youtube:visitor_data={visitor_data}',
        '--extractor-args', 'youtube:player_client=android',
        '--extractor-args', 'youtube:player_client=web',
        '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        '--extract-audio',
        '--audio-format', 'mp3',
        '--audio-quality', '5',
        '--audio-bitrate', '64k',
        '--add-metadata',
        '--no-playlist',
        '--output', os.path.join(output_path, '%(title)s.%(ext)s'),
        youtube_url
    ]
    
    logger.info(f"📥 Downloading: {youtube_url}")
    logger.info(f"🔧 Using ffmpeg: {FFMPEG_PATH}")
    
    # Rate limit ကိုရှောင်ဖို့ ၃ စက္ကန့် အနားယူပါ
    time.sleep(3)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            check=False
        )
        
        if result.returncode != 0:
            logger.error(f"❌ Download failed: {result.stderr[:500]}")
            return None, None, None
        
        # ဒေါင်းလုဒ်လုပ်ထားတဲ့ ဖိုင်ကို ရှာပါ
        for file in os.listdir(output_path):
            if file.endswith('.mp3'):
                file_path = os.path.join(output_path, file)
                title = os.path.splitext(file)[0]
                title = clean_filename(title)
                logger.info(f"✅ Downloaded: {file_path}")
                return file_path, title, "Unknown"
        
        logger.error(f"❌ No MP3 file found")
        return None, None, None
        
    except subprocess.TimeoutExpired:
        logger.error(f"❌ Timeout")
        return None, None, None
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return None, None, None

def download_audio_from_youtube_with_info(youtube_url, output_path=None):
    """
    YouTube ဗီဒီယိုကနေ MP3 ကို ဒေါင်းလုဒ်လုပ်ပြီး
    သီချင်းအချက်အလက်တွေကိုပါ ပြန်ပေးမယ်
    """
    if not output_path:
        output_path = "downloads"
    
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
    """
    if not output_path:
        output_path = "downloads"
    
    os.makedirs(output_path, exist_ok=True)
    
    try:
        from moviepy.editor import VideoFileClip
        video = VideoFileClip(video_path)
        if video.audio is None:
            logger.warning(f"⚠️ No audio track in: {video_path}")
            return None, "No audio track found"
        
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_file = os.path.join(output_path, f"{base_name}.mp3")
        
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

def ensure_download_directory():
    """Download ဖိုင်တွဲ ရှိမရှိ စစ်ဆေးပြီး မရှိရင် ဖန်တီးမယ်"""
    os.makedirs("downloads", exist_ok=True)
    return "downloads"

def get_ffmpeg_version():
    """ffmpeg ဗားရှင်းကို ယူမယ်"""
    try:
        result = subprocess.run(
            [FFMPEG_PATH, '-version'],
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

def test_ffmpeg():
    """ffmpeg အလုပ်လုပ်လား စမ်းသပ်မယ်"""
    try:
        result = subprocess.run(
            [FFMPEG_PATH, '-version'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False
