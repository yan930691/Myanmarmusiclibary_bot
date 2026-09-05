#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import re
import imageio_ffmpeg

logger = logging.getLogger(__name__)

# ffmpeg path
try:
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
    os.environ["IMAGEIO_FFMPEG_EXE"] = FFMPEG_PATH
    os.environ["FFMPEG_BINARY"] = FFMPEG_PATH
    logger.info(f"✅ FFmpeg: {FFMPEG_PATH}")
except Exception as e:
    logger.warning(f"⚠️ FFmpeg error: {e}")
    FFMPEG_PATH = "ffmpeg"

# ============ Zawgyi to Unicode ============
def zg2uni(text):
    if not text:
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
    if not filename:
        return "unknown"
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', ' ', filename).strip()
    return filename[:200] or "unknown"

# ============ YouTube Download ============

def download_audio_from_youtube(youtube_url, output_path="downloads"):
    """YouTube ကနေ MP3 ဒေါင်းလုဒ်လုပ်မယ်"""
    os.makedirs(output_path, exist_ok=True)
    
    # ffmpeg အလုပ်လုပ်လား စမ်းသပ်ပါ
    try:
        subprocess.run([FFMPEG_PATH, '-version'], capture_output=True, check=True)
        logger.info("✅ FFmpeg is working")
    except Exception as e:
        logger.error(f"❌ FFmpeg not working: {e}")
        return None, None, None
    
    # Visitor Data
    visitor_data = "CgtwUlZzV25LUmllOCiQvuG7BjIHCgVnZW5lcg%3D%3D"
    
    cmd = [
        'yt-dlp',
        '--ffmpeg-location', FFMPEG_PATH,
        '--extractor-args', f'youtube:visitor_data={visitor_data}',
        '--extractor-args', 'youtube:po_token=NONE',
        '--extract-audio',
        '--audio-format', 'mp3',
        '--audio-quality', '5',
        '--add-metadata',
        '--no-playlist',
        '--output', os.path.join(output_path, '%(title)s.%(ext)s'),
        youtube_url
    ]
    
    logger.info(f"📥 Downloading: {youtube_url}")
    logger.info(f"🔧 Using ffmpeg: {FFMPEG_PATH}")
    
    try:
        import time
        time.sleep(2)  # Rate limit ကိုရှောင်ဖို့
        
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

def get_file_size_mb(file_path):
    if os.path.exists(file_path):
        try:
            return os.path.getsize(file_path) / (1024 * 1024)
        except Exception:
            return 0
    return 0

def cleanup_temp_files(file_paths):
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                logger.debug(f"🗑️ Cleaned up: {path}")
            except Exception as e:
                logger.warning(f"⚠️ Cleanup error: {e}")
