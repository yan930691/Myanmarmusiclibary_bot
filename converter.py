import os
import subprocess
import tempfile
from moviepy.editor import VideoFileClip

def download_audio_from_youtube(youtube_url, output_path=None):
    """
    YouTube ဗီဒီယိုကနေ MP3 ကို yt-dlp သုံးပြီး ဒေါင်းလုဒ်လုပ်မယ်
    ရလဒ်: (audio_file_path, title, performer)
    """
    if not output_path:
        output_path = tempfile.gettempdir()
    
    # yt-dlp အတွက် Command
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
        
        # ဒေါင်းလုဒ်လုပ်ထားတဲ့ ဖိုင်ကို ရှာမယ်
        for file in os.listdir(output_path):
            if file.endswith('.mp3'):
                file_path = os.path.join(output_path, file)
                title = os.path.splitext(file)[0]
                performer = "Unknown"
                return file_path, title, performer
        
        return None, None, None
        
    except subprocess.CalledProcessError as e:
        print(f"Download error: {e.stderr}")
        return None, None, None

def convert_mp4_to_mp3(video_path, output_path=None):
    """
    MP4 ဗီဒီယိုကို MP3 အသံအဖြစ် ပြောင်းမယ်
    """
    if not output_path:
        output_path = tempfile.gettempdir()
    
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
# ဇော်ဂျီ-ယူနီကုဒ် ပြောင်းတဲ့ Mapping ကို သတ်မှတ်ပါ
ZAWGYI_TO_UNICODE = {
    '္': '်', 'ႏ': 'န်', '၍': 'ရ', '၌': 'နှ', 
    # ... စာလုံးတွေ အကုန်လုံးကို ထည့်ဖို့ လိုပါလိမ့်မယ်
}

def zg2uni(text):
    """ဇော်ဂျီ ကနေ ယူနီကုဒ် ပြောင်းမယ်"""
    if not text:
        return text
    result = text
    for zg, uni in ZAWGYI_TO_UNICODE.items():
        result = result.replace(zg, uni)
    return result
