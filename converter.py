import os
import subprocess
import tempfile
import re
from moviepy.editor import VideoFileClip
from config import DOWNLOAD_PATH

# ============ Zawgyi to Unicode Converter ============
ZAWGYI_TO_UNICODE_MAP = {
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

def zg2uni(text):
    """ဇော်ဂျီ ကနေ ယူနီကုဒ် ပြောင်းမယ်"""
    if not text or not isinstance(text, str):
        return text
    result = text
    for zg, uni in ZAWGYI_TO_UNICODE_MAP.items():
        result = result.replace(zg, uni)
    return result

# ============ YouTube Download Functions ============
def download_audio_from_youtube(youtube_url, output_path=None):
    """YouTube ဗီဒီယိုကနေ MP3 ကို yt-dlp သုံးပြီး ဒေါင်းလုဒ်လုပ်မယ်"""
    if not output_path:
        output_path = DOWNLOAD_PATH
    os.makedirs(output_path, exist_ok=True)

    cmd = [
        'yt-dlp',
        '--extract-audio',
        '--audio-format', 'mp3',
        '--audio-quality', '5',
        '--add-metadata',
        '--output', f'{output_path}/%(title)s.%(ext)s',
        youtube_url
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        for file in os.listdir(output_path):
            if file.endswith('.mp3'):
                file_path = os.path.join(output_path, file)
                title = os.path.splitext(file)[0]
                return file_path, title, "Unknown"
        return None, None, None
    except subprocess.CalledProcessError as e:
        print(f"Download error: {e.stderr}")
        return None, None, None

def convert_mp4_to_mp3(video_path, output_path=None):
    """MP4 ဗီဒီယိုကို MP3 အသံအဖြစ် ပြောင်းမယ်"""
    if not output_path:
        output_path = DOWNLOAD_PATH
    os.makedirs(output_path, exist_ok=True)

    try:
        video = VideoFileClip(video_path)
        if video.audio is None:
            return None, None
        output_file = os.path.join(output_path, f"{os.path.splitext(os.path.basename(video_path))[0]}.mp3")
        video.audio.write_audiofile(output_file, codec='mp3', bitrate="128k")
        video.close()
        return output_file, None
    except Exception as e:
        print(f"Conversion error: {e}")
        return None, str(e)

def get_file_size_mb(file_path):
    """ဖိုင်ရဲ့ အရွယ်အစား (MB) ကို ယူမယ်"""
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    return 0

def cleanup_temp_files(file_paths):
    """ခေတ္တဖိုင်တွေကို ရှင်းပစ်မယ်"""
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                print(f"🗑️ Cleaned up: {path}")
            except Exception as e:
                print(f"Cleanup error for {path}: {e}")
