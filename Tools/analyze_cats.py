"""
تحليل شامل لكل المواقع وتحديد التصنيفات الخاطئة والمقترحة
"""
import json

with open('site_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Keywords for classification
RECLASSIFY_RULES = {
    # AI content creation (from ai_bots_and_tools or other)
    "ai_content_creation": {
        "keywords": ["صناعة محتوى", "إنشاء محتوى", "كتابة محتوى", "content creation", "content generat"],
        "desc_keywords": ["محتوى بالذكاء", "إنشاء محتوى", "صناعة محتوى"],
    },
    # AI voice/music (from ai_bots_and_tools or sound)
    "ai_voice_and_music": {
        "keywords": ["صوت", "موسيقى", "voice", "music", "speech", "clone", "استنساخ"],
        "desc_keywords": ["تحويل صوت", "استنساخ صوت", "توليد صوت", "موسيقى بالذكاء", "voice clone", "music ai"],
    },
    # AI avatars
    "ai_avatars_and_characters": {
        "keywords": ["avatar", "أفاتار", "شخصية", "character", "deepfake"],
        "desc_keywords": ["أفاتار", "شخصية افتراضية", "avatar", "talking head", "وجه", "شخصية ذك"],
    },
    # Password/identity
    "password_and_identity": {
        "keywords": ["كلمة سر", "password", "كلمات السر", "هوية"],
        "desc_keywords": ["كلمات السر", "password", "كلمة مرور", "حفظ كلمة", "خزنة"],
    },
    # Link/file scanning
    "link_and_file_scanning": {
        "keywords": ["فحص", "scan", "check"],
        "desc_keywords": ["فحص رابط", "فحص ملف", "فحص موقع", "scan", "فحص أي رابط", "فحص مصداقية"],
    },
    # OSINT / people search
    "osint_and_people_search": {
        "keywords": ["بحث عن شخص", "search person", "osint"],
        "desc_keywords": ["البحث عن أي شخص", "البحث عن شخص", "معرفة صاحب", "تتبع"],
    },
    # Privacy tools
    "privacy_tools": {
        "keywords": ["vpn", "خصوصية", "privacy", "مؤقت", "temp"],
        "desc_keywords": ["vpn", "رقم مؤقت", "إيميل مؤقت", "temp", "مجهول", "anonymous", "خصوصية"],
    },
    # Email/phone verification
    "email_and_phone_verification": {
        "keywords": ["فحص إيميل", "email check", "verify"],
        "desc_keywords": ["فحص الإيميل", "فحص إيميل", "email verify", "التحقق من", "breach"],
    },
    # Brand naming
    "brand_naming": {
        "keywords": ["اسم مشروع", "نطاق", "domain", "يوزرنيم"],
        "desc_keywords": ["اسم للمشروع", "اسم المشروع", "حجز اسم", "اسم تجاري", "username", "يوزرنيم", "اسم موحد"],
    },
    # Plagiarism
    "plagiarism_detection": {
        "keywords": ["اقتباس", "سرقة أدبية", "plagiarism"],
        "desc_keywords": ["نسبة الاقتباس", "سرقة أدبية", "plagiarism", "نسبة السرقة"],
    },
    # AI detection
    "ai_detection": {
        "keywords": ["كشف ذكاء", "ai detect", "غش"],
        "desc_keywords": ["نسبة الغش", "كشف الذكاء", "ai detect", "تحويله لكتابة بشرية", "كشف وجود عمل الذكاء"],
    },
    # Paraphrasing
    "paraphrasing_tools": {
        "keywords": ["إعادة صياغة", "paraphras", "rewrite"],
        "desc_keywords": ["إعادة صياغة", "نص جديد", "كلمات جديدة", "paraphras", "rewrite"],
    },
    # Subtitle tools
    "subtitle_tools": {
        "keywords": ["ترجمة فيديو", "subtitle", "تفريغ"],
        "desc_keywords": ["ترجمة فيديو", "subtitle", "تفريغ", "transcri"],
    },
    # AI video generation
    "ai_video_generation": {
        "keywords": ["إنشاء فيديو", "text to video", "video generat"],
        "desc_keywords": ["إنشاء فيديو", "فيديو بالذكاء", "نص إلى فيديو", "text to video", "video generat"],
    },
}

# Collect ALL sites
all_sites = []
for main_cat, content in data['main_categories'].items():
    for sub_cat, sites in content.get('sub_categories', {}).items():
        if not isinstance(sites, list):
            continue
        for site in sites:
            if isinstance(site, dict):
                all_sites.append({
                    "website": site.get("website", ""),
                    "description": site.get("description", ""),
                    "benefit": site.get("benefit", ""),
                    "current_main": main_cat,
                    "current_sub": sub_cat,
                })

# Analyze each site
reclassifications = []
for site in all_sites:
    desc_lower = site["description"].lower()
    benefit_lower = site["benefit"].lower() if site["benefit"] else ""
    combined = f"{desc_lower} {benefit_lower}"
    
    for new_sub, rules in RECLASSIFY_RULES.items():
        for kw in rules["desc_keywords"]:
            if kw.lower() in combined:
                # Check if it's not already in the right place
                if site["current_sub"] != new_sub:
                    reclassifications.append({
                        "website": site["website"],
                        "description": site["description"][:80],
                        "current": f"{site['current_main']}/{site['current_sub']}",
                        "suggested_sub": new_sub,
                    })
                break

# Print results grouped by suggested new subcategory
from collections import defaultdict
grouped = defaultdict(list)
for r in reclassifications:
    grouped[r["suggested_sub"]].append(r)

for sub, items in sorted(grouped.items()):
    print(f"\n{'='*60}")
    print(f"📁 {sub} ({len(items)} مواقع مرشحة)")
    print(f"{'='*60}")
    for item in items:
        print(f"  🔗 {item['website']}")
        print(f"     📝 {item['description']}")
        print(f"     📂 حالياً: {item['current']}")
        print()

print(f"\n\n📊 ملخص:")
print(f"  إجمالي المواقع: {len(all_sites)}")
print(f"  مواقع مرشحة لإعادة التصنيف: {len(reclassifications)}")
for sub, items in sorted(grouped.items()):
    print(f"  - {sub}: {len(items)}")
