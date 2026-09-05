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
# ffmpeg ရဲ့ Path ကို imageio_ffmpeg ကနေ ယူပါ
try:
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
    os.environ["IMAGEIO_FFMPEG_EXE"] = FFMPEG_PATH
    os.environ["FFMPEG_BINARY"] = FFMPEG_PATH
    logger.info(f"✅ FFmpeg found at: {FFMPEG_PATH}")
except Exception as e:
    logger.warning(f"⚠️ Could not find ffmpeg: {e}")
    FFMPEG_PATH = "ffmpeg"  # fallback

# ============ Zawgyi to Unicode Converter ============
ZAWGYI_TO_UNICODE_MAP = {
    'က္': 'က္', 'ဂ္': 'ဂ္', 'င္': 'င္', 'စ္': 'စ္', 'ဇ္': 'ဇ္',
    'ည္': 'ည္', 'ဋ္': 'ဋ္', 'ဌ္': 'ဌ္', 'ဍ္': 'ဍ္', 'ဏ္': 'ဏ္',
    'တ္': 'တ္', 'ထ္': 'ထ္', 'ဒ္': 'ဒ္', 'န္': 'န္', 'ပ္': 'ပ္',
    'ဗ္': 'ဗ္', 'ဘ္': 'ဘ္', 'မ္': 'မ္', 'ယ္': 'ယ္', 'ရ္': 'ရ္',
    'လ္': 'လ္', 'ဝ္': 'ဝ္', 'သ္': 'သ္', 'ဟ္': 'ဟ္', 'ဠ္': 'ဠ္',
    'အ': 'အ', 'ဣ': 'ဣ', 'ဤ': 'ဤ', 'ဥ': 'ဥ', 'ဦ': 'ဦ',
    'ဧ': 'ဧ', 'ဨ': 'ဨ', 'ဩ': 'ဩ', 'ဪ': 'ဪ',
    '၏': '၏', '၊': '၊', '။': '။',
    '္': '်', 'ျ': 'ျ', 'ွ': 'ွ', 'ှ': 'ှ', 'ဿ': 'ဿ',
    '၍': 'ရ', '၌': 'နှ', 'ႏ': 'န်', '႐': 'ရ', '႑': 'ဒ',
}

ZAWGYI_SPECIAL_CASES = {
    'ေက': 'ကေ', 'ေခ': 'ခေ', 'ေဂ': 'ဂေ', 'ေင': 'ငေ',
    'ေစ': 'စေ', 'ေဆ': 'ဆေ', 'ေဇ': 'ဇေ', 'ေဈ': 'ဈေ',
    'ေည': 'ညေ', 'ေဋ': 'ဋေ', 'ေဌ': 'ဌေ', 'ေဍ': 'ဍေ',
    'ေဎ': 'ဎေ', 'ေဏ': 'ဏေ', 'ေတ': 'တေ', 'ေထ': 'ထေ',
    'ေဒ': 'ဒေ', 'ေဓ': 'ဓေ', 'ေန': 'နေ', 'ေပ': 'ပေ',
    'ေဖ': 'ဖေ', 'ေဗ': 'ဗေ', 'ေဘ': 'ဘေ', 'ေမ': 'မေ',
    'ေယ': 'ယေ', 'ေရ': 'ရေ', 'ေလ': 'လေ', 'ေဝ': 'ဝေ',
    'ေသ': 'သေ', 'ေဟ': 'ဟေ', 'ေဠ': 'ဠေ', 'ေအ': 'အေ',
}

def zg2uni(text):
    """ဇော်ဂျီ ကနေ ယူနီကုဒ် ပြောင်းမယ်"""
    if not text or not isinstance(text, str):
        return text
    
    result = text
    for zg, uni in ZAWGYI_SPECIAL_CASES.items():
        result = result.replace(zg, uni)
    for zg, uni in ZAWGYI_TO_UNICODE_MAP.items():
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

# ============ YouTube Download Functions ============

def download_audio_from_youtube(youtube_url, output_path=None):
    """YouTube ဗီဒီယိုကနေ MP3 ကို yt-dlp သုံးပြီး ဒေါင်းလုဒ်လုပ်မယ်"""
    if not output_path:
        output_path = DOWNLOAD_PATH
    
    os.makedirs(output_path, exist_ok=True)
    
    cmd = [
        'yt-dlp',
        '--ffmpeg-location', FFMPEG_PATH,
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
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"❌ Download failed: {result.stderr[:500]}")
            return None, None, None
        
        for file in os.listdir(output_path):
            if file.endswith('.mp3'):
                file_path = os.path.join(output_path, file)
                title = os.path.splitext(file)[0]
                title = clean_filename(title)
                logger.info(f"📁 Downloaded: {file_path}")
                return file_path, title, "Unknown"
        
        logger.error(f"❌ No MP3 file found")
        return None, None, None
        
    except subprocess.TimeoutExpired:
        logger.error(f"❌ Download timeout")
        return None, None, None
    except Exception as e:
        logger.error(f"❌ Download error: {e}")
        return None, None, None

def get_file_size_mb(file_path):
    """ဖိုင်ရဲ့ အရွယ်အစား (MB) ကို ယူမယ်"""
    if os.path.exists(file_path):
        try:
            return os.path.getsize(file_path) / (1024 * 1024)
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
                logger.warning(f"⚠️ Cleanup error: {e}")
