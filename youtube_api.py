import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import YOUTUBE_API_KEY, SEARCH_QUERY, MAX_RESULTS_PER_SEARCH

def search_youtube_music(query=None, max_results=MAX_RESULTS_PER_SEARCH):
    """
    YouTube မှာ သီချင်းတွေကို ရှာဖွေမယ်
    ရလဒ်: [{title, video_id, channel_name, channel_id, thumbnail}]
    """
    if not query:
        query = SEARCH_QUERY
    
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        request = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            videoCategoryId="10",  # Music Category
            maxResults=max_results,
            order="date"  # အသစ်ဆုံးက အရင်ပါ
        )
        response = request.execute()
        
        results = []
        for item in response.get('items', []):
            video_id = item['id']['videoId']
            snippet = item['snippet']
            
            # မြန်မာသီချင်းတွေကိုပဲ ရွေးဖို့ filter (ရွေးချယ်နိုင်သည်)
            title = snippet.get('title', '')
            if not is_myanmar_song(title):
                continue
                
            results.append({
                'title': title,
                'video_id': video_id,
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'channel_name': snippet.get('channelTitle', 'Unknown'),
                'channel_id': snippet.get('channelId', ''),
                'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
                'description': snippet.get('description', '')
            })
        
        return results
        
    except HttpError as e:
        print(f"YouTube API Error: {e}")
        return []

def is_myanmar_song(title):
    """ခေါင်းစဉ်ထဲမှာ မြန်မာစာလုံးတွေ ပါလားစစ်မယ်"""
    # မြန်မာယူနီကုဒ် အကွာအဝေး (U+1000 to U+109F)
    myanmar_pattern = re.compile(r'[\u1000-\u109F]')
    return bool(myanmar_pattern.search(title))

def extract_video_id(url):
    """YouTube URL ကနေ Video ID ကို ဆွဲထုတ်မယ်"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([\w-]+)',
        r'(?:youtu\.be\/)([\w-]+)',
        r'(?:youtube\.com\/embed\/)([\w-]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
