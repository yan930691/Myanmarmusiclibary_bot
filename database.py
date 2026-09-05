#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
import logging

from config import MONGODB_URI, DATABASE_NAME
from converter import zg2uni

logger = logging.getLogger(__name__)

# MongoDB Client
client = MongoClient(MONGODB_URI)
db = client[DATABASE_NAME]

content_types_collection = db['content_types']
categories_collection = db['categories']
contents_collection = db['contents']

def test_connection():
    try:
        client.admin.command('ping')
        logger.info("✅ MongoDB connection successful!")
        return True
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        return False

def init_db():
    try:
        contents_collection.create_index("youtube_url", unique=True)
        contents_collection.create_index("title")
        contents_collection.create_index("performer")
        contents_collection.create_index("category_id")
        contents_collection.create_index("created_at", expireAfterSeconds=60*60*24*30)

        if content_types_collection.count_documents({}) == 0:
            content_types_collection.insert_many([
                {"_id": 1, "name": "Music", "created_at": datetime.utcnow()},
                {"_id": 2, "name": "Dhamma", "created_at": datetime.utcnow()},
                {"_id": 3, "name": "Audio Drama", "created_at": datetime.utcnow()},
                {"_id": 4, "name": "Audio Book", "created_at": datetime.utcnow()},
                {"_id": 5, "name": "Literature Talk", "created_at": datetime.utcnow()}
            ])

        if categories_collection.count_documents({}) == 0:
            categories_collection.insert_many([
                {"_id": 1, "content_type_id": 1, "name": "မြန်မာသီချင်းများ", "cover_file_id": None, "created_at": datetime.utcnow()},
                {"_id": 2, "content_type_id": 2, "name": "ဓမ္မစကားများ", "cover_file_id": None, "created_at": datetime.utcnow()},
                {"_id": 3, "content_type_id": 3, "name": "အသံဇာတ်လမ်းများ", "cover_file_id": None, "created_at": datetime.utcnow()}
            ])
        
        logger.info("✅ Database initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ Database init error: {e}")
        return False

def save_content(category_id, title, performer, album, file_id, file_type, youtube_url, metadata=""):
    try:
        title_uni = zg2uni(title) if title else "ခေါင်းစဉ်မသတ်မှတ်ရသေး"
        performer_uni = zg2uni(performer) if performer else "အဆိုတော်မသတ်မှတ်ရသေး"
        album_uni = zg2uni(album) if album else "အယ်လ်ဘမ်မသတ်မှတ်ရသေး"

        content_data = {
            "category_id": category_id,
            "title": title_uni,
            "performer": performer_uni,
            "album": album_uni,
            "file_id": file_id,
            "file_type": file_type,
            "youtube_url": youtube_url,
            "metadata": metadata,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = contents_collection.insert_one(content_data)
        return str(result.inserted_id)
    except DuplicateKeyError:
        logger.warning(f"⚠️ Content already exists: {youtube_url}")
        return None
    except Exception as e:
        logger.error(f"❌ Save content error: {e}")
        return None

def content_exists(youtube_url):
    try:
        return contents_collection.find_one({"youtube_url": youtube_url}) is not None
    except Exception as e:
        logger.error(f"❌ Check content exists error: {e}")
        return False

def get_content_by_file_id(file_id):
    try:
        return contents_collection.find_one({"file_id": file_id})
    except Exception as e:
        logger.error(f"❌ Get content by file ID error: {e}")
        return None

def get_stats():
    try:
        total_contents = contents_collection.count_documents({})
        total_music = contents_collection.count_documents({"category_id": 1})
        total_dhamma = contents_collection.count_documents({"category_id": 2})
        return {
            "total": total_contents,
            "music": total_music,
            "dhamma": total_dhamma,
            "others": total_contents - total_music - total_dhamma
        }
    except Exception as e:
        logger.error(f"❌ Get stats error: {e}")
        return {"total": 0, "music": 0, "dhamma": 0, "others": 0}

def get_categories():
    """Category အားလုံးကို ယူမယ်"""
    try:
        return list(categories_collection.find({}, {
            "_id": 0,
            "id": {"$toString": "$_id"},
            "content_type_id": 1,
            "name": 1
        }))
    except Exception as e:
        logger.error(f"❌ Get categories error: {e}")
        return []

def delete_content(content_id):
    try:
        result = contents_collection.delete_one({"_id": ObjectId(content_id)})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"❌ Delete content error: {e}")
        return False
