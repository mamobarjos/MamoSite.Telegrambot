import sqlite3
import json
import os
from typing import Dict, List, Union

def load_json_file(file_path: str) -> Union[Dict, List]:
    """تحميل ملف JSON والتحقق من وجوده."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ملف {file_path} غير موجود!")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"خطأ في قراءة ملف JSON: {e}")

def initialize_database(db_path: str) -> sqlite3.Connection:
    """تهيئة قاعدة بيانات SQLite وإنشاء/تعديل الجدول."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # إنشاء الجدول إذا لم يكن موجودًا
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            website TEXT,
            description TEXT,
            benefit TEXT,
            category TEXT,
            sub_category TEXT,
            PRIMARY KEY (website, category, sub_category)
        )
    ''')
    
    # التحقق مما إذا كان العمود sub_category موجودًا، وإضافته إذا لزم الأمر
    cursor.execute("PRAGMA table_info(resources)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'sub_category' not in columns:
        cursor.execute('ALTER TABLE resources ADD COLUMN sub_category TEXT')
    
    # إنشاء الفهارس
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON resources(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sub_category ON resources(sub_category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_website ON resources(website)')
    
    conn.commit()
    return conn

def insert_data_to_db(conn: sqlite3.Connection, data: Dict) -> int:
    """إدخال البيانات من JSON إلى قاعدة البيانات."""
    cursor = conn.cursor()
    total_inserted = 0

    if 'main_categories' not in data:
        print("تحذير: المفتاح 'main_categories' غير موجود. التحقق من الفئات مباشرة.")
        return total_inserted

    for category, category_data in data['main_categories'].items():
        if not isinstance(category_data, dict) or 'sub_categories' not in category_data:
            print(f"تحذير: الفئة '{category}' لا تحتوي على 'sub_categories' أو ليست كائنًا.")
            continue

        for sub_category, items in category_data['sub_categories'].items():
            if not isinstance(items, list):
                print(f"تحذير: الفئة الفرعية '{sub_category}' ليست قائمة.")
                continue

            for item in items:
                try:
                    if isinstance(item, str):
                        # التعامل مع روابط مباشرة
                        cursor.execute('''
                            INSERT OR IGNORE INTO resources (website, description, benefit, category, sub_category)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (item, 'رابط', 'رابط', category, sub_category))
                        total_inserted += cursor.rowcount
                    elif isinstance(item, dict):
                        # التعامل مع كائنات
                        cursor.execute('''
                            INSERT OR IGNORE INTO resources (website, description, benefit, category, sub_category)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (item.get('website', ''), 
                              item.get('description', ''), 
                              item.get('benefit', ''), 
                              category, 
                              item.get('sub_category', sub_category)))
                        total_inserted += cursor.rowcount
                    else:
                        print(f"تحذير: عنصر غير متوقع في '{category}/{sub_category}': {item}")
                except KeyError as e:
                    print(f"تحذير: عنصر في '{category}/{sub_category}' يفتقد المفتاح {e}. تخطي العنصر.")
                    continue

    conn.commit()
    return total_inserted

def main():
    """الدالة الرئيسية لتحويل JSON إلى SQLite."""
    json_file = 'site_data.json'
    db_file = 'site_data.db'
    
    try:
        # تحميل JSON
        data = load_json_file(json_file)
        
        # تهيئة قاعدة البيانات
        conn = initialize_database(db_file)
        
        # إدخال البيانات
        total_inserted = insert_data_to_db(conn, data)
        
        # إغلاق الاتصال
        conn.close()
        
        print(f"تم تحويل البيانات إلى قاعدة بيانات SQLite في {db_file}.")
        print(f"إجمالي السجلات المُدخلة: {total_inserted}")
        
    except Exception as e:
        print(f"حدث خطأ: {e}")

if __name__ == '__main__':
    main()