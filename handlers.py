import logging
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
import pandas as pd
from data import (
    CATEGORIES,
    SUB_CATEGORY_TRANSLATION,
    CATEGORY_TRANSLATION,
    normalize_arabic,
    load_site_data,
    add_new_site,
    edit_site,
    delete_site,
    smart_search,
    index_data,
)
from db import check_duplicate, is_admin, add_admin, fetch_all_admins
from config import SUPABASE_URL, ADMIN_PASSWORD
from telegram.ext import ApplicationHandlerStop

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- التحقق الأمني (Middleware) ---
async def auth_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    
    if update.message and update.message.text and update.message.text.startswith('/login'):
        return
        
    if not is_admin(user_id):
        if update.message:
            await update.message.reply_text("⛔ عذراً، هذا البوت مخصص للإدارة المركزية فقط.\n\nإذا كنت مسؤولاً، يرجى إرسال أمر الدخول بالشكل التالي:\n`/login PASSWORD`", parse_mode='Markdown')
        raise ApplicationHandlerStop()

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ يرجى إدخال كلمة المرور مع الأمر، مثال:\n`/login 123456`")
        return
        
    if args[0] == ADMIN_PASSWORD:
        user_id = update.effective_user.id
        name = update.effective_user.first_name or "Admin"
        if add_admin(user_id, name):
            await update.message.reply_text("✅ تم التحقق بنجاح! أنت الآن مدير معتمد.\n\nاضغط /start لفتح لوحة التحكم.")
        else:
            await update.message.reply_text("⚠️ حدث خطأ أثناء التسجيل.")
    else:
        await update.message.reply_text("❌ كلمة المرور غير صحيحة.")

# تعريف حالات المحادثة
NAME, DESCRIPTION, BENEFIT, MAIN_CATEGORY, SUB_CATEGORY, CONFIRM, SEARCH, VIEW_RESULT, EDIT_NAME, EDIT_DESCRIPTION, EDIT_BENEFIT, EXPORT_MENU, EXPORT_SMART_SEARCH, EXPORT_MAIN_CAT_SELECT, EXPORT_SUB_CAT_SELECT = range(15)


# دالة لبناء لوحة مفاتيح تفاعلية للتصنيفات الفرعية
def build_keyboard(options, row_size=2):
    keyboard = [
        [InlineKeyboardButton(SUB_CATEGORY_TRANSLATION.get(opt, opt), callback_data=opt) for opt in options[i:i + row_size]]
        for i in range(0, len(options), row_size)
    ]
    return InlineKeyboardMarkup(keyboard)

# دالة لبناء لوحة مفاتيح تفاعلية للتصنيفات الرئيسية
def build_main_category_keyboard(options, row_size=2):
    keyboard = [
        [InlineKeyboardButton(CATEGORY_TRANSLATION.get(opt, opt), callback_data=opt) for opt in options[i:i + row_size]]
        for i in range(0, len(options), row_size)
    ]
    return InlineKeyboardMarkup(keyboard)

# إنشاء لوحة المفاتيح التفاعلية
start_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("ابدأ الآن ▶️", callback_data='start')],
    [InlineKeyboardButton("تصدير البيانات 📤", callback_data='export_data')],
    [InlineKeyboardButton("البحث 🔍", callback_data='search')]
])

confirm_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("نعم", callback_data='yes'), InlineKeyboardButton("لا", callback_data='no')]
])

# لوحة مفاتيح لعرض النتائج
def result_options_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("رجوع ⬅️", callback_data='back_to_results'),
            InlineKeyboardButton("تعديل ✏️", callback_data='edit_result'),
            InlineKeyboardButton("حذف 🗑️", callback_data='delete_result')
        ],
        [
            InlineKeyboardButton("🔍 بحث جديد", callback_data='search'),
            InlineKeyboardButton("🏠 القائمة", callback_data='main_menu')
        ]
    ])

# دالة إلغاء المحادثة
async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚫 تم إلغاء العملية.")
    context.user_data.clear()
    return ConversationHandler.END

# ---# --- معالجات الأوامر ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    logger.info(f"بدء المحادثة مع المستخدم {update.effective_user.id}")
    
    from db import fetch_pending_suggestions
    suggestions = fetch_pending_suggestions()
    count = len(suggestions)
    
    keyboard = []
    if count > 0:
        keyboard.append([InlineKeyboardButton(f"📩 مراجعة الاقتراحات ({count})", callback_data='review_suggestions')])
    
    keyboard.extend([
        [InlineKeyboardButton("ابدأ إضافة موقع ▶️", callback_data='start_add')],
        [InlineKeyboardButton("تصدير البيانات 📤", callback_data='export_data')],
        [InlineKeyboardButton("البحث 🔍", callback_data='search')]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text("اختر أحد الخيارات:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("اختر أحد الخيارات:", reply_markup=reply_markup)
    return NAME

# --- معالجة النقر على الزر ---
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    logger.info(f"استقبال callback_query: {query.data} من المستخدم {update.effective_user.id}")
    await query.answer()
    logger.info(f"تم النقر على الزر: {query.data} بواسطة المستخدم {update.effective_user.id}")

    # إضافة تأخير بسيط لتجنب حدود Telegram API
    await asyncio.sleep(0.5)

    if query.data == 'start_add':
        context.user_data.clear()
        await query.edit_message_text("📝 اسم الموقع أو الرابط:")
        return NAME
    elif query.data == 'main_menu':
        context.user_data.clear()
        return await start(update, context)
        
    # --- قسم الاقتراحات ---
    elif query.data == 'review_suggestions':
        from db import fetch_pending_suggestions, update_suggestion_status
        suggestions = fetch_pending_suggestions()
        if not suggestions:
            await query.answer("لا يوجد اقتراحات حالياً", show_alert=True)
            return await start(update, context)
            
        sug = suggestions[0]
        text = (f"📩 اقتراح جديد:\n\n"
                f"🌐 الموقع: {sug.get('website', '')}\n"
                f"📂 التصنيفات المقترحة: {sug.get('main_category', '')} > {sug.get('sub_category', 'غير محدد')}\n"
                f"📝 الوصف: {sug.get('description', '')}\n"
                f"💡 الفائدة: {sug.get('benefit', 'لا يوجد')}")
                
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ موافقة وتسكين", callback_data=f"app_{sug['id']}"),
             InlineKeyboardButton("❌ تعليق/رفض", callback_data=f"rej_{sug['id']}")],
            [InlineKeyboardButton("تخطي ➡️", callback_data=f"skip_sug"),
             InlineKeyboardButton("رجوع ⬅️", callback_data='main_menu')]
        ])
        await query.edit_message_text(text, reply_markup=keyboard)
        return NAME

    elif query.data.startswith("app_"):
        from db import fetch_pending_suggestions, update_suggestion_status, add_site
        from data import CATEGORY_TRANSLATION, SUB_CATEGORY_TRANSLATION
        
        sug_id = query.data.split("_")[1]
        suggestions = fetch_pending_suggestions()
        sug = next((s for s in suggestions if str(s['id']) == sug_id), None)
        if not sug:
            await query.answer("لم يتم العثور على الاقتراح")
            return await start(update, context)
            
        def get_en_key(ar_val, mapping):
            for k, v in mapping.items():
                if v == ar_val: return k
            return ""
            
        main_en = get_en_key(sug.get('main_category', ''), CATEGORY_TRANSLATION)
        sub_en = get_en_key(sug.get('sub_category', ''), SUB_CATEGORY_TRANSLATION)
        
        update_suggestion_status(sug_id, "approved")
        
        if main_en and sub_en:
            add_site(
                main_category_en=main_en,
                sub_category_en=sub_en,
                website=sug.get('website', ''),
                description=sug.get('description', ''),
                benefit=sug.get('benefit', '')
            )
            await query.answer("✅ تم قبول وإضافة الموقع مباشرة للفرع المحدد!", show_alert=True)
            query.data = 'review_suggestions'
            return await handle_button(update, context)
        else:
            context.user_data['name'] = sug.get('website', '')
            context.user_data['description'] = sug.get('description', '')
            context.user_data['benefit'] = sug.get('benefit', '')
            
            options = list(CATEGORIES.keys())
            reply_markup = build_main_category_keyboard(options)
            await query.edit_message_text(f"تم قبول {sug.get('website', '')}!\n\n⚠️ التصنيفات لم تتعرف تلقائياً.\n📂 يرجى اختيار التصنيف الرئيسي لإضافته:", reply_markup=reply_markup)
            return MAIN_CATEGORY

    elif query.data.startswith("rej_"):
        from db import update_suggestion_status
        sug_id = query.data.split("_")[1]
        update_suggestion_status(sug_id, "rejected")
        await query.answer("تم رفض/تعليق الاقتراح")
        query.data = 'review_suggestions' # لمحاكاة الضغط وتجلب الاقتراح التالي
        return await handle_button(update, context)

    elif query.data == "skip_sug":
        return await start(update, context)
    # ----------------------
    elif query.data == 'export_data':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("تصدير الكل (كل المواقع) 📦", callback_data='export_all')],
            [InlineKeyboardButton("فلترة ذكية بكلمة بحث 🔍", callback_data='export_smart')],
            [InlineKeyboardButton("فلترة حسب التصنيف 📂", callback_data='export_category')],
            [InlineKeyboardButton("إلغاء 🚫", callback_data='main_menu')]
        ])
        await query.edit_message_text("📥 خيارات تصدير البيانات:\nاختر كيف تريد استخراج البيانات:", reply_markup=keyboard)
        return EXPORT_MENU
    elif query.data == 'export_all':
        await query.edit_message_text("⏳ جاري تجهيز كل البيانات...")
        data = load_site_data()
        flat_data = []
        for main_cat_en, content in data.get('main_categories', {}).items():
            main_cat_ar = CATEGORY_TRANSLATION.get(main_cat_en, main_cat_en)
            for sub_cat_en, sites in content.get('sub_categories', {}).items():
                sub_cat_ar = SUB_CATEGORY_TRANSLATION.get(sub_cat_en, sub_cat_en)
                for site in sites:
                    flat_data.append({
                        "التصنيف الرئيسي": main_cat_ar,
                        "التصنيف الفرعي": sub_cat_ar,
                        "الموقع": site.get("website", ""),
                        "الوصف": site.get("description", ""),
                        "الفائدة": site.get("benefit", "")
                    })
        await generate_and_send_excel(query.message, flat_data, 'sites_all.xlsx', "✅ تم التصدير الكامل")
        return await start(update, context)
    elif query.data == 'export_smart':
        await query.edit_message_text("✍️ اكتب الكلمة الافتتاحية أو الفائدة التي تبحث عنها (مثال: مونتاج، تصميم، ذكاء اصطناعي):")
        return EXPORT_SMART_SEARCH
    elif query.data == 'export_category':
        main_categories = list(CATEGORIES.keys())
        reply_markup = build_main_category_keyboard(main_categories)
        await query.edit_message_text("📂 اختر التصنيف الرئيسي الذي تريد تصديره:", reply_markup=reply_markup)
        return EXPORT_MAIN_CAT_SELECT
    elif query.data == 'search':
        context.user_data.clear()
        await query.edit_message_text("🔍 اكتب ما تبحث عنه:")
        return SEARCH
    elif query.data.startswith('view_'):
        try:
            index = int(query.data.split('_')[1])
            search_results = context.user_data.get('search_results', [])
            logger.info(f"محاولة عرض النتيجة رقم {index}. عدد النتائج: {len(search_results)}")
            if not search_results:
                logger.error("قائمة search_results فارغة")
                await query.answer("⚠️ النتائج غير متوفرة. حاول البحث مرة أخرى.", show_alert=True)
                return await start(update, context)
            if 0 <= index < len(search_results):
                context.user_data['current_result_index'] = index
                result = search_results[index]
                logger.info(f"عرض النتيجة: {result['website']}")
                await query.edit_message_text(
                    f"📌 النتيجة:\n\n"
                    f"الموقع: {result['website']}\n"
                    f"الوصف: {result['description']}\n"
                    f"الفائدة: {result['benefit']}\n"
                    f"التصنيف الرئيسي: {result['main_category_ar']}\n"
                    f"التصنيف الفرعي: {result['sub_category_ar']}",
                    reply_markup=result_options_keyboard()
                )
            else:
                logger.error(f"الفهرس {index} خارج النطاق")
                await query.answer("⚠️ النتيجة غير موجودة.", show_alert=True)
                return await start(update, context)
        except Exception as e:
            logger.error(f"خطأ أثناء عرض النتيجة: {e}")
            await query.answer("⚠️ حدث خطأ أثناء عرض النتيجة.", show_alert=True)
            return await start(update, context)
    elif query.data == 'back_to_results':
        search_results = context.user_data.get('search_results', [])
        if search_results:
            keyboard = [[InlineKeyboardButton(match['website'], callback_data=f"view_{i}")] for i, match in enumerate(search_results)]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("🔍 اختر النتيجة المطلوبة:", reply_markup=reply_markup)
            return VIEW_RESULT
        else:
            await query.answer("⚠️ لا توجد نتائج.", show_alert=True)
            return await start(update, context)
    elif query.data == 'edit_result':
        await query.edit_message_text("📝 أدخل اسم الموقع الجديد:")
        return EDIT_NAME
    elif query.data == 'delete_result':
        search_results = context.user_data.get('search_results', [])
        index = context.user_data.get('current_result_index', 0)
        if 0 <= index < len(search_results):
            result = search_results[index]
            success = delete_site(
                main_category_en=result['main_category_en'],
                sub_category_en=result['sub_category_en'],
                website=result['website']
            )
            if success:
                search_results.pop(index)
                context.user_data['search_results'] = search_results
                await query.answer("🗑️ تم حذف الموقع بنجاح.", show_alert=True)
                return await start(update, context)
            else:
                await query.answer("⚠️ فشل في حذف الموقع.", show_alert=True)
                return await start(update, context)
    elif query.data == 'continue_add':
        # المتابعة بإضافة موقع مكرر
        await query.edit_message_text("✍️ وصف الموقع:")
        return DESCRIPTION
    elif query.data == 'cancel_add':
        context.user_data.clear()
        await query.answer("🚫 تم الإلغاء.", show_alert=True)
        return await start(update, context)
    return NAME

# --- معالجة اسم الموقع ---
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("⚠️ الرجاء إدخال اسم الموقع أو الرابط:")
        return NAME
    context.user_data['name'] = update.message.text.strip()
    logger.info(f"تم إدخال الاسم: {context.user_data['name']}")

    # فحص التكرار المبكر
    duplicates = check_duplicate(context.user_data['name'])
    if duplicates:
        dup_lines = []
        for dup in duplicates:
            dup_main_ar = CATEGORY_TRANSLATION.get(dup.get('main_category', ''), dup.get('main_category', ''))
            dup_sub_ar = SUB_CATEGORY_TRANSLATION.get(dup.get('sub_category', ''), dup.get('sub_category', ''))
            dup_desc = dup.get('description', '')[:60]
            dup_lines.append(f"📂 {dup_main_ar} > {dup_sub_ar}\n📝 {dup_desc}")

        dup_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ متابعة الإضافة", callback_data='continue_add'),
             InlineKeyboardButton("❌ إلغاء", callback_data='cancel_add')]
        ])
        await update.message.reply_text(
            f"⚠️ هذا الموقع موجود مسبقاً:\n\n"
            + "\n\n".join(dup_lines)
            + "\n\nهل تريد المتابعة وإضافته في تصنيف آخر؟",
            reply_markup=dup_keyboard
        )
        return NAME  # يبقى في نفس الحالة حتى يختار المستخدم

    await update.message.reply_text("✍️ وصف الموقع:")
    return DESCRIPTION

# --- معالجة الوصف ---
async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("⚠️ الرجاء إدخال وصف الموقع:")
        return DESCRIPTION
    context.user_data['description'] = update.message.text.strip()
    logger.info(f"تم إدخال الوصف: {context.user_data['description']}")
    await update.message.reply_text("✍️ اكتب فائدة الموقع:")
    return BENEFIT

# --- معالجة الفائدة ---
async def get_benefit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("⚠️ الرجاء إدخال فائدة الموقع:")
        return BENEFIT
    context.user_data['benefit'] = update.message.text.strip()
    logger.info(f"تم إدخال الفائدة: {context.user_data['benefit']}")
    main_categories = list(CATEGORIES.keys())
    reply_markup = build_main_category_keyboard(main_categories)
    await update.message.reply_text("📂 اختر التصنيف الرئيسي:", reply_markup=reply_markup)
    return MAIN_CATEGORY

# --- استقبال التصنيف الرئيسي ---
async def get_main_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    main_category = query.data
    logger.info(f"تم اختيار التصنيف الرئيسي: {main_category}")

    if main_category not in CATEGORIES:
        await query.answer("⚠️ التصنيف الرئيسي غير موجود.", show_alert=True)
        return await start(update, context)

    context.user_data['main_category'] = main_category
    sub_categories = CATEGORIES.get(main_category, [])
    if sub_categories:
        reply_markup = build_keyboard(sub_categories)
        await query.edit_message_text(f"📂 اختر التصنيف الفرعي لـ {CATEGORY_TRANSLATION.get(main_category, main_category)}:", reply_markup=reply_markup)
        return SUB_CATEGORY
    else:
        context.user_data['sub_category'] = None
        await query.edit_message_text(
            f"✅ البيانات المدخلة:\n\n"
            f"الاسم: {context.user_data['name']}\n"
            f"الوصف: {context.user_data['description']}\n"
            f"الفائدة: {context.user_data['benefit']}\n"
            f"التصنيف الرئيسي: {CATEGORY_TRANSLATION.get(main_category, main_category)}\n"
            "هل تريد حفظها؟",
            reply_markup=confirm_keyboard
        )
        return CONFIRM

# --- استقبال التصنيف الفرعي ---
async def get_sub_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    sub_category_en = query.data
    logger.info(f"تم اختيار التصنيف الفرعي: {sub_category_en}")

    main_category = context.user_data.get('main_category')
    if not main_category or main_category not in CATEGORIES:
        await query.answer("⚠️ التصنيف الرئيسي غير موجود.", show_alert=True)
        return await start(update, context)

    sub_categories = CATEGORIES.get(main_category, [])
    if sub_category_en not in sub_categories and sub_categories:
        await query.answer("⚠️ التصنيف الفرعي غير موجود.", show_alert=True)
        return await start(update, context)

    context.user_data['sub_category'] = sub_category_en
    main_category_ar = CATEGORY_TRANSLATION.get(main_category, main_category)
    sub_category_ar = SUB_CATEGORY_TRANSLATION.get(sub_category_en, sub_category_en)

    await query.edit_message_text(
        f"✅ البيانات المدخلة:\n\n"
        f"الاسم: {context.user_data['name']}\n"
        f"الوصف: {context.user_data['description']}\n"
        f"الفائدة: {context.user_data['benefit']}\n"
        f"التصنيف الرئيسي: {main_category_ar}\n"
        f"التصنيف الفرعي: {sub_category_ar}\n"
        "هل تريد حفظها؟",
        reply_markup=confirm_keyboard
    )
    return CONFIRM

# --- تأكيد الحفظ ---
async def confirm_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_response = query.data
    logger.info(f"تأكيد البيانات: {user_response}")

    required_keys = ['name', 'description', 'benefit', 'main_category']
    if not all(key in context.user_data for key in required_keys):
        await query.answer("⚠️ هناك خطأ في البيانات.", show_alert=True)
        context.user_data.clear()
        return await start(update, context)

    if user_response == 'yes':
        main_category = context.user_data['main_category']
        sub_category = context.user_data.get('sub_category')
        add_new_site(
            main_category_en=main_category,
            sub_category_en=sub_category,
            website=context.user_data['name'],
            description=context.user_data['description'],
            benefit=context.user_data['benefit']
        )
        await query.answer("💾 تم الحفظ بنجاح.", show_alert=True)
        context.user_data.clear()
        return await start(update, context)
    else:
        await query.answer("🚫 تم الإلغاء.", show_alert=True)
        context.user_data.clear()
        return await start(update, context)

# --- تنفيذ البحث ---
async def perform_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("⚠️ الرجاء إدخال نص البحث:")
        return SEARCH

    search_query = update.message.text.strip()
    logger.info(f"تنفيذ البحث عن: {search_query}")

    # رسالة تحميل
    loading_msg = await update.message.reply_text("🔍 جاري البحث...")

    # فهرسة البيانات
    indexed_data = index_data()
    
    # تنفيذ البحث
    matches = smart_search(search_query, indexed_data)
    
    if matches:
        context.user_data['search_results'] = matches
        keyboard = [[InlineKeyboardButton(match['website'], callback_data=f"view_{i}")] for i, match in enumerate(matches)]
        keyboard.append([
            InlineKeyboardButton("🔍 بحث جديد", callback_data='search'),
            InlineKeyboardButton("🏠 القائمة", callback_data='main_menu')
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await loading_msg.edit_text("🔍 اختر النتيجة المطلوبة:", reply_markup=reply_markup)
    else:
        await loading_msg.edit_text("⚠️ لا توجد نتائج.")
    return VIEW_RESULT

# --- معالجة تعديل اسم الموقع ---
async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("⚠️ الرجاء إدخال اسم الموقع الجديد:")
        return EDIT_NAME
    context.user_data['edit_name'] = update.message.text.strip()
    await update.message.reply_text("✍️ أدخل الوصف الجديد:")
    return EDIT_DESCRIPTION

# --- معالجة تعديل الوصف ---
async def edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("⚠️ الرجاء إدخال الوصف الجديد:")
        return EDIT_DESCRIPTION
    context.user_data['edit_description'] = update.message.text.strip()
    await update.message.reply_text("✍️ أدخل الفائدة الجديدة:")
    return EDIT_BENEFIT

# --- معالجة تعديل الفائدة وتأكيد التعديل ---
async def edit_benefit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("⚠️ الرجاء إدخال الفائدة الجديدة:")
        return EDIT_BENEFIT
    context.user_data['edit_benefit'] = update.message.text.strip()

    search_results = context.user_data.get('search_results', [])
    index = context.user_data.get('current_result_index', 0)
    if 0 <= index < len(search_results):
        result = search_results[index]
        success = edit_site(
            main_category_en=result['main_category_en'],
            sub_category_en=result['sub_category_en'],
            old_website=result['website'],
            new_website=context.user_data['edit_name'],
            new_description=context.user_data['edit_description'],
            new_benefit=context.user_data['edit_benefit']
        )
        if success:
            # تحديث النتيجة في القائمة
            result['website'] = context.user_data['edit_name']
            result['description'] = context.user_data['edit_description']
            result['benefit'] = context.user_data['edit_benefit']
            search_results[index] = result
            context.user_data['search_results'] = search_results
            await update.message.reply_text(
                f"📌 النتيجة المعدلة:\n\n"
                f"الموقع: {result['website']}\n"
                f"الوصف: {result['description']}\n"
                f"الفائدة: {result['benefit']}\n"
                f"التصنيف الرئيسي: {result['main_category_ar']}\n"
                f"التصنيف الفرعي: {result['sub_category_ar']}",
                reply_markup=result_options_keyboard()
            )
        else:
            await update.message.reply_text("⚠️ فشل في تعديل الموقع.")
            return await start(update, context)
    return VIEW_RESULT

# --- معالجة التصدير الذكي بالبحث ---
async def handle_export_smart_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("⚠️ الرجاء كتابة الكلمة الافتتاحية للتصدير:")
        return EXPORT_SMART_SEARCH
    
    term = update.message.text.strip()
    loading_msg = await update.message.reply_text(f"🔍 جاري سحب كل المواقع المرتبطة بـ ({term})...")
    
    indexed_data = index_data()
    
    # فلترة كل البيانات (لا نقتصر على 5 نتائج فقط كالبحث العادي)
    term_lower = term.strip().lower()
    import re
    term_clean = re.sub(r'[ًٌٍَُِّْ]', '', term_lower)
    
    flat_data = []
    for item in indexed_data:
        search_text = item['search_text']
        website_lower = item['website'].lower()
        desc_lower = item['description'].lower()
        benefit_lower = item['benefit'].lower() if item['benefit'] else ''
        
        # بحث شامل
        if term_clean in website_lower or term_clean in desc_lower or term_clean in benefit_lower or term_clean in search_text:
            flat_data.append({
                "التصنيف الرئيسي": item['main_category_ar'],
                "التصنيف الفرعي": item['sub_category_ar'],
                "الموقع": item['website'],
                "الوصف": item['description'],
                "الفائدة": item['benefit']
            })
            continue
            
        # إضافة الفلترة التقريبية (Fuzzy) لكن بعتبة عالية للحفاظ على جودة التصدير
        from fuzzywuzzy import fuzz
        text = f"{desc_lower} {benefit_lower}"
        if fuzz.partial_ratio(term_clean, text) >= 85:
             flat_data.append({
                "التصنيف الرئيسي": item['main_category_ar'],
                "التصنيف الفرعي": item['sub_category_ar'],
                "الموقع": item['website'],
                "الوصف": item['description'],
                "الفائدة": item['benefit']
            })

    if not flat_data:
        await loading_msg.edit_text(f"⚠️ لم يتم العثور على أي مواقع تطابق ({term}).", reply_markup=start_keyboard)
        return NAME

    await loading_msg.delete()
    await generate_and_send_excel(update.message, flat_data, f'sites_{term_clean}.xlsx', f"✅ تم تصدير {len(flat_data)} موقع يخص ({term})")
    await update.message.reply_text("اختر أحد الخيارات:", reply_markup=start_keyboard)
    return NAME

# --- معالجة الفلترة بالتصنيف للتصدير ---
async def export_get_main_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'main_menu':
        await query.edit_message_text("اختر أحد الخيارات:", reply_markup=start_keyboard)
        return NAME

    main_category_en = query.data
    context.user_data['export_main_category'] = main_category_en
    main_category_ar = CATEGORY_TRANSLATION.get(main_category_en, main_category_en)
    
    sub_categories = CATEGORIES.get(main_category_en, [])
    
    keyboard = [[InlineKeyboardButton(f"📦 تصدير كل ({main_category_ar})", callback_data='export_this_main')]]
    if sub_categories:
        keyboard.append([InlineKeyboardButton("📂 واصل الفلترة بالتصنيف الفرعي", callback_data='filter_sub')])
    keyboard.append([InlineKeyboardButton("رجوع ⬅️", callback_data='export_data')])
    
    await query.edit_message_text(f"📥 خيارات تصدير لـ ({main_category_ar}):", reply_markup=InlineKeyboardMarkup(keyboard))
    return EXPORT_SUB_CAT_SELECT

async def export_get_sub_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    main_category_en = context.user_data.get('export_main_category', '')
    main_category_ar = CATEGORY_TRANSLATION.get(main_category_en, main_category_en)
    
    if query.data == 'export_data':
        # العودة للقائمة الأولى
        return await handle_button(update, context) # سيتعامل مع export_data
        
    elif query.data == 'export_this_main':
        await query.edit_message_text(f"⏳ جاري تجهيز كل مواقع ({main_category_ar})...")
        flat_data = get_data_for_export(main_category_en)
        if not flat_data:
            await query.edit_message_text(f"⚠️ لا توجد مواقع في هذا التصنيف.")
        else:
            await generate_and_send_excel(query.message, flat_data, f'sites_{main_category_en}.xlsx', f"✅ تم تصدير كل مواقع ({main_category_ar})")
        await query.message.reply_text("اختر أحد الخيارات:", reply_markup=start_keyboard)
        return NAME
        
    elif query.data == 'filter_sub':
        sub_categories = CATEGORIES.get(main_category_en, [])
        reply_markup = build_keyboard(sub_categories)
        await query.edit_message_text(f"📂 اختر التصنيف الفرعي من ({main_category_ar}) الذي تريد تصديره:", reply_markup=reply_markup)
        return EXPORT_SUB_CAT_SELECT
        
    else:
        # المستخدم اختار تصنيف فرعي معين لتصديره
        sub_category_en = query.data
        sub_category_ar = SUB_CATEGORY_TRANSLATION.get(sub_category_en, sub_category_en)
        await query.edit_message_text(f"⏳ جاري تجهيز مواقع ({sub_category_ar})...")
        
        flat_data = get_data_for_export(main_category_en, sub_category_en)
        if not flat_data:
            await query.edit_message_text(f"⚠️ لا توجد مواقع في هذا التصنيف الفرعي.")
        else:
            await generate_and_send_excel(query.message, flat_data, f'sites_{sub_category_en}.xlsx', f"✅ تم تصدير مواقـع ({sub_category_ar})")
        await query.message.reply_text("اختر أحد الخيارات:", reply_markup=start_keyboard)
        return NAME

# دوال مساعدة للتصدير
def get_data_for_export(main_filter=None, sub_filter=None):
    data = load_site_data()
    flat_data = []
    for main_cat_en, content in data.get('main_categories', {}).items():
        if main_filter and main_filter != main_cat_en:
            continue
        main_cat_ar = CATEGORY_TRANSLATION.get(main_cat_en, main_cat_en)
        for sub_cat_en, sites in content.get('sub_categories', {}).items():
            if sub_filter and sub_filter != sub_cat_en:
                continue
            sub_cat_ar = SUB_CATEGORY_TRANSLATION.get(sub_cat_en, sub_cat_en)
            for site in sites:
                flat_data.append({
                    "التصنيف الرئيسي": main_cat_ar,
                    "التصنيف الفرعي": sub_cat_ar,
                    "الموقع": site.get("website", ""),
                    "الوصف": site.get("description", ""),
                    "الفائدة": site.get("benefit", "")
                })
    return flat_data

def create_html_report(data, title):
    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f2f5; margin: 0; padding: 15px; }}
        h1 {{ text-align: center; color: #1a73e8; font-size: 22px; margin-bottom: 20px; }}
        .stats {{ text-align: center; color: #5f6368; font-size: 14px; margin-bottom: 20px; }}
        .card {{ background: white; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-right: 4px solid #1a73e8; }}
        .site-name {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
        .site-name a {{ color: #1a73e8; text-decoration: none; word-break: break-all; }}
        .badges {{ margin-bottom: 10px; }}
        .badge {{ display: inline-block; background: #e8f0fe; color: #1967d2; padding: 4px 10px; border-radius: 12px; font-size: 12px; margin-left: 5px; }}
        .desc {{ font-size: 14px; color: #3c4043; line-height: 1.5; margin-bottom: 10px; }}
        .benefit {{ font-size: 14px; color: #0d652d; background: #e6f4ea; padding: 10px; border-radius: 8px; line-height: 1.5; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="stats">إجمالي المواقع: {len(data)}</div>
"""
    for item in data:
        html += f"""
    <div class="card">
        <div class="site-name"><a href="{item.get('الموقع','')}" target="_blank">{item.get('الموقع','')}</a></div>
        <div class="badges">
            <span class="badge">{item.get('التصنيف الرئيسي','')}</span>
            <span class="badge">{item.get('التصنيف الفرعي','')}</span>
        </div>
        <div class="desc">📝 <b>الوصف:</b> {item.get('الوصف','')}</div>
"""
        if item.get('الفائدة',''):
            html += f'        <div class="benefit">💡 <b>الفائدة:</b> {item.get("الفائدة","")}</div>\n'
        html += '    </div>\n'
    
    html += "</body>\n</html>"
    return html

async def generate_and_send_excel(message, flat_data, filename, success_text):
    if not flat_data:
        await message.reply_text("❌ لم يتم العثور على بيانات للتصدير.")
        return
    try:
        from telegram import InputMediaDocument
        
        # 1. إعداد Excel
        df = pd.DataFrame(flat_data)
        excel_filename = filename
        with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sites')
            worksheet = writer.sheets['Sites']
            worksheet.sheet_view.rightToLeft = True # دعم اللغة العربية
            # توسعة الأعمدة
            for column_cells in worksheet.columns:
                length = max(len(str(cell.value)) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 60)
                
        # 2. إعداد HTML
        title_hdr = success_text.replace("✅ ", "").replace("", "")
        html_content = create_html_report(flat_data, title_hdr)
        html_filename = filename.replace('.xlsx', '.html')
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        # 3. إرسال الملفين كـ Media Group
        with open(excel_filename, 'rb') as f_xl, open(html_filename, 'rb') as f_html:
            await message.reply_media_group([
                InputMediaDocument(f_xl, caption="📊 ملف Excel (يدعم العربية)"),
                InputMediaDocument(f_html, caption="🌐 صفحة HTML تفاعلية وممتازة للجوال")
            ])
        await message.reply_text(success_text)
            
    except Exception as e:
        logger.error(f"خطأ أثناء إنشاء ملفات التصدير: {e}")
        await message.reply_text("⚠️ حدث خطأ أثناء تجهيز ملفات التصدير.")
    finally:
        import os
        # تنظيف الملفات المؤقتة
        for temp_file in [filename, filename.replace('.xlsx', '.html')]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logger.error(f"فشل في مسح الملف المؤقت {temp_file}: {e}")

# --- معالج المحادثة ---
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_name),
            CallbackQueryHandler(handle_button)
        ],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
        BENEFIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_benefit)],
        MAIN_CATEGORY: [CallbackQueryHandler(get_main_category)],
        SUB_CATEGORY: [CallbackQueryHandler(get_sub_category)],
        CONFIRM: [CallbackQueryHandler(confirm_data)],
        SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, perform_search)],
        VIEW_RESULT: [CallbackQueryHandler(handle_button)],
        EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],
        EDIT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_description)],
        EDIT_BENEFIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_benefit)],
        EXPORT_MENU: [CallbackQueryHandler(handle_button)],
        EXPORT_SMART_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_export_smart_search)],
        EXPORT_MAIN_CAT_SELECT: [CallbackQueryHandler(export_get_main_category)],
        EXPORT_SUB_CAT_SELECT: [CallbackQueryHandler(export_get_sub_category)],
    },
    fallbacks=[CommandHandler('cancel', cancel_conversation)]
)