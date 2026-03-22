"""
db.py - طبقة الاتصال مع Supabase
يستبدل القراءة/الكتابة من ملف JSON بعمليات مباشرة على قاعدة البيانات
"""

import logging
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# إنشاء عميل Supabase
_supabase_client: Client = None


def get_client() -> Client:
    """الحصول على عميل Supabase (يُنشأ مرة واحدة فقط)."""
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL و SUPABASE_KEY يجب أن يكونا محددين في متغيرات البيئة")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("تم الاتصال بـ Supabase بنجاح")
    return _supabase_client


def fetch_all_sites() -> list:
    """
    جلب جميع المواقع من Supabase (مع التصفح لتجاوز حد 1000 صف).
    
    Returns:
        list: قائمة من القواميس تحتوي على بيانات المواقع.
    """
    try:
        client = get_client()
        all_data = []
        page_size = 1000
        offset = 0
        
        while True:
            response = client.table("sites").select("*").range(offset, offset + page_size - 1).execute()
            if not response.data:
                break
            all_data.extend(response.data)
            if len(response.data) < page_size:
                break  # آخر صفحة
            offset += page_size
        
        logger.info(f"تم جلب {len(all_data)} موقع من Supabase")
        return all_data
    except Exception as e:
        logger.error(f"خطأ في جلب البيانات من Supabase: {e}")
        return []


def add_site(main_category: str, sub_category: str, website: str, description: str, benefit: str = "") -> bool:
    """
    إضافة موقع جديد إلى Supabase مع منع التكرار.
    
    Returns:
        bool: True إذا تمت الإضافة بنجاح.
    """
    try:
        client = get_client()
        
        # التحقق من عدم وجود الموقع مسبقاً
        existing = client.table("sites").select("id").eq(
            "website", website
        ).eq(
            "main_category", main_category
        ).eq(
            "sub_category", sub_category
        ).execute()
        
        if existing.data:
            logger.info(f"الموقع {website} موجود بالفعل في {main_category}/{sub_category}")
            return False
        
        # إضافة الموقع
        client.table("sites").insert({
            "website": website,
            "description": description,
            "benefit": benefit,
            "main_category": main_category,
            "sub_category": sub_category
        }).execute()
        
        logger.info(f"تم إضافة الموقع {website} بنجاح إلى {main_category}/{sub_category}")
        return True
    except Exception as e:
        logger.error(f"خطأ في إضافة الموقع: {e}")
        return False


def update_site(main_category: str, sub_category: str, old_website: str,
                new_website: str, new_description: str, new_benefit: str) -> bool:
    """
    تعديل موقع موجود في Supabase.
    
    Returns:
        bool: True إذا تم التعديل بنجاح.
    """
    try:
        client = get_client()
        response = client.table("sites").update({
            "website": new_website,
            "description": new_description,
            "benefit": new_benefit
        }).eq(
            "website", old_website
        ).eq(
            "main_category", main_category
        ).eq(
            "sub_category", sub_category
        ).execute()
        
        if response.data:
            logger.info(f"تم تعديل الموقع {old_website} بنجاح إلى {new_website}")
            return True
        else:
            logger.info(f"لم يتم العثور على الموقع {old_website} في {main_category}/{sub_category}")
            return False
    except Exception as e:
        logger.error(f"خطأ في تعديل الموقع: {e}")
        return False


def remove_site(main_category_en: str, sub_category_en: str, website: str) -> bool:
    """
    حذف موقع من Supabase.
    """
    try:
        client = get_client()
        client.table("sites").delete().eq(
            "website", website
        ).eq(
            "main_category", main_category_en
        ).eq(
            "sub_category", sub_category_en
        ).execute()
        
        logger.info(f"تم حذف الموقع {website} بنجاح من {main_category_en}/{sub_category_en}")
        return True
    except Exception as e:
        logger.error(f"خطأ في حذف الموقع: {e}")
        return False


def fetch_sites_as_nested_dict() -> dict:
    """
    جلب جميع المواقع وتحويلها إلى البنية المتداخلة (نفس بنية site_data.json).
    
    Returns:
        dict: بيانات بنفس بنية الملف الأصلي {"main_categories": {...}}
    """
    sites = fetch_all_sites()
    data = {"main_categories": {}}
    
    for site in sites:
        main_cat = site.get("main_category", "")
        sub_cat = site.get("sub_category", "")
        
        if main_cat not in data["main_categories"]:
            data["main_categories"][main_cat] = {"sub_categories": {}}
        
        if sub_cat not in data["main_categories"][main_cat]["sub_categories"]:
            data["main_categories"][main_cat]["sub_categories"][sub_cat] = []
        
        data["main_categories"][main_cat]["sub_categories"][sub_cat].append({
            "website": site.get("website", ""),
            "description": site.get("description", ""),
            "benefit": site.get("benefit", "")
        })
    
    return data


def check_duplicate(website: str) -> list:
    """
    فحص هل الموقع موجود مسبقاً في أي تصنيف.
    
    Args:
        website: رابط أو اسم الموقع.
    
    Returns:
        list: قائمة بالسجلات المطابقة (فارغة إذا لم يُعثر عليه).
    """
    try:
        client = get_client()
        # بحث دقيق أولاً
        response = client.table("sites").select("*").eq("website", website).execute()
        if response.data:
            return response.data
        
        # بحث جزئي إذا لم يُعثر بدقة
        response = client.table("sites").select("*").ilike("website", f"%{website}%").execute()
        return response.data
    except Exception as e:
        logger.error(f"خطأ في فحص التكرار: {e}")
        return []


def is_admin(user_id: int) -> bool:
    """التحقق مما إذا كان المستخدم مديراً"""
    if user_id == 257741366: # Owner Fallback
        return True
    try:
        client = get_client()
        result = client.table("admins").select("user_id").eq("user_id", user_id).execute()
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"خطأ في التحقق من المدير: {e}")
        return False

def add_admin(user_id: int, name: str) -> bool:
    """إضافة مدير جديد"""
    try:
        client = get_client()
        data = {"user_id": user_id, "name": name}
        client.table("admins").insert(data).execute()
        return True
    except Exception as e:
        logger.error(f"خطأ في إضافة مدير: {e}")
        return False


def fetch_all_admins() -> list:
    """جلب قائمة بجميع المسؤولين"""
    try:
        client = get_client()
        response = client.table("admins").select("*").execute()
        return response.data
    except Exception as e:
        logger.error(f"خطأ في جلب المسؤولين: {e}")
        return []

# --- دوال إدارة الاقتراحات (Suggestions) ---

def fetch_pending_suggestions() -> list:
    """جلب الاقتراحات المعلقة"""
    try:
        client = get_client()
        response = client.table("suggestions").select("*").eq("status", "pending").order("created_at").execute()
        return response.data
    except Exception as e:
        logger.error(f"خطأ في جلب الاقتراحات: {e}")
        return []

def update_suggestion_status(suggestion_id: str, new_status: str) -> bool:
    """تحديث حالة اقتراح معين (approved, rejected)"""
    try:
        client = get_client()
        client.table("suggestions").update({"status": new_status}).eq("id", suggestion_id).execute()
        return True
    except Exception as e:
        logger.error(f"خطأ في تحديث الاقتراح: {e}")
        return False
