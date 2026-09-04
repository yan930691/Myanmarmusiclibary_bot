import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from rabbit import Rabbit
from config import MONGODB_URI

# MongoDB Client ကို ချိတ်ဆက်ပါ
if not MONGODB_URI:
    raise ValueError("MONGODB_URI environment variable is not set!")

client = MongoClient(MONGODB_URI)
db = client['music_catalog_db']  # Database Name

# Collections (SQLite ရဲ့ Table တွေနဲ့ တူတယ်)
content_types_collection = db['content_types']
categories_collection = db['categories']
contents_collection = db['contents']

def init_db():
    """Database ကို စတင်ဆောက်လုပ်မယ် (MongoDB)"""
    # Index တွေ ဖန်တီးပါ (ရှာဖွေမှု မြန်စေဖို့)
    contents_collection.create_index("youtube_url", unique=True)
    contents_collection.create_index("title")
    contents_collection.create_index("performer")
    contents_collection.create_index("category_id")
    contents_collection.create_index("file_id", unique=True)
    
    # Default Content Types ထည့်သွင်းခြင်း
    if content_types_collection.count_documents({}) == 0:
        content_types_collection.insert_many([
            {"_id": 1, "name": "Music"},
            {"_id": 2, "name": "Dhamma"},
            {"_id": 3, "name": "Audio Drama"},
            {"_id": 4, "name": "Audio Book"},
            {"_id": 5, "name": "Literature Talk"}
        ])
    
    # Default Category ထည့်သွင်းခြင်း
    if categories_collection.count_documents({}) == 0:
        categories_collection.insert_one({
            "_id": 1, 
            "content_type_id": 1, 
            "name": "မြန်မာသီချင်းများ",
            "cover_file_id": None
        })
    
    print("✅ MongoDB Database initialized successfully!")

def save_content(category_id, title, performer, album, file_id, file_type, youtube_url, metadata=""):
    """Content အသစ်ကို MongoDB ထဲ သိမ်းမယ်"""
    # ဇော်ဂျီကနေ ယူနီကုဒ်ပြောင်းပါ
    title_uni = Rabbit.zg2uni(title) if title else ""
    performer_uni = Rabbit.zg2uni(performer) if performer else ""
    album_uni = Rabbit.zg2uni(album) if album else ""
    
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
    
    try:
        result = contents_collection.insert_one(content_data)
        return str(result.inserted_id)  # ObjectId ကို string အဖြစ် ပြောင်းပါ
    except DuplicateKeyError:
        # YouTube URL ဒါမှမဟုတ် File ID နဲ့ ထပ်နေရင်
        print(f"Duplicate content: {youtube_url}")
        return None

def get_all_contents(limit=50):
    """Database ထဲက Content အားလုံးကို ယူမယ် (နောက်ဆုံးအသစ်ဆုံး)"""
    return list(contents_collection.find(
        {}, 
        {
            "_id": 1, "title": 1, "performer": 1, "album": 1, 
            "file_id": 1, "file_type": 1, "youtube_url": 1
        }
    ).sort("created_at", -1).limit(limit))

def content_exists_by_url(youtube_url):
    """ဒီ YouTube URL က Database ထဲ ရှိပြီးသားလား စစ်မယ်"""
    return contents_collection.find_one({"youtube_url": youtube_url}) is not None

def content_exists_by_file_id(file_id):
    """ဒီ File ID က Database ထဲ ရှိပြီးသားလား စစ်မယ်"""
    return contents_collection.find_one({"file_id": file_id}) is not None

def get_content_by_id(content_id):
    """Content ID (string) နဲ့ အချက်အလက်တွေကို ယူမယ်"""
    from bson import ObjectId
    try:
        return contents_collection.find_one({"_id": ObjectId(content_id)})
    except:
        return None

def get_content_by_file_id(file_id):
    """File ID နဲ့ အချက်အလက်တွေကို ယူမယ်"""
    return contents_collection.find_one({"file_id": file_id})

def search_contents(query, category_id=None):
    """Title ဒါမှမဟုတ် Performer နဲ့ ရှာဖွေမယ်"""
    filter_query = {
        "$or": [
            {"title": {"$regex": query, "$options": "i"}},
            {"performer": {"$regex": query, "$options": "i"}}
        ]
    }
    if category_id:
        filter_query["category_id"] = category_id
    
    return list(contents_collection.find(filter_query).limit(20))

def get_contents_by_category(category_id, limit=50):
    """Category ID အလိုက် Content တွေကို ယူမယ်"""
    return list(contents_collection.find(
        {"category_id": category_id},
        {
            "_id": 1, "title": 1, "performer": 1, "album": 1, 
            "file_id": 1, "file_type": 1, "youtube_url": 1
        }
    ).sort("created_at", -1).limit(limit))

def delete_content(content_id):
    """Content တစ်ခုကို ဖျက်မယ်"""
    from bson import ObjectId
    try:
        result = contents_collection.delete_one({"_id": ObjectId(content_id)})
        return result.deleted_count > 0
    except:
        return False

def count_contents():
    """စုစုပေါင်း Content အရေအတွက်ကို ယူမယ်"""
    return contents_collection.count_documents({})
