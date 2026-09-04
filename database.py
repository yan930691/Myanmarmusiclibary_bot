import sqlite3
from config import DATABASE_FILE
from rabbit import Rabbit

def init_db():
    """Database ကို စတင်ဆောက်လုပ်မယ်"""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    
    # Content Types ဇယား
    c.execute('''CREATE TABLE IF NOT EXISTS content_types
                 (id INTEGER PRIMARY KEY, name TEXT)''')
    
    # Categories ဇယား
    c.execute('''CREATE TABLE IF NOT EXISTS categories
                 (id INTEGER PRIMARY KEY, content_type_id INTEGER, name TEXT,
                  FOREIGN KEY(content_type_id) REFERENCES content_types(id))''')
    
    # Contents ဇယား
    c.execute('''CREATE TABLE IF NOT EXISTS contents
                 (id INTEGER PRIMARY KEY, category_id INTEGER, title TEXT, 
                  performer TEXT, album TEXT, file_id TEXT, file_type TEXT,
                  youtube_url TEXT, metadata TEXT,
                  FOREIGN KEY(category_id) REFERENCES categories(id))''')
    
    # Default Content Types ထည့်သွင်းခြင်း
    c.execute("INSERT OR IGNORE INTO content_types (id, name) VALUES (1, 'Music')")
    c.execute("INSERT OR IGNORE INTO content_types (id, name) VALUES (2, 'Dhamma')")
    c.execute("INSERT OR IGNORE INTO content_types (id, name) VALUES (3, 'Audio Drama')")
    
    # Default Category ထည့်သွင်းခြင်း
    c.execute("INSERT OR IGNORE INTO categories (id, content_type_id, name) VALUES (1, 1, 'မြန်မာသီချင်းများ')")
    
    conn.commit()
    conn.close()

def save_content(category_id, title, performer, album, file_id, file_type, youtube_url, metadata=""):
    """Content အသစ်ကို Database ထဲ သိမ်းမယ်"""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    
    # ဇော်ဂျီကနေ ယူနီကုဒ်ပြောင်းပါ
    title_uni = Rabbit.zg2uni(title) if title else ""
    performer_uni = Rabbit.zg2uni(performer) if performer else ""
    album_uni = Rabbit.zg2uni(album) if album else ""
    
    c.execute('''INSERT INTO contents 
                 (category_id, title, performer, album, file_id, file_type, youtube_url, metadata)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (category_id, title_uni, performer_uni, album_uni, file_id, file_type, youtube_url, metadata))
    
    content_id = c.lastrowid
    conn.commit()
    conn.close()
    return content_id

def get_all_contents():
    """Database ထဲက Content အားလုံးကို ယူမယ်"""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute('''SELECT id, title, performer, album, file_id, file_type, youtube_url 
                 FROM contents ORDER BY id DESC''')
    results = c.fetchall()
    conn.close()
    return results

def content_exists(youtube_url):
    """ဒီ YouTube URL က Database ထဲ ရှိပြီးသားလား စစ်မယ်"""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM contents WHERE youtube_url = ?", (youtube_url,))
    result = c.fetchone()
    conn.close()
    return result is not None

def get_content_by_id(content_id):
    """Content ID နဲ့ အချက်အလက်တွေကို ယူမယ်"""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute('''SELECT title, performer, album, file_id, file_type, youtube_url, metadata 
                 FROM contents WHERE id = ?''', (content_id,))
    result = c.fetchone()
    conn.close()
    return result
def get_content_count():
    """Database ထဲက သီချင်းအရေအတွက်ကို ယူမယ်"""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM contents")
    count = c.fetchone()[0]
    conn.close()
    return count
