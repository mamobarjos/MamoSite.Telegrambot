"""
reclassify_sites.py - إعادة تصنيف المواقع في Supabase
ينقل المواقع للتصنيفات الفرعية الجديدة بدون تغيير الوصف أو الفائدة
"""
import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

# قائمة المواقع المراد نقلها: (website_pattern, from_main, from_sub, to_main, to_sub)
MOVES = [
    # === ai_video_generation (في artificial_intelligence) ===
    ("sora.com", "artificial_intelligence", "ai_video_image_editing", "artificial_intelligence", "ai_video_generation"),
    ("hailuoai.video", "artificial_intelligence", "ai_video_image_editing", "artificial_intelligence", "ai_video_generation"),
    ("lumalabs.ai", "artificial_intelligence", "ai_video_image_editing", "artificial_intelligence", "ai_video_generation"),
    ("klingai.com", "artificial_intelligence", "ai_video_image_editing", "artificial_intelligence", "ai_video_generation"),
    ("app.pixverse", "artificial_intelligence", "ai_video_image_editing", "artificial_intelligence", "ai_video_generation"),
    ("deepmind.google/technologies/veo", "artificial_intelligence", "ai_video_image_editing", "artificial_intelligence", "ai_video_generation"),
    ("runwayml.com", "artificial_intelligence", "ai_bots_and_tools", "artificial_intelligence", "ai_video_generation"),
    ("invideo.io", "artificial_intelligence", "ai_bots_and_tools", "artificial_intelligence", "ai_video_generation"),
    ("lumen5.com", "marketing", "video_design_pros", "artificial_intelligence", "ai_video_generation"),
    ("synthesia.io", "marketing", "video_design_pros", "artificial_intelligence", "ai_video_generation"),
    ("fliki.ai", "sound", "text_to_speech", "artificial_intelligence", "ai_video_generation"),
    ("labs.google/fx/ar/tools/flow", "artificial_intelligence", "ai_video_image_editing", "artificial_intelligence", "ai_video_generation"),

    # === ai_avatars_and_characters (في artificial_intelligence) ===
    ("d-id.com", "artificial_intelligence", "ai_bots_and_tools", "artificial_intelligence", "ai_avatars_and_characters"),
    ("heygen.com", "artificial_intelligence", "ai_bots_and_tools", "artificial_intelligence", "ai_avatars_and_characters"),
    ("elai.io", "artificial_intelligence", "ai_bots_and_tools", "artificial_intelligence", "ai_avatars_and_characters"),
    ("character.ai", "artificial_intelligence", "ai_bots_and_tools", "artificial_intelligence", "ai_avatars_and_characters"),
    ("freepik.com/pikaso/ai-image-generator?create=character", "design", "text_to_image", "artificial_intelligence", "ai_avatars_and_characters"),

    # === ai_voice_and_music (في artificial_intelligence) ===
    ("elevenlabs.io", "artificial_intelligence", "ai_bots_and_tools", "artificial_intelligence", "ai_voice_and_music"),
    ("murf.ai", "sound", "text_to_speech", "artificial_intelligence", "ai_voice_and_music"),
    ("suno.com", "artificial_intelligence", "ai_bots_and_tools", "artificial_intelligence", "ai_voice_and_music"),
    ("udio.com", "artificial_intelligence", "ai_bots_and_tools", "artificial_intelligence", "ai_voice_and_music"),
    ("soundraw.io", "sound", "music_download", "artificial_intelligence", "ai_voice_and_music"),

    # === osint_and_people_search (في cybersecurity) ===
    ("social-searcher.com", "cybersecurity", "cybersecurity_tools", "cybersecurity", "osint_and_people_search"),
    ("candidatechecker.io", "cybersecurity", "cybersecurity_tools", "cybersecurity", "osint_and_people_search"),
    ("epieos.com", "cybersecurity", "cybersecurity_tools", "cybersecurity", "osint_and_people_search"),
    ("maltego.com", "cybersecurity", "cybersecurity_tools", "cybersecurity", "osint_and_people_search"),
    ("numlookup.com", "cybersecurity", "cybersecurity_tools", "cybersecurity", "osint_and_people_search"),
    ("pipl.com", "cybersecurity", "cybersecurity_tools", "cybersecurity", "osint_and_people_search"),
    ("shodan.io", "cybersecurity", "cybersecurity_tools", "cybersecurity", "osint_and_people_search"),

    # === privacy_tools (في cybersecurity) ===
    ("temp-mail.org", "cybersecurity", "cybersecurity_tools", "cybersecurity", "privacy_tools"),
    ("bugmenot.com", "cybersecurity", "cybersecurity_tools", "cybersecurity", "privacy_tools"),
    ("afreesms.com", "cybersecurity", "cybersecurity_tools", "cybersecurity", "privacy_tools"),
    ("anonymousemail.me", "cybersecurity", "cybersecurity_tools", "cybersecurity", "privacy_tools"),
    ("tails.net", "cybersecurity", "cybersecurity_tools", "cybersecurity", "privacy_tools"),
    ("console.twilio.com", "cybersecurity", "cybersecurity_tools", "cybersecurity", "privacy_tools"),
    ("temp-number.com", "miscellaneous_useful_sites", "miscellaneous_tools", "cybersecurity", "privacy_tools"),

    # === link_and_file_scanning (في cybersecurity) ===
    ("scamadviser.com", "cybersecurity", "cybersecurity_tools", "cybersecurity", "link_and_file_scanning"),
    ("psafe.com", "cybersecurity", "cybersecurity_tools", "cybersecurity", "link_and_file_scanning"),
    ("filescan.io", "cybersecurity", "cybersecurity_tools", "cybersecurity", "link_and_file_scanning"),
    ("transparencyreport.google.com", "cybersecurity", "cybersecurity_tools", "cybersecurity", "link_and_file_scanning"),
    ("virustotal.com", "cybersecurity", "cybersecurity_tools", "cybersecurity", "link_and_file_scanning"),

    # === password_and_identity (في cybersecurity) ===
    ("security.org", "cybersecurity", "cybersecurity_tools", "cybersecurity", "password_and_identity"),
    ("keepersecurity.com", "cybersecurity", "cybersecurity_tools", "cybersecurity", "password_and_identity"),
    ("hashcat.net", "cybersecurity", "linux_tools", "cybersecurity", "password_and_identity"),
    ("kali.org/tools/john", "cybersecurity", "linux_tools", "cybersecurity", "password_and_identity"),

    # === email_and_phone_verification (في cybersecurity) ===
    ("haveibeenpwned.com", "cybersecurity", "cybersecurity_tools", "cybersecurity", "email_and_phone_verification"),
    ("emailrep.io", "cybersecurity", "cybersecurity_tools", "cybersecurity", "email_and_phone_verification"),
    ("hunter.io", "cybersecurity", "cybersecurity_tools", "cybersecurity", "email_and_phone_verification"),

    # === brand_naming (في ecommerce) ===
    ("analyzeid.com", "ecommerce", "store_creation", "ecommerce", "brand_naming"),
    ("namecheckr.com", "ecommerce", "store_creation", "ecommerce", "brand_naming"),
    ("biznamewiz.com", "ecommerce", "store_creation", "ecommerce", "brand_naming"),
    ("namy.ai", "ecommerce", "store_creation", "ecommerce", "brand_naming"),
    ("namelix.com", "ecommerce", "store_creation", "ecommerce", "brand_naming"),

    # === plagiarism_detection (في university_tools) ===
    ("prepostseo.com", "university_tools", "general_tools", "university_tools", "plagiarism_detection"),
    ("plagiarismdetector.net", "university_tools", "general_tools", "university_tools", "plagiarism_detection"),
    ("plag.ai", "university_tools", "general_tools", "university_tools", "plagiarism_detection"),
    ("copyleaks.com", "university_tools", "general_tools", "university_tools", "plagiarism_detection"),

    # === ai_detection (في university_tools) ===
    ("gptzero.me", "university_tools", "general_tools", "university_tools", "ai_detection"),
    ("justdone.ai", "university_tools", "general_tools", "university_tools", "ai_detection"),

    # === paraphrasing_tools (في university_tools) ===
    ("speedwrite.com", "university_tools", "general_tools", "university_tools", "paraphrasing_tools"),
    ("quillbot.com", "university_tools", "general_tools", "university_tools", "paraphrasing_tools"),
    ("rewritify.ai", "writing_and_articles", "ai_article_generation", "university_tools", "paraphrasing_tools"),
    ("spinbot.com", "writing_and_articles", "article_writing_tools", "university_tools", "paraphrasing_tools"),

    # === subtitle_tools (في video) ===
    ("notta.ai", "university_tools", "study_and_courses", "video", "subtitle_tools"),
    ("almufaragh.com", "computer_and_technology", "tech_tools", "video", "subtitle_tools"),
    ("deepl.com", "online_work", "online_jobs", "video", "subtitle_tools"),
]

def run_reclassification():
    moved = 0
    not_found = 0
    errors = 0
    flagged = []

    print("🔄 بدء إعادة التصنيف...\n")

    for website_part, from_main, from_sub, to_main, to_sub in MOVES:
        try:
            # البحث عن الموقع - يحتوي على website_part
            result = client.table("sites").select("*").eq(
                "main_category", from_main
            ).eq(
                "sub_category", from_sub
            ).ilike(
                "website", f"%{website_part}%"
            ).execute()

            if not result.data:
                not_found += 1
                print(f"  ⚠️ لم يُعثر على: {website_part} في {from_main}/{from_sub}")
                continue

            for site in result.data:
                # نقل الموقع
                client.table("sites").update({
                    "main_category": to_main,
                    "sub_category": to_sub
                }).eq("id", site["id"]).execute()

                moved += 1
                print(f"  ✅ {site['website']}")
                print(f"     {from_main}/{from_sub} → {to_main}/{to_sub}")

        except Exception as e:
            errors += 1
            print(f"  ❌ خطأ في {website_part}: {e}")

    print(f"\n{'='*50}")
    print(f"📊 النتائج:")
    print(f"  ✅ تم نقل: {moved} موقع")
    print(f"  ⚠️ لم يُعثر على: {not_found}")
    print(f"  ❌ أخطاء: {errors}")
    print(f"{'='*50}")

    # التحقق من التوزيع الجديد
    print("\n📊 التوزيع بعد إعادة التصنيف:")
    for new_sub in ["ai_video_generation", "ai_avatars_and_characters", "ai_voice_and_music",
                     "osint_and_people_search", "privacy_tools", "link_and_file_scanning",
                     "password_and_identity", "email_and_phone_verification", "brand_naming",
                     "plagiarism_detection", "ai_detection", "paraphrasing_tools", "subtitle_tools"]:
        count = client.table("sites").select("id", count="exact").eq("sub_category", new_sub).execute()
        print(f"  {new_sub}: {count.count} مواقع")

if __name__ == '__main__':
    run_reclassification()
