import json
import re
import logging
from fuzzywuzzy import fuzz
import arabic_reshaper
from bidi.algorithm import get_display
from db import fetch_all_sites, add_site, update_site, remove_site, fetch_sites_as_nested_dict

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# قائمة التصنيفات بالإنجليزية
CATEGORIES = {
    "artificial_intelligence": ["ai_video_image_editing", "ai_bots_and_tools", "ai_prompt_writing", "ai_video_generation", "ai_avatars_and_characters", "ai_voice_and_music", "ai_content_creation"],
    "chrome_extensions": ["video_and_translation", "email_and_messaging", "content_and_design", "productivity_and_tools", "social_media_and_marketing", "ai_and_chatgpt", "education_and_exams", "website_analysis", "business_and_contacts"],
    "computer_and_technology": ["pc_building", "tech_tools", "file_management", "file_upload", "software_downloads", "device_repair", "qr_code_generator", "screen_recording", "video_backgrounds"],
    "cybersecurity": ["cybersecurity_tools", "dark_web", "linux_tools", "osint_and_people_search", "privacy_tools", "link_and_file_scanning", "password_and_identity", "email_and_phone_verification"],
    "design": ["libraries", "learning", "colors", "image_search", "ad_image_design", "photoshop_templates", "image_editing", "text_to_image", "image_lighting", "image_selling", "drawing_tools", "logo_design", "logo_animation"],
    "ecommerce": ["store_creation", "car_parts", "wholesale", "domain_purchase", "dropshipping", "amazon_training", "amazon_tools", "digital_products", "drop_service", "brand_naming"],
    "english_learning": ["language_learning"],
    "lifestyle_and_health": ["health_and_fitness", "movies_and_series", "travel_tools", "scholarship_tools", "calm_music"],
    "online_shopping": ["cheap_subscriptions", "shopping_assistance", "global_brands", "turkish_shopping"],
    "miscellaneous_useful_sites": ["research_and_questions", "home_and_interior_design", "live_streaming_and_games", "diy_projects", "kids_and_education", "miscellaneous_tools", "fake_cards_and_ids"],
    "online_work": ["youtube_tools", "online_jobs", "job_search", "project_ideas", "project_tools", "investor_platforms", "course_creation", "course_publishing", "link_shorteners", "document_templates"],
    "programming": ["study_programming", "program_projects", "solve_programming_problems", "website_development", "website_analysis", "seo_tools", "no_code_website_builders", "app_development", "no_code_app_builders", "advanced_programming_tools", "github_tools", "qa_testing"],
    "sound": ["music_download", "sound_search", "sound_editing", "text_to_speech"],
    "telegram_bots": ["media_and_images", "messaging_and_communication", "file_management", "downloads_and_content", "education_and_resources", "security_and_privacy", "miscellaneous_tools"],
    "trading_and_cryptocurrencies": ["crypto_and_forex_trading", "nft_platforms", "nft_games"],
    "university_tools": ["general_tools", "study_and_courses", "research_tools", "presentation_tools", "cv_and_job_tools", "free_books", "plagiarism_detection", "ai_detection", "paraphrasing_tools"],
    "video": ["video_download", "video_editing", "motion_videos", "video_montage", "animated_video_icons", "subtitle_tools"],
    "writing_and_articles": ["free_article_sources", "ai_article_generation", "ai_writing_tools", "article_writing_tools", "email_writing_tools", "paid_article_writing"],
    "marketing": [
        "study_marketing", "content_ideas", "competitor_analysis", "data_collection", "audience_insights",
        "marketing_platforms", "response_tools", "task_management", "content_writing", "content_analysis",
        "ad_design", "video_design_pros", "video_recording", "ready_ad_templates", "ai_content_creation",
        "social_media_analysis", "ad_performance_analysis", "customer_communication", "chatbots",
        "content_publishing", "hashtags", "email_marketing", "affiliate_marketing", "affiliate_links",
        "link_management", "landing_pages", "social_media_tools", "tiktok_optimization",
        "social_media_management", "document_management", "account_trading", "ai_marketing"
    ]
}

# خريطة الترجمة من الإنجليزية إلى العربية للتصنيفات الفرعية
SUB_CATEGORY_TRANSLATION = {
    "ai_video_image_editing": "تعديل فيديو وصور",
    "ai_bots_and_tools": "بوتات وأدوات ذكية",
    "ai_prompt_writing": "كتابة البرومبت",
    "video_and_translation": "الفيديو والترجمة",
    "email_and_messaging": "الإيميلات والرسائل",
    "content_and_design": "المحتوى والتصميم",
    "productivity_and_tools": "الإنتاجية والأدوات",
    "social_media_and_marketing": "وسائل التواصل",
    "ai_and_chatgpt": "الذكاء الاصطناعي",
    "education_and_exams": "التعليم والامتحانات",
    "website_analysis": "تحليل المواقع",
    "business_and_contacts": "الأعمال وجهات الاتصال",
    "pc_building": "تجميع الكمبيوتر",
    "tech_tools": "أدوات تقنية",
    "file_management": "إدارة الملفات",
    "file_upload": "رفع الملفات",
    "software_downloads": "تحميل البرامج",
    "device_repair": "إصلاح الأجهزة",
    "qr_code_generator": "مولد رموز QR",
    "screen_recording": "تسجيل الشاشة",
    "video_backgrounds": "خلفيات فيديو",
    "cybersecurity_tools": "أدوات الأمن",
    "dark_web": "الويب المظلم",
    "linux_tools": "أدوات لينكس",
    "libraries": "مكتبات التصميم",
    "learning": "التعلم",
    "colors": "الألوان",
    "image_search": "بحث الصور",
    "ad_image_design": "تصميم إعلانات",
    "photoshop_templates": "قوالب فوتوشوب",
    "image_editing": "تعديل الصور",
    "text_to_image": "نص إلى صورة",
    "image_lighting": "إضاءة الصور",
    "image_selling": "بيع الصور",
    "drawing_tools": "أدوات الرسم",
    "logo_design": "تصميم الشعارات",
    "logo_animation": "تحريك الشعارات",
    "store_creation": "إنشاء متجر",
    "car_parts": "قطع غيار السيارات",
    "wholesale": "الجملة",
    "domain_purchase": "شراء نطاق",
    "dropshipping": "الدروبشيبينغ",
    "amazon_training": "تدريب أمازون",
    "amazon_tools": "أدوات أمازون",
    "digital_products": "منتجات رقمية",
    "drop_service": "خدمة الدروب",
    "language_learning": "تعلم اللغة",
    "health_and_fitness": "الصحة وبناء العضلات",
    "movies_and_series": "الأفلام والمسلسلات",
    "travel_tools": "أدوات السفر",
    "scholarship_tools": "أدوات المنح الدراسية",
    "calm_music": "موسيقى هادئة",
    "cheap_subscriptions": "اشتراكات رخيصة",
    "shopping_assistance": "مساعدة التسوق",
    "global_brands": "ماركات عالمية",
    "turkish_shopping": "تسوق تركي",
    "research_and_questions": "البحث والأسئلة",
    "home_and_interior_design": "تصميم البيوت والديكور",
    "live_streaming_and_games": "البث المباشر والألعاب",
    "diy_projects": "مشاريع يدوية",
    "kids_and_education": "الأطفال والتعليم",
    "miscellaneous_tools": "أدوات متنوعة",
    "fake_cards_and_ids": "بطاقات وهمية",
    "youtube_tools": "أدوات يوتيوب",
    "online_jobs": "وظائف عبر الإنترنت",
    "job_search": "بحث عن عمل",
    "project_ideas": "أفكار مشاريع",
    "project_tools": "أدوات مشاريع",
    "investor_platforms": "منصات المستثمرين",
    "course_creation": "إنشاء دورات",
    "course_publishing": "نشر الدورات",
    "link_shorteners": "مقصر الروابط",
    "document_templates": "قوالب المستندات",
    "study_programming": "دراسة البرمجة",
    "program_projects": "مشاريع برمجة",
    "solve_programming_problems": "حل مشاكل برمجة",
    "website_development": "تطوير المواقع",
    "seo_tools": "أدوات SEO",
    "no_code_website_builders": "مواقع بدون كود",
    "app_development": "تطوير التطبيقات",
    "no_code_app_builders": "تطبيقات بدون كود",
    "advanced_programming_tools": "أدوات برمجة متقدمة",
    "github_tools": "أدوات جيثب",
    "qa_testing": "اختبار الجودة",
    "music_download": "تحميل الموسيقى",
    "sound_search": "بحث الصوت",
    "sound_editing": "تعديل الصوت",
    "text_to_speech": "نص إلى كلام",
    "media_and_images": "وسائط وصور",
    "messaging_and_communication": "الرسائل والتواصل",
    "downloads_and_content": "التحميل والمحتوى",
    "education_and_resources": "التعليم والموارد",
    "security_and_privacy": "الأمان والخصوصية",
    "crypto_and_forex_trading": "تداول العملات",
    "nft_platforms": "منصات NFT",
    "nft_games": "ألعاب NFT",
    "general_tools": "أدوات عامة",
    "study_and_courses": "الدراسة والدورات",
    "research_tools": "أدوات البحث",
    "presentation_tools": "أدوات العروض",
    "cv_and_job_tools": "أدوات السيرة والوظائف",
    "free_books": "كتب مجانية",
    "free_article_sources": "مصادر مقالات مجانية",
    "ai_article_generation": "توليد مقالات",
    "ai_writing_tools": "أدوات كتابة",
    "article_writing_tools": "أدوات مقالات",
    "email_writing_tools": "أدوات إيميلات",
    "paid_article_writing": "مقالات مدفوعة",
    "video_download": "تحميل الفيديو",
    "video_editing": "تحرير الفيديو",
    "motion_videos": "فيديوهات متحركة",
    "video_montage": "مونتاج الفيديو",
    "animated_video_icons": "أيقونات فيديو متحركة",
    # إضافة التصنيفات الفرعية لـ marketing
    "study_marketing": "دراسة التسويق",
    "content_ideas": "أفكار المحتوى",
    "competitor_analysis": "تحليل المنافسين",
    "data_collection": "جمع البيانات",
    "audience_insights": "رؤى الجمهور",
    "marketing_platforms": "منصات التسويق",
    "response_tools": "أدوات الاستجابة",
    "task_management": "إدارة المهام",
    "content_writing": "كتابة المحتوى",
    "content_analysis": "تحليل المحتوى",
    "ad_design": "تصميم الإعلانات",
    "video_design_pros": "محترفو تصميم الفيديو",
    "video_recording": "تسجيل الفيديو",
    "ready_ad_templates": "قوالب إعلانات جاهزة",
    "ai_content_creation": "إنشاء محتوى بالذكاء الاصطناعي",
    "social_media_analysis": "تحليل وسائل التواصل",
    "ad_performance_analysis": "تحليل أداء الإعلانات",
    "customer_communication": "تواصل العملاء",
    "chatbots": "الشات بوتس",
    "content_publishing": "نشر المحتوى",
    "hashtags": "الهاشتاغات",
    "email_marketing": "التسويق بالإيميل",
    "affiliate_marketing": "التسويق بالعمولة",
    "affiliate_links": "روابط التسويق بالعمولة",
    "link_management": "إدارة الروابط",
    "landing_pages": "صفحات الهبوط",
    "social_media_tools": "أدوات وسائل التواصل",
    "tiktok_optimization": "تحسين تيك توك",
    "social_media_management": "إدارة وسائل التواصل",
    "document_management": "إدارة المستندات",
    "account_trading": "تداول الحسابات",
    "ai_marketing": "التسويق بالذكاء الاصطناعي",
    # التصنيفات الفرعية الجديدة
    "ai_video_generation": "إنشاء فيديو بالذكاء",
    "ai_avatars_and_characters": "شخصيات وأفاتار ذكية",
    "ai_voice_and_music": "الصوت والموسيقى بالذكاء",
    "ai_content_creation": "أدوات صناعة المحتوى",
    "osint_and_people_search": "البحث عن هويات ومعلومات",
    "privacy_tools": "أدوات الخصوصية",
    "link_and_file_scanning": "فحص الروابط والملفات",
    "password_and_identity": "كلمات السر والحماية",
    "email_and_phone_verification": "فحص الإيميلات والأرقام",
    "brand_naming": "تسمية المشاريع",
    "plagiarism_detection": "كشف الاقتباس والسرقة",
    "ai_detection": "كشف نصوص الذكاء الاصطناعي",
    "paraphrasing_tools": "إعادة صياغة النصوص",
    "subtitle_tools": "التفريغ والترجمة الصوتية"
}

# خريطة الترجمة من الإنجليزية إلى العربية للتصنيفات الرئيسية
CATEGORY_TRANSLATION = {
    "artificial_intelligence": "الذكاء الاصطناعي",
    "chrome_extensions": "إضافات الكروم",
    "computer_and_technology": "الحاسوب والتكنولوجيا",
    "cybersecurity": "الأمن السيبراني",
    "design": "التصميم",
    "ecommerce": "التجارة الإلكترونية",
    "english_learning": "تعلم الإنجليزية",
    "lifestyle_and_health": "الصحة ونمط الحياة",
    "online_shopping": "التسوق الإلكتروني",
    "miscellaneous_useful_sites": "مواقع مفيدة أخرى",
    "online_work": "العمل عبر الإنترنت",
    "programming": "البرمجة",
    "sound": "الصوتيات",
    "telegram_bots": "بوتات التلغرام",
    "trading_and_cryptocurrencies": "تداول العملات",
    "university_tools": "أدوات الجامعة",
    "video": "الفيديو",
    "writing_and_articles": "الكتابة والمقالات",
    "marketing": "التسويق"
}

# دالة لتطبيع النصوص العربية
def normalize_arabic(text: str) -> str:
    """
    تطبيع النصوص العربية مع الحفاظ على الروابط.
    
    Args:
        text (str): النص المراد تطبيعه.
    
    Returns:
        str: النص المطبع بعد المعالجة.
    """
    if not isinstance(text, str):
        return ""
    # إعادة تشكيل النصوص العربية
    text = arabic_reshaper.reshape(text)
    text = get_display(text)
    # إزالة التشكيلات فقط من النصوص العربية، مع الحفاظ على الروابط
    text = re.sub(r'[ًٌٍَُِّْ]', '', text)
    # تطبيع النص مع الحفاظ على الروابط
    return text.strip().lower()

# دالة لتحميل البيانات من Supabase (بنفس البنية القديمة للتوافق)
def load_site_data(file_path: str = None) -> dict:
    """
    تحميل البيانات من Supabase بنفس بنية ملف JSON الأصلي.
    
    Args:
        file_path: غير مستخدم (موجود للتوافق مع الكود القديم).
    
    Returns:
        dict: البيانات بنفس بنية {"main_categories": {...}}
    """
    try:
        return fetch_sites_as_nested_dict()
    except Exception as e:
        logger.error(f"خطأ في تحميل البيانات من Supabase: {e}")
        return {"main_categories": {}}

# دالة لإضافة موقع جديد (مع منع التكرار)
def add_new_site(main_category_en: str, sub_category_en: str, website: str, description: str, benefit: str = "") -> bool:
    """
    إضافة موقع جديد إلى Supabase مع منع التكرار.
    
    Args:
        main_category_en (str): التصنيف الرئيسي بالإنجليزية.
        sub_category_en (str): التصنيف الفرعي بالإنجليزية (قد يكون فارغًا).
        website (str): اسم الموقع أو الرابط.
        description (str): وصف الموقع.
        benefit (str): فائدة الموقع (اختياري).
    
    Returns:
        bool: True إذا تمت الإضافة بنجاح، False إذا فشلت.
    """
    sub_cat_key = sub_category_en if sub_category_en else "no_sub_category"
    return add_site(main_category_en, sub_cat_key, website, description, benefit)

# دالة لتعديل موقع موجود
def edit_site(main_category_en: str, sub_category_en: str, old_website: str, new_website: str, new_description: str, new_benefit: str) -> bool:
    """
    تعديل موقع موجود في Supabase.
    
    Args:
        main_category_en (str): التصنيف الرئيسي بالإنجليزية.
        sub_category_en (str): التصنيف الفرعي بالإنجليزية.
        old_website (str): اسم الموقع القديم.
        new_website (str): اسم الموقع الجديد.
        new_description (str): الوصف الجديد.
        new_benefit (str): الفائدة الجديدة.
    
    Returns:
        bool: True إذا تم التعديل بنجاح، False إذا لم يتم العثور على الموقع.
    """
    sub_cat_key = sub_category_en if sub_category_en else "no_sub_category"
    return update_site(main_category_en, sub_cat_key, old_website, new_website, new_description, new_benefit)

# دالة لحذف موقع
def delete_site(main_category_en: str, sub_category_en: str, website: str) -> bool:
    """
    حذف موقع من Supabase.
    
    Args:
        main_category_en (str): التصنيف الرئيسي بالإنجليزية.
        sub_category_en (str): التصنيف الفرعي بالإنجليزية.
        website (str): اسم الموقع المراد حذفه.
    
    Returns:
        bool: True إذا تم الحذف بنجاح، False إذا لم يتم العثور على الموقع.
    """
    sub_cat_key = sub_category_en if sub_category_en else "no_sub_category"
    return remove_site(main_category_en, sub_cat_key, website)

# دالة لفهرسة البيانات لتحسين البحث
def index_data() -> list:
    """
    فهرسة البيانات من Supabase لتحسين أداء البحث.
    
    Returns:
        list: قائمة تحتوي على عناصر مفهرسة تحتوي على النصوص والمعلومات المرتبطة.
    """
    sites = fetch_all_sites()
    indexed_data = []
    
    for site in sites:
        main_cat_en = site.get('main_category', '')
        sub_cat_en = site.get('sub_category', '')
        main_cat_ar = CATEGORY_TRANSLATION.get(main_cat_en, main_cat_en)
        sub_cat_ar = SUB_CATEGORY_TRANSLATION.get(sub_cat_en, sub_cat_en)
        
        website = site.get('website', '')
        description = site.get('description', '')
        benefit = site.get('benefit', '')
        
        indexed_data.append({
            'website': website,
            'description': description,
            'benefit': benefit,
            'main_category_en': main_cat_en,
            'main_category_ar': main_cat_ar,
            'sub_category_en': sub_cat_en,
            'sub_category_ar': sub_cat_ar,
            'search_text': f"{website} {description} {benefit}".lower()
        })
    
    return indexed_data

# دالة البحث الذكي المحسنة
def smart_search(term: str, indexed_data: list) -> list:
    """
    البحث الذكي المحسن — سريع وفعال.
    
    1. بحث نصي مباشر (أسرع) — يبحث في النص الكامل
    2. بحث تقريبي (أبطأ) — فقط إذا لم يُعثر على نتائج كافية
    
    Args:
        term (str): مصطلح البحث.
        indexed_data (list): البيانات المفهرسة.
    
    Returns:
        list: قائمة بالنتائج المطابقة مرتبة حسب الدقة والأحدث.
    """
    if not term:
        return []
    
    term_lower = term.strip().lower()
    # إزالة التشكيلات العربية فقط
    term_clean = re.sub(r'[ًٌٍَُِّْ]', '', term_lower)
    
    results = []
    fuzzy_candidates = []
    
    for i, item in enumerate(indexed_data):
        search_text = item['search_text']  # مبني مسبقاً في index_data()
        website_lower = item['website'].lower()
        desc_lower = item['description'].lower()
        benefit_lower = item['benefit'].lower() if item['benefit'] else ''
        
        # --- المرحلة 1: بحث نصي مباشر (سريع جداً) ---
        score = 0
        exact_match = False
        
        if website_lower.startswith(term_clean):
            exact_match = True
            score = 150  # أعلى أولوية — الموقع يبدأ بالكلمة بالضبط
        elif term_clean in website_lower:
            exact_match = True
            score = 120  # أولوية ثانية — مطابقة في اسم الموقع
        elif term_clean in desc_lower:
            exact_match = True
            score = 100  # مطابقة في الوصف
        elif term_clean in benefit_lower:
            exact_match = True
            score = 90   # مطابقة في الفائدة
        elif term_clean in search_text:
            exact_match = True
            score = 80
        
        if exact_match:
            results.append({
                'score': score,
                'exact_match': True,
                'index': i,
                'website': item['website'],
                'description': item['description'],
                'benefit': item['benefit'],
                'main_category_en': item['main_category_en'],
                'main_category_ar': item['main_category_ar'],
                'sub_category_en': item['sub_category_en'],
                'sub_category_ar': item['sub_category_ar']
            })
        else:
            fuzzy_candidates.append((i, item))
    
    # --- المرحلة 2: بحث تقريبي (فقط إذا النتائج قليلة) ---
    if len(results) < 5 and len(term_clean) >= 3:
        for i, item in fuzzy_candidates:
            # بحث تقريبي فقط في الوصف والفائدة (ليس الروابط)
            text = f"{item['description']} {item['benefit']}".lower()
            score = fuzz.partial_ratio(term_clean, text)
            if score >= 85:
                results.append({
                    'score': score,
                    'exact_match': False,
                    'index': i,
                    'website': item['website'],
                    'description': item['description'],
                    'benefit': item['benefit'],
                    'main_category_en': item['main_category_en'],
                    'main_category_ar': item['main_category_ar'],
                    'sub_category_en': item['sub_category_en'],
                    'sub_category_ar': item['sub_category_ar']
                })
            # نكتفي بعد الوصول لـ 5 نتائج
            if len(results) >= 5:
                break
    
    # الترتيب: 1- الأطابق التام (True)، 2- السكور (الأعلى)، 3- الأحدث إضافة (index أعلى)
    results.sort(key=lambda x: (-x['exact_match'], -x['score'], -x['index']))
    return results[:5]