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
    if user_id == 1156962576: # Owner Fallback
        return True
    try:
        client = get_client()
        result = client.table("admins").select("telegram_id").eq("telegram_id", user_id).execute()
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"خطأ في التحقق من المدير: {e}")
        return False

def add_admin(user_id: int, name: str) -> tuple[bool, str]:
    """إضافة مدير جديد"""
    try:
        client = get_client()
        data = {"telegram_id": user_id, "name": name}
        client.table("admins").insert(data).execute()
        return True, ""
    except Exception as e:
        logger.error(f"خطأ في إضافة مدير: {e}")
        return False, str(e)


def fetch_all_admins() -> list:
    """جلب قائمة بجميع المسؤولين"""
    try:
        client = get_client()
        response = client.table("admins").select("*").execute()
        return response.data
    except Exception as e:
        logger.error(f"خطأ في جلب المسؤولين: {e}")
        return []

def remove_admin(telegram_id: int) -> bool:
    """حذف مسؤول حسب رقم تيليجرام"""
    try:
        client = get_client()
        client.table("admins").delete().eq("telegram_id", telegram_id).execute()
        return True
    except Exception as e:
        logger.error(f"خطأ في حذف المسؤول: {e}")
        return False

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

def update_suggestion_data(suggestion_id: str, website: str, description: str, benefit: str) -> bool:
    """تحديث بيانات اقتراح معين (الموقع، الوصف، الفائدة)"""
    try:
        client = get_client()
        client.table("suggestions").update({
            "website": website,
            "description": description,
            "benefit": benefit
        }).eq("id", suggestion_id).execute()
        return True
    except Exception as e:
        logger.error(f"خطأ في تحديث بيانات الاقتراح: {e}")
        return False


# =====================================================
# دوال إدارة الوصول عبر IP وكلمة المرور
# =====================================================

def fetch_allowed_ips() -> list:
    """جلب قائمة الـ IPs المسموح لها"""
    try:
        client = get_client()
        response = client.table("allowed_ips").select("*").order("created_at", desc=False).execute()
        return response.data
    except Exception as e:
        logger.error(f"خطأ في جلب الـ IPs: {e}")
        return []


def add_allowed_ip(ip: str, label: str = '') -> tuple[bool, str]:
    """إضافة IP جديد إلى القائمة البيضاء"""
    try:
        client = get_client()
        # التحقق من عدم الوجود مسبقاً
        existing = client.table("allowed_ips").select("id").eq("ip", ip).execute()
        if existing.data:
            return False, "موجود مسبقاً"
        client.table("allowed_ips").insert({"ip": ip, "label": label}).execute()
        logger.info(f"تم إضافة IP {ip}")
        return True, ""
    except Exception as e:
        logger.error(f"خطأ في إضافة IP: {e}")
        return False, str(e)


def remove_allowed_ip(ip: str) -> bool:
    """حذف IP من القائمة البيضاء"""
    try:
        client = get_client()
        client.table("allowed_ips").delete().eq("ip", ip).execute()
        logger.info(f"تم حذف IP {ip}")
        return True
    except Exception as e:
        logger.error(f"خطأ في حذف IP: {e}")
        return False


def get_access_password() -> str:
    """جلب كلمة المرور الحالية"""
    try:
        client = get_client()
        response = client.table("site_settings").select("value").eq("key", "access_password").single().execute()
        return response.data.get("value", "") if response.data else ""
    except Exception as e:
        logger.error(f"خطأ في جلب كلمة المرور: {e}")
        return ""


def set_access_password(new_password: str) -> bool:
    """تغيير كلمة المرور"""
    try:
        client = get_client()
        client.table("site_settings").upsert(
            {"key": "access_password", "value": new_password, "updated_at": "now()"}
        ).execute()
        logger.info("تم تغيير كلمة المرور بنجاح")
        return True
    except Exception as e:
        logger.error(f"خطأ في تغيير كلمة المرور: {e}")
        return False


# =====================================================
# دوال نظام الحماية والأجهزة وربط المحاولات في Supabase
# =====================================================

def is_device_blocked(identifier: str) -> bool:
    """التحقق مما إذا كان الجهاز أو المستخدم محظوراً"""
    try:
        client = get_client()
        identifier_str = str(identifier)
        # فحص في جدول devices
        res = client.table("devices").select("is_blocked").or_(f"device_id.eq.{identifier_str},user_id.eq.{identifier_str}").execute()
        if res.data and any(d.get("is_blocked") for d in res.data):
            return True
        # فحص في جدول allowed_ips
        res2 = client.table("allowed_ips").select("is_blocked").eq("ip", identifier_str).execute()
        if res2.data and any(d.get("is_blocked") for d in res2.data):
            return True
        return False
    except Exception as e:
        logger.error(f"خطأ في التحقق من الحظر: {e}")
        return False


def record_login_attempt(identifier: str, success: bool, ip: str = "") -> int:
    """
    تسجيل محاولة دخول في login_attempts وإرجاع عدد المحاولات الخاطئة المتتالية.
    """
    try:
        client = get_client()
        identifier_str = str(identifier)
        
        # 1. إدراج سجل المحاولة في جدول login_attempts
        try:
            client.table("login_attempts").insert({
                "identifier": identifier_str,
                "success": success,
                "ip_address": ip
            }).execute()
        except Exception as log_err:
            logger.warning(f"تعذر الإدراج في جدول login_attempts: {log_err}")

        if success:
            reset_failed_attempts(identifier_str)
            return 0
        else:
            return increment_failed_attempts(identifier_str)
    except Exception as e:
        logger.error(f"خطأ في تسجيل محاولة الدخول: {e}")
        return 1


def increment_failed_attempts(identifier: str) -> int:
    """زيادة عداد المحاولات الفاشلة وحظر الجهاز إذا تجاوز 5 محاولات"""
    try:
        client = get_client()
        identifier_str = str(identifier)
        
        res = client.table("devices").select("*").or_(f"device_id.eq.{identifier_str},user_id.eq.{identifier_str}").execute()
        
        failed_count = 1
        if res.data:
            dev = res.data[0]
            failed_count = (dev.get("failed_attempts") or 0) + 1
            is_blocked = failed_count >= 5
            
            client.table("devices").update({
                "failed_attempts": failed_count,
                "is_blocked": is_blocked,
                "updated_at": "now()"
            }).eq("id", dev["id"]).execute()
        else:
            is_blocked = failed_count >= 5
            client.table("devices").insert({
                "user_id": identifier_str,
                "device_id": identifier_str,
                "failed_attempts": failed_count,
                "is_blocked": is_blocked
            }).execute()
            
        return failed_count
    except Exception as e:
        logger.error(f"خطأ في زيادة المحاولات الفاشلة: {e}")
        return 1


def reset_failed_attempts(identifier: str) -> bool:
    """إعادة تصفير المحاولات الفاشلة عند نجاح الدخول"""
    try:
        client = get_client()
        identifier_str = str(identifier)
        client.table("devices").update({
            "failed_attempts": 0,
            "updated_at": "now()"
        }).or_(f"device_id.eq.{identifier_str},user_id.eq.{identifier_str}").execute()
        return True
    except Exception as e:
        logger.error(f"خطأ في إعادة تصفير المحاولات: {e}")
        return False


def set_device_block_status(identifier: str, is_blocked: bool) -> bool:
    """تغيير حالة حظر جهاز أو IP في قاعدة البيانات"""
    try:
        client = get_client()
        identifier_str = str(identifier)
        
        # 1. تحديث في devices
        try:
            client.table("devices").upsert({
                "device_id": identifier_str,
                "user_id": identifier_str,
                "is_blocked": is_blocked,
                "failed_attempts": 0 if not is_blocked else 5,
                "updated_at": "now()"
            }, on_conflict="device_id").execute()
        except Exception as dev_err:
            logger.warning(f"حدث تصفير/تحديث جزئي في devices: {dev_err}")

        # 2. تحديث في allowed_ips إن وجد
        try:
            client.table("allowed_ips").update({
                "is_blocked": is_blocked
            }).eq("ip", identifier_str).execute()
        except Exception as ip_err:
            logger.warning(f"حدث تحديث جزئي في allowed_ips: {ip_err}")
            
        logger.info(f"تم تعديل حالة الحظر للجهاز {identifier_str} إلى {is_blocked}")
        return True
    except Exception as e:
        logger.error(f"خطأ في تغيير حالة الحظر: {e}")
        return False


def fetch_all_devices_and_ips() -> list:
    """جلب جميع الأجهزة والـ IPs المسموحة والمحظورة"""
    try:
        client = get_client()
        allowed_ips = client.table("allowed_ips").select("*").execute().data or []
        devices = client.table("devices").select("*").execute().data or []
        
        combined = []
        seen_ids = set()
        
        for ip_row in allowed_ips:
            ip_val = ip_row.get("ip", "")
            is_blocked = ip_row.get("is_blocked", False)
            dev_match = next((d for d in devices if d.get("device_id") == ip_val or d.get("user_id") == ip_val), None)
            if dev_match and dev_match.get("is_blocked"):
                is_blocked = True
                
            combined.append({
                "identifier": ip_val,
                "label": ip_row.get("label", "") or "IP مسموح",
                "is_blocked": is_blocked,
                "type": "ip",
                "created_at": ip_row.get("created_at", "")
            })
            seen_ids.add(ip_val)
            
        for dev_row in devices:
            dev_id = str(dev_row.get("device_id") or dev_row.get("user_id", ""))
            if dev_id and dev_id not in seen_ids:
                combined.append({
                    "identifier": dev_id,
                    "label": f"جهاز {dev_id}",
                    "is_blocked": dev_row.get("is_blocked", False),
                    "type": "device",
                    "created_at": dev_row.get("created_at", "")
                })
                seen_ids.add(dev_id)
                
        return combined
    except Exception as e:
        logger.error(f"خطأ في جلب الأجهزة والـ IPs: {e}")
        return fetch_allowed_ips()

