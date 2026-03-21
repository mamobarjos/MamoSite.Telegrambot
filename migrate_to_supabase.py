"""
migrate_to_supabase.py - نقل البيانات من site_data.json إلى Supabase

استخدم هذا السكريبت مرة واحدة فقط لنقل بياناتك الحالية.

الخطوات:
1. أنشئ مشروع في Supabase
2. أنشئ جدول sites باستخدام SQL التالي:
   
   CREATE TABLE sites (
       id SERIAL PRIMARY KEY,
       website TEXT NOT NULL,
       description TEXT DEFAULT '',
       benefit TEXT DEFAULT '',
       main_category TEXT NOT NULL,
       sub_category TEXT NOT NULL,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       UNIQUE(website, main_category, sub_category)
   );
   
   CREATE INDEX idx_sites_main_category ON sites(main_category);
   CREATE INDEX idx_sites_sub_category ON sites(sub_category);
   CREATE INDEX idx_sites_website ON sites(website);

3. أضف SUPABASE_URL و SUPABASE_KEY في ملف .env
4. شغّل هذا السكريبت: python migrate_to_supabase.py
"""

import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client


def load_json_data(file_path: str) -> dict:
    """تحميل البيانات من ملف JSON."""
    if not os.path.exists(file_path):
        print(f"❌ الملف {file_path} غير موجود!")
        sys.exit(1)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def migrate(json_file: str = 'site_data.json'):
    """نقل البيانات من JSON إلى Supabase."""
    
    # التحقق من متغيرات البيئة
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_KEY", "")
    
    if not supabase_url or not supabase_key or "your-" in supabase_url:
        print("❌ يرجى تعيين SUPABASE_URL و SUPABASE_KEY في ملف .env")
        print("   مثال:")
        print("   SUPABASE_URL=https://abcdefg.supabase.co")
        print("   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIs...")
        sys.exit(1)
    
    # تحميل JSON
    print(f"📂 تحميل البيانات من {json_file}...")
    data = load_json_data(json_file)
    
    if 'main_categories' not in data:
        print("❌ الملف لا يحتوي على 'main_categories'")
        sys.exit(1)
    
    # الاتصال بـ Supabase
    print("🔗 الاتصال بـ Supabase...")
    client = create_client(supabase_url, supabase_key)
    
    # تجهيز البيانات
    sites_to_insert = []
    total_sites = 0
    skipped = 0
    
    for main_cat, content in data['main_categories'].items():
        if not isinstance(content, dict) or 'sub_categories' not in content:
            continue
        
        for sub_cat, sites in content['sub_categories'].items():
            if not isinstance(sites, list):
                continue
            
            for site in sites:
                if not isinstance(site, dict):
                    skipped += 1
                    continue
                
                total_sites += 1
                sites_to_insert.append({
                    "website": site.get('website', ''),
                    "description": site.get('description', ''),
                    "benefit": site.get('benefit', ''),
                    "main_category": main_cat,
                    "sub_category": sub_cat
                })
    
    print(f"📊 تم العثور على {total_sites} موقع (تم تخطي {skipped} عنصر غير صالح)")
    
    if not sites_to_insert:
        print("❌ لا توجد بيانات لنقلها!")
        return
    
    # إدخال البيانات على دفعات (50 موقع في كل دفعة)
    batch_size = 50
    inserted = 0
    errors = 0
    
    for i in range(0, len(sites_to_insert), batch_size):
        batch = sites_to_insert[i:i + batch_size]
        try:
            response = client.table("sites").upsert(batch, on_conflict="website,main_category,sub_category").execute()
            inserted += len(response.data)
            progress = min(i + batch_size, len(sites_to_insert))
            print(f"   ✅ {progress}/{len(sites_to_insert)} موقع...")
        except Exception as e:
            errors += len(batch)
            print(f"   ⚠️ خطأ في الدفعة {i // batch_size + 1}: {e}")
    
    print(f"\n{'='*50}")
    print(f"✅ تم نقل {inserted} موقع بنجاح!")
    if errors > 0:
        print(f"⚠️ فشل نقل {errors} موقع")
    print(f"{'='*50}")
    
    # التحقق من العدد في Supabase
    try:
        count_response = client.table("sites").select("id", count="exact").execute()
        print(f"📊 إجمالي المواقع في Supabase الآن: {count_response.count}")
    except Exception as e:
        print(f"⚠️ لم يتمكن من التحقق من العدد: {e}")


if __name__ == '__main__':
    migrate()
