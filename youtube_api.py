import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import YOUTUBE_API_KEY, SEARCH_QUERY, MAX_RESULTS_PER_SEARCH

def search_youtube_music(query=None, max_results=MAX_RESULTS_PER_SEARCH):
    if not query:
        query = SEARCH_QUERY

    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

        request = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            videoCategoryId="10",
            maxResults=max_results,
            order="date"
        )
        response = request.execute()

        results = []
        for item in response.get('items', []):
            video_id = item['id']['videoId']
            snippet = item['snippet']
            title = snippet.get('title', '')
            
            if not re.search(r'[\u1000-\u109F]', title):
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
