#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YouTube API Wrapper (SoundCloud ကို ခေါ်ဖို့ ပြောင်းထားတယ်)
ဒီဖိုင်ကို YouTube API လို့ နာမည်ထားပေမယ့် SoundCloud ကနေ ရှာပါမယ်
"""

import subprocess
import json
import logging
from config import SEARCH_QUERY, MAX_RESULTS_PER_SEARCH

logger = logging.getLogger(__name__)

def search_youtube_music(query=None, max_results=MAX_RESULTS_PER_SEARCH):
    """
    SoundCloud မှာ သီချင်းတွေကို ရှာဖွေမယ် (yt-dlp သုံးပြီး)
    """
    if not query:
        query = SEARCH_QUERY
    
    cmd = [
        'yt-dlp',
        f'scsearch:{query}',
        '--flat-playlist',
        '--dump-json',
        '--no-playlist',
        '--max-downloads', str(max_results)
    ]
    
    logger.info(f"🔍 Searching SoundCloud: {query}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False
        )
        
        if result.returncode != 0:
            logger.error(f"❌ Search failed: {result.stderr[:200]}")
            return []
        
        results = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                title = data.get('title', '')
                url = data.get('url', '')
                if not url:
                    continue
                    
                results.append({
                    'title': title,
                    'url': url,
                    'channel_name': data.get('uploader', 'Unknown'),
                    'channel_id': data.get('channel_id', ''),
                    'thumbnail': data.get('thumbnail', ''),
                    'description': data.get('description', ''),
                    'duration': data.get('duration', 0)
                })
            except json.JSONDecodeError:
                continue
        
        logger.info(f"✅ Found {len(results)} results from SoundCloud")
        return results
        
    except subprocess.TimeoutExpired:
        logger.error("❌ Search timeout")
        return []
    except Exception as e:
        logger.error(f"❌ Search error: {e}")
        return []
