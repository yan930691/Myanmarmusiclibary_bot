import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError, OperationFailure
from rabbit import Rabbit
from config import MONGODB_URI

# MongoDB Client ကို ချိတ်ဆက်ပါ
try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    # Connection ကောင်းမကောင်း စစ်ဆေးပါ
    client.admin.command('ping')
    print("✅ MongoDB ကို အောင်မြင်စွာ ချိတ်ဆက်နိုင်ခဲ့ပါပြီ။")
except ConnectionFailure as e:
    print(f"❌ MongoDB ချိတ်ဆက်ရာမှာ အဆင်မပြေပါ: {e}")
    exit(1)

db = client['music_catalog_db']  # Database Name

# Collections (SQLite ရဲ့ Table တွေနဲ့ တူတယ်)
content_types_collection = db['content_types']
categories_collection = db['categories']
contents_collection = db['contents']

def init_db():
    """Database ကို စတင်ဆောက်လုပ်မယ် (MongoDB)"""
    try:
        # Index တွေ ဖန်တီးပါ (ရှာဖွေမှု မြန်စေဖို့)
        contents_collection.create_index("youtube_url", unique=True)
        contents_collection.create_index("title")
        contents_collection.create_index("performer")
        contents_collection.create_index("category_id")
        contents_collection.create_index("created_at")

        # Default Content Types ထည့်သွင်းခြင်း
        if content_types_collection.count_documents({}) == 0:
            content_types_collection.insert_many([
                {"_id": 1, "name": "Music"},
                {"_id": 2, "name": "Dhamma"},
                {"_id": 3, "name": "Audio Drama"},
                {"_id": 4, "name": "Audio Book"},
                {"_id": 5, "name": "Literature Talk"}
            ])
            print("✅ Content Types များ ထည့်သွင်းပြီးပါပြီ။")

        # Default Category ထည့်သွင်းခြင်း
        if categories_collection.count_documents({}) == 0:
            categories_collection.insert_one({
                "_id": 1,
                "content_type_id": 1,
                "name": "မြန်မာသီချင်းများ",
                "cover_file_id": None
            })
            print("✅ Default Category ထည့်သွင်းပြီးပါပြီ။")

        print("✅ Database စတင်ဆောက်လုပ်ခြင်း ပြီးဆုံးပါပြီ။")
    except OperationFailure as e:
        print(f"❌ Database ဆောက်လုပ်ရာမှာ အဆင်မပြေပါ: {e}")

def save_content(category_id, title, performer, album, file_id, file_type, youtube_url, metadata=""):
    """Content အသစ်ကို MongoDB ထဲ သိမ်းမယ်"""
    try:
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
            "created_at": datetime.utcnow()
        }

        result = contents_collection.insert_one(content_data)
        print(f"✅ Content သိမ်းဆည်းပြီးပါပြီ။ ID: {result.inserted_id}")
        return result.inserted_id
    except DuplicateKeyError:
        print(f"⚠️ ဒီ YouTube URL က ရှိပြီးသားပါ: {youtube_url}")
        return None
    except Exception as e:
        print(f"❌ Content သိမ်းဆည်းရာမှာ အဆင်မပြေပါ: {e}")
        return None

def get_all_contents(limit=100):
    """Database ထဲက Content အားလုံးကို ယူမယ်"""
    try:
        return list(contents_collection.find({}, {
            "_id": 1, "title": 1, "performer": 1, "album": 1,
            "file_id": 1, "file_type": 1, "youtube_url": 1, "created_at": 1
        }).sort("created_at", -1).limit(limit))
    except Exception as e:
        print(f"❌ Content များကို ယူရာမှာ အဆင်မပြေပါ: {e}")
        return []

def get_contents_by_category(category_id, limit=50):
    """Category ID နဲ့ Content များကို ယူမယ်"""
    try:
        return list(contents_collection.find(
            {"category_id": category_id},
            {"_id": 1, "title": 1, "performer": 1, "album": 1, "file_id": 1}
        ).sort("created_at", -1).limit(limit))
    except Exception as e:
        print(f"❌ Category အတိုင်း Content များကို ယူရာမှာ အဆင်မပြေပါ: {e}")
        return []

def content_exists(youtube_url):
    """ဒီ YouTube URL က Database ထဲ ရှိပြီးသားလား စစ်မယ်"""
    try:
        return contents_collection.find_one({"youtube_url": youtube_url}) is not None
    except Exception as e:
        print(f"❌ Content ရှိမရှိ စစ်ဆေးရာမှာ အဆင်မပြေပါ: {e}")
        return False

def get_content_by_id(content_id):
    """Content ID နဲ့ အချက်အလက်တွေကို ယူမယ်"""
    try:
        from bson import ObjectId
        return contents_collection.find_one({"_id": ObjectId(content_id)})
    except Exception as e:
        print(f"❌ Content ID နဲ့ ရှာဖွေရာမှာ အဆင်မပြေပါ: {e}")
        return None

def get_content_by_file_id(file_id):
    """File ID နဲ့ အချက်အလက်တွေကို ယူမယ်"""
    try:
        return contents_collection.find_one({"file_id": file_id})
    except Exception as e:
        print(f"❌ File ID နဲ့ ရှာဖွေရာမှာ အဆင်မပြေပါ: {e}")
        return None

def search_contents(query, category_id=None, limit=20):
    """Title ဒါမှမဟုတ် Performer နဲ့ ရှာဖွေမယ်"""
    try:
        filter_query = {
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"performer": {"$regex": query, "$options": "i"}}
            ]
        }
        if category_id:
            filter_query["category_id"] = category_id

        return list(contents_collection.find(filter_query, {
            "_id": 1, "title": 1, "performer": 1, "album": 1, "file_id": 1
        }).limit(limit))
    except Exception as e:
        print(f"❌ ရှာဖွေရာမှာ အဆင်မပြေပါ: {e}")
        return []

def delete_content(content_id):
    """Content တစ်ခုကို ဖျက်မယ်"""
    try:
        from bson import ObjectId
        result = contents_collection.delete_one({"_id": ObjectId(content_id)})
        if result.deleted_count > 0:
            print(f"✅ Content ဖျက်ပြီးပါပြီ။ ID: {content_id}")
            return True
        else:
            print(f"⚠️ Content မတွေ့ပါ။ ID: {content_id}")
            return False
    except Exception as e:
        print(f"❌ Content ဖျက်ရာမှာ အဆင်မပြေပါ: {e}")
        return False

def get_statistics():
    """Database ရဲ့ စာရင်းအင်းတွေကို ယူမယ်"""
    try:
        total_contents = contents_collection.count_documents({})
        total_music = contents_collection.count_documents({"category_id": 1})
        total_dhamma = contents_collection.count_documents({"category_id": 2})
        total_drama = contents_collection.count_documents({"category_id": 3})

        return {
            "total_contents": total_contents,
            "total_music": total_music,
            "total_dhamma": total_dhamma,
            "total_drama": total_drama
        }
    except Exception as e:
        print(f"❌ စာရင်းအင်းများ ယူရာမှာ အဆင်မပြေပါ: {e}")
        return {}
