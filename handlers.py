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

def escape_md(text):
    """تهريب الرموز الخاصة في Markdown"""
    for ch in ['_', '*', '`', '[']:
        text = str(text).replace(ch, f'\\{ch}')
    return text

# --- التحقق الأمني (Middleware) ---
async def auth_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    
    if update.message and update.message.text and update.message.text.startswith('/login'):
        return
        
    if not is_admin(user_id):
        if update.message:
            await update.message.reply_text("⛔ عذراً، هذا البوت مخصص للإدارة المركزية فقط.\nيرجى التواصل مع المسؤول للحصول على صلاحية الوصول.")
        raise ApplicationHandlerStop()

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # تسجيل الدخول مخصص فقط للمالك
    if update.effective_user.id != 1156962576:
        await update.message.reply_text("⛔ هذا الأمر مخصص للمالك فقط.\nيرجى التواصل مع المسؤول لإضافتك.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ يرجى إدخال كلمة المرور مع الأمر، مثال:\n`/login PASSWORD`", parse_mode='Markdown')
        return
        
    if args[0] == ADMIN_PASSWORD:
        user_id = update.effective_user.id
        name = update.effective_user.first_name or "Admin"
        success, error_msg = add_admin(user_id, name)
        if success:
            await update.message.reply_text("✅ تم التحقق بنجاح! أنت الآن مدير معتمد.\n\nاضغط /start لفتح لوحة التحكم.")
        else:
            await update.message.reply_text(f"⚠️ حدث خطأ أثناء التسجيل.\n\nالخطأ: {error_msg}")
    else:
        await update.message.reply_text("❌ كلمة المرور غير صحيحة.")

# تعريف حالات المحادثة
NAME, DESCRIPTION, BENEFIT, MAIN_CATEGORY, SUB_CATEGORY, CONFIRM, SEARCH, VIEW_RESULT, EDIT_NAME, EDIT_DESCRIPTION, EDIT_BENEFIT, EXPORT_MENU, EXPORT_SMART_SEARCH, EXPORT_MAIN_CAT_SELECT, EXPORT_SUB_CAT_SELECT, ADD_ADMIN_STATE = range(16)


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

# دالة إضافة مسؤول جديد عبر Telegram ID
async def handle_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    
    try:
        new_id = int(text)
    except ValueError:
        await update.message.reply_text("❌ يرجى إدخال الـ Telegram ID كرقم صحيح فقط (بدون أحرف).\n\nأعد المحاولة أو اضغط /start للعودة.")
        return ADD_ADMIN_STATE
    
    # التحقق من عدم إضافته مسبقاً
    if is_admin(new_id):
        await update.message.reply_text(f"⚠️ المستخدم `{new_id}` مسجل مسبقاً كمسؤول.", parse_mode='Markdown')
        context.user_data.pop('awaiting_admin_id', None)
        return await start(update, context)
    
    success, error_msg = add_admin(new_id, f"Admin {new_id}")
    if success:
        await update.message.reply_text(f"✅ تمت إضافة المسؤول الجديد بنجاح!\n\nTelegram ID: `{new_id}`\n\nالآن يمكنه فتح البوت واستخدامه مباشرة.", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"⚠️ حدث خطأ أثناء الإضافة.\n\nالخطأ: {error_msg}")
    
    context.user_data.pop('awaiting_admin_id', None)
    return await start(update, context)

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
    
    # Show admin management only for the owner
    if update.effective_user.id == 1156962576:
        keyboard.append([InlineKeyboardButton("👥 إدارة المسؤولين", callback_data='manage_admins')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text("اختر أحد الخيارات:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("اختر أحد الخيارات:", reply_markup=reply_markup)
    return NAME

# --- دالة مساعدة لعرض اقتراح ---
async def show_suggestion(query, context, prefix=""):
    """عرض اقتراح بالفهرس الحالي مع أزرار التنقل وكشف التكرار"""
    suggestions = context.user_data.get('suggestions_list', [])
    idx = context.user_data.get('sug_index', 0)
    total = len(suggestions)
    
    if not suggestions or idx >= total:
        await query.edit_message_text("📭 لا يوجد اقتراحات معلقة.")
        return
    
    sug = suggestions[idx]
    website = sug.get('website', '')
    
    text = (f"{prefix}📩 اقتراح ({idx + 1}/{total}):\n\n"
            f"🌐 الموقع: {escape_md(website)}\n"
            f"📂 التصنيف: {escape_md(sug.get('main_category', ''))} > {escape_md(sug.get('sub_category', 'غير محدد'))}\n"
            f"📝 الوصف: {escape_md(sug.get('description', ''))}\n"
            f"💡 الفائدة: {escape_md(sug.get('benefit', 'لا يوجد'))}")
    
    # --- كشف التكرار ---
    duplicates = check_duplicate(website)
    has_duplicate = bool(duplicates)
    
    if has_duplicate:
        dup = duplicates[0]  # أول تطابق
        dup_main_ar = CATEGORY_TRANSLATION.get(dup.get('main_category', ''), dup.get('main_category', ''))
        dup_sub_ar = SUB_CATEGORY_TRANSLATION.get(dup.get('sub_category', ''), dup.get('sub_category', ''))
        text += (
            f"\n\n⚠️ *هذا الموقع موجود مسبقاً في قاعدة البيانات!*\n"
            f"➖➖➖➖➖➖➖➖\n"
            f"📌 *الموقع الموجود:*\n"
            f"🌐 الاسم/الرابط: {escape_md(dup.get('website', 'لا يوجد'))}\n"
            f"📂 التصنيف: {escape_md(dup_main_ar)} \\> {escape_md(dup_sub_ar)}\n"
            f"📝 الوصف: {escape_md(dup.get('description', 'لا يوجد'))}\n"
            f"💡 الفائدة: {escape_md(dup.get('benefit', 'لا يوجد'))}"
        )
        # حفظ بيانات الموقع الموجود لاستخدامها لاحقاً عند تعديله
        context.user_data['dup_existing_site'] = dup
    else:
        context.user_data.pop('dup_existing_site', None)
    
    # --- بناء الأزرار ---
    row1 = [
        InlineKeyboardButton("✅ موافقة", callback_data=f"app_{sug['id']}"),
        InlineKeyboardButton("❌ رفض", callback_data=f"rej_{sug['id']}")
    ]
    
    rows = [row1]
    
    # دمج أزرار التعديل في صف واحد لتجنب قص النص على التلفون
    if has_duplicate:
        rows.append([
            InlineKeyboardButton("✏️ تعديل الاقتراح", callback_data=f"sug_edit_{sug['id']}"),
            InlineKeyboardButton("🔧 تعديل الموجود", callback_data=f"dup_edit_{sug['id']}")
        ])
    else:
        rows.append([InlineKeyboardButton("✏️ تعديل الاقتراح", callback_data=f"sug_edit_{sug['id']}")])
    
    # أزرار التنقل
    nav_buttons = []
    if idx > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data="sug_prev"))
    if idx < total - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ▶️", callback_data="sug_next"))
    if nav_buttons:
        rows.append(nav_buttons)
    
    rows.append([InlineKeyboardButton("🏠 رجوع للقائمة", callback_data='main_menu')])
    
    keyboard = InlineKeyboardMarkup(rows)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

# --- معالجة النقر على الزر ---
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    logger.info(f"استقبال callback_query: {query.data} من المستخدم {update.effective_user.id}")
    await query.answer()

    if query.data == 'start_add':
        context.user_data.clear()
        await query.edit_message_text("📝 اسم الموقع أو الرابط:")
        return NAME
    elif query.data == 'main_menu':
        context.user_data.clear()
        return await start(update, context)
        
    # --- قسم الاقتراحات ---
    elif query.data == 'review_suggestions':
        from db import fetch_pending_suggestions
        suggestions = fetch_pending_suggestions()
        if not suggestions:
            await query.edit_message_text("📭 لا يوجد اقتراحات معلقة حالياً.")
            await asyncio.sleep(1)
            return await start(update, context)
        
        context.user_data['suggestions_list'] = suggestions
        context.user_data['sug_index'] = 0
        await show_suggestion(query, context)
        return NAME

    elif query.data == 'sug_next':
        suggestions = context.user_data.get('suggestions_list', [])
        idx = context.user_data.get('sug_index', 0)
        if idx < len(suggestions) - 1:
            context.user_data['sug_index'] = idx + 1
        await show_suggestion(query, context)
        return NAME

    elif query.data == 'sug_prev':
        idx = context.user_data.get('sug_index', 0)
        if idx > 0:
            context.user_data['sug_index'] = idx - 1
        await show_suggestion(query, context)
        return NAME

    elif query.data.startswith("app_"):
        from db import fetch_pending_suggestions, update_suggestion_status, add_site
        
        sug_id = query.data.split("_")[1]
        suggestions = context.user_data.get('suggestions_list', [])
        sug = next((s for s in suggestions if str(s['id']) == sug_id), None)
        if not sug:
            await query.edit_message_text("⚠️ لم يتم العثور على الاقتراح.")
            await asyncio.sleep(1)
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
                main_category=main_en,
                sub_category=sub_en,
                website=sug.get('website', ''),
                description=sug.get('description', ''),
                benefit=sug.get('benefit', '')
            )
            # تحديث القائمة وعرض التالي
            updated = fetch_pending_suggestions()
            context.user_data['suggestions_list'] = updated
            if updated:
                context.user_data['sug_index'] = 0
                await show_suggestion(query, context, prefix="✅ تم قبول وإضافة الموقع!\n\n")
            else:
                await query.edit_message_text("✅ تم قبول وإضافة الموقع!\n\n📭 لا يوجد اقتراحات أخرى معلقة.")
                await asyncio.sleep(1)
                return await start(update, context)
            return NAME
        else:
            context.user_data['name'] = sug.get('website', '')
            context.user_data['description'] = sug.get('description', '')
            context.user_data['benefit'] = sug.get('benefit', '')
            
            options = list(CATEGORIES.keys())
            reply_markup = build_main_category_keyboard(options)
            await query.edit_message_text(f"تم قبول {sug.get('website', '')}!\n\n⚠️ التصنيفات لم تتعرف تلقائياً.\n📂 يرجى اختيار التصنيف الرئيسي لإضافته:", reply_markup=reply_markup)
            return MAIN_CATEGORY

    elif query.data.startswith("rej_"):
        from db import update_suggestion_status, fetch_pending_suggestions
        sug_id = query.data.split("_")[1]
        update_suggestion_status(sug_id, "rejected")
        
        # تحديث القائمة وعرض التالي
        updated = fetch_pending_suggestions()
        context.user_data['suggestions_list'] = updated
        if updated:
            context.user_data['sug_index'] = 0
            await show_suggestion(query, context, prefix="✅ تم الرفض!\n\n")
        else:
            await query.edit_message_text("✅ تم الرفض!\n\n📭 لا يوجد اقتراحات أخرى معلقة.")
            await asyncio.sleep(1)
            return await start(update, context)
        return NAME

    elif query.data.startswith("sug_edit_"):
        sug_id = query.data.split("sug_edit_")[1]
        suggestions = context.user_data.get('suggestions_list', [])
        sug = next((s for s in suggestions if str(s['id']) == sug_id), None)
        if not sug:
            await query.edit_message_text("⚠️ لم يتم العثور على الاقتراح.")
            await asyncio.sleep(1)
            return await start(update, context)
        
        # حفظ بيانات الاقتراح للتعديل
        context.user_data['editing_suggestion_id'] = sug_id
        context.user_data['edit_old_name'] = sug.get('website', '')
        context.user_data['edit_old_description'] = sug.get('description', '')
        context.user_data['edit_old_benefit'] = sug.get('benefit', '')
        context.user_data['editing_mode'] = 'suggestion'
        
        old_name = sug.get('website', '')
        await query.edit_message_text(
            f"✏️ **تعديل بيانات الاقتراح**\n\n"
            f"📝 **الاسم/الرابط الحالي:**\n`{old_name}`\n\n"
            f"أدخل الاسم الجديد أو أرسل **-** للإبقاء على الحالي:",
            parse_mode='Markdown'
        )
        return EDIT_NAME

    elif query.data.startswith("dup_edit_"):
        # تعديل الموقع الموجود (المكرر) في قاعدة البيانات
        dup = context.user_data.get('dup_existing_site')
        if not dup:
            await query.answer("⚠️ لم يتم العثور على بيانات الموقع الموجود.", show_alert=True)
            return NAME
        
        # تجهيز بيانات الموقع الموجود للتعديل
        context.user_data['edit_old_name'] = dup.get('website', '')
        context.user_data['edit_old_description'] = dup.get('description', '')
        context.user_data['edit_old_benefit'] = dup.get('benefit', '')
        context.user_data['edit_main_category_en'] = dup.get('main_category', '')
        context.user_data['edit_sub_category_en'] = dup.get('sub_category', '')
        context.user_data['editing_mode'] = 'site'
        # حفظ مؤشر الاقتراح للعودة إليه لاحقاً
        context.user_data['return_to_suggestions'] = True
        
        old_name = dup.get('website', '')
        dup_main_ar = CATEGORY_TRANSLATION.get(dup.get('main_category', ''), dup.get('main_category', ''))
        dup_sub_ar = SUB_CATEGORY_TRANSLATION.get(dup.get('sub_category', ''), dup.get('sub_category', ''))
        
        text = (
            f"🔧 تعديل الموقع الموجود\n\n"
            f"📂 التصنيف: {dup_main_ar} > {dup_sub_ar}\n\n"
            f"📝 الاسم/الرابط الحالي:\n{old_name}\n\n"
            f"أدخل الاسم الجديد أو أرسل - للإبقاء على الحالي:"
        )
        
        try:
            await query.edit_message_text(text)
        except Exception as e:
            logger.error(f"Error editing message in dup_edit_: {e}")
            await query.message.reply_text(text)
            
        return EDIT_NAME
    
    # --- قسم إدارة المسؤولين ---
    elif query.data == 'manage_admins':
        if update.effective_user.id != 1156962576:
            await query.edit_message_text("⛔ فقط المالك يمكنه إدارة المسؤولين")
            await asyncio.sleep(1)
            return await start(update, context)
        
        admins = fetch_all_admins()
        text = "👥 **إدارة المسؤولين**\n\n"
        if admins:
            for i, admin in enumerate(admins, 1):
                owner_badge = " 👑" if admin.get('telegram_id') == 1156962576 else ""
                text += f"{i}. {escape_md(admin.get('name', 'غير معرف'))} (`{admin.get('telegram_id', '?')}`){owner_badge}\n"
        else:
            text += "لا يوجد مسؤولون مسجلون حالياً.\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━\n"
        text += "📌 **كيفية إضافة مسؤول جديد:**\n"
        text += "1️⃣ أرسل لصديقك رابط البوت: @userinfobot\n"
        text += "2️⃣ اطلب منه يفتحه ويرسل أي رسالة\n"
        text += "3️⃣ سيظهر له رقم `Id:` — هذا هو الـ Telegram ID\n"
        text += "4️⃣ يرسل لك هذا الرقم\n"
        text += "5️⃣ اضغط ➕ إضافة مسؤول وأدخل الرقم\n"
        text += "✅ **بعدها سيعمل البوت معه مباشرة!**\n\n"
        text += "🗑️ **كيفية حذف مسؤول:**\n"
        text += "اضغط حذف مسؤول واختر الشخص المراد حذفه."
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ إضافة مسؤول", callback_data='add_admin_start'),
             InlineKeyboardButton("🗑️ حذف مسؤول", callback_data='del_admin_list')],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu')]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return NAME
    
    elif query.data == 'add_admin_start':
        await query.edit_message_text("✏️ أدخل رقم **Telegram ID** للشخص الذي تريد إضافته كمسؤول:\n\n(يمكنه معرفة رقمه بإرسال أي رسالة لبوت @userinfobot)", parse_mode='Markdown')
        context.user_data['awaiting_admin_id'] = True
        return ADD_ADMIN_STATE
    
    elif query.data == 'del_admin_list':
        admins = fetch_all_admins()
        admins = [a for a in admins if a.get('telegram_id') != 1156962576]  # لا تسمح بحذف المالك
        if not admins:
            await query.edit_message_text("✅ لا يوجد مسؤولون يمكن حذفهم.")
            await asyncio.sleep(1)
            return await start(update, context)
        
        keyboard = []
        for admin in admins:
            name = admin.get('name', 'غير معرف')
            tid = admin.get('telegram_id', '?')
            keyboard.append([InlineKeyboardButton(f"❌ {name} ({tid})", callback_data=f"rmadm_{tid}")])
        keyboard.append([InlineKeyboardButton("رجوع ⬅️", callback_data='manage_admins')])
        
        await query.edit_message_text("اختر المسؤول الذي تريد حذفه:", reply_markup=InlineKeyboardMarkup(keyboard))
        return NAME
    
    elif query.data.startswith("rmadm_"):
        from db import remove_admin
        tid = int(query.data.split("_")[1])
        if remove_admin(tid):
            await query.answer(f"✅ تم حذف المسؤول {tid} بنجاح", show_alert=True)
        else:
            await query.answer("⚠️ حدث خطأ أثناء الحذف", show_alert=True)
        # عرض قائمة المسؤولين المحدثة مباشرة
        admins = fetch_all_admins()
        text = "👥 **إدارة المسؤولين**\n\n"
        if admins:
            for i, admin in enumerate(admins, 1):
                owner_badge = " 👑" if admin.get('telegram_id') == 1156962576 else ""
                text += f"{i}. {escape_md(admin.get('name', 'غير معرف'))} (`{admin.get('telegram_id', '?')}`){owner_badge}\n"
        else:
            text += "لا يوجد مسؤولون مسجلون حالياً.\n"
        text += "\n✅ تم تحديث القائمة."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ إضافة مسؤول", callback_data='add_admin_start'),
             InlineKeyboardButton("🗑️ حذف مسؤول", callback_data='del_admin_list')],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu')]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return NAME
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
        search_results = context.user_data.get('search_results', [])
        index = context.user_data.get('current_result_index', 0)
        if 0 <= index < len(search_results):
            result = search_results[index]
            context.user_data['edit_old_name'] = result.get('website', '')
            context.user_data['edit_old_description'] = result.get('description', '')
            context.user_data['edit_old_benefit'] = result.get('benefit', '')
            context.user_data['editing_mode'] = 'site'
            old_name = result.get('website', '')
            await query.edit_message_text(
                f"✏️ **تعديل الموقع**\n\n"
                f"📝 **الاسم/الرابط الحالي:**\n`{escape_md(old_name)}`\n\n"
                f"أدخل الاسم الجديد أو أرسل **-** للإبقاء على الحالي:",
                parse_mode='Markdown'
            )
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
    
    user_input = update.message.text.strip()
    old_name = context.user_data.get('edit_old_name', '')
    context.user_data['edit_name'] = old_name if user_input == '-' else user_input
    
    old_desc = context.user_data.get('edit_old_description', '')
    await update.message.reply_text(
        f"✏️ **الوصف الحالي:**\n{escape_md(old_desc)}\n\n"
        f"أدخل الوصف الجديد أو أرسل **-** للإبقاء على الحالي:",
        parse_mode='Markdown'
    )
    return EDIT_DESCRIPTION

# --- معالجة تعديل الوصف ---
async def edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("⚠️ الرجاء إدخال الوصف الجديد:")
        return EDIT_DESCRIPTION
    
    user_input = update.message.text.strip()
    old_desc = context.user_data.get('edit_old_description', '')
    context.user_data['edit_description'] = old_desc if user_input == '-' else user_input
    
    old_benefit = context.user_data.get('edit_old_benefit', '')
    await update.message.reply_text(
        f"✏️ **الفائدة الحالية:**\n{escape_md(old_benefit)}\n\n"
        f"أدخل الفائدة الجديدة أو أرسل **-** للإبقاء على الحالية:",
        parse_mode='Markdown'
    )
    return EDIT_BENEFIT

# --- معالجة تعديل الفائدة وتأكيد التعديل ---
async def edit_benefit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("⚠️ الرجاء إدخال الفائدة الجديدة:")
        return EDIT_BENEFIT
    
    user_input = update.message.text.strip()
    old_benefit = context.user_data.get('edit_old_benefit', '')
    context.user_data['edit_benefit'] = old_benefit if user_input == '-' else user_input
    
    editing_mode = context.user_data.get('editing_mode', 'site')
    
    if editing_mode == 'suggestion':
        # تعديل اقتراح
        from db import update_suggestion_data, fetch_pending_suggestions
        sug_id = context.user_data.get('editing_suggestion_id', '')
        success = update_suggestion_data(
            sug_id,
            context.user_data['edit_name'],
            context.user_data['edit_description'],
            context.user_data['edit_benefit']
        )
        if success:
            await update.message.reply_text("✅ تم تعديل بيانات الاقتراح بنجاح!")
        else:
            await update.message.reply_text("⚠️ حدث خطأ أثناء التعديل.")
        
        # إعادة تحميل الاقتراحات والعودة
        updated = fetch_pending_suggestions()
        context.user_data['suggestions_list'] = updated
        context.user_data['sug_index'] = 0
        context.user_data.pop('editing_mode', None)
        context.user_data.pop('editing_suggestion_id', None)
        return await start(update, context)
    
    # تعديل موقع موجود (المكرر) قادم من مراجعة الاقتراحات
    if context.user_data.get('return_to_suggestions'):
        from db import fetch_pending_suggestions
        main_cat_en = context.user_data.get('edit_main_category_en', '')
        sub_cat_en = context.user_data.get('edit_sub_category_en', '')
        success = edit_site(
            main_category_en=main_cat_en,
            sub_category_en=sub_cat_en,
            old_website=context.user_data.get('edit_old_name', ''),
            new_website=context.user_data['edit_name'],
            new_description=context.user_data['edit_description'],
            new_benefit=context.user_data['edit_benefit']
        )
        if success:
            await update.message.reply_text(
                f"✅ تم تعديل الموقع الموجود بنجاح!\n\n"
                f"📌 الموقع المعدل:\n"
                f"🌐 {context.user_data['edit_name']}\n"
                f"📝 {context.user_data['edit_description']}\n"
                f"💡 {context.user_data['edit_benefit']}"
            )
        else:
            await update.message.reply_text("⚠️ حدث خطأ أثناء تعديل الموقع الموجود.")
        
        # تنظيف وإعادة بيانات الاقتراحات
        context.user_data.pop('return_to_suggestions', None)
        context.user_data.pop('edit_main_category_en', None)
        context.user_data.pop('edit_sub_category_en', None)
        context.user_data.pop('editing_mode', None)
        updated = fetch_pending_suggestions()
        context.user_data['suggestions_list'] = updated
        context.user_data['sug_index'] = 0
        return await start(update, context)
    
    # تعديل موقع من نتائج البحث

    search_results = context.user_data.get('search_results', [])
    index = context.user_data.get('current_result_index', 0)
    if 0 <= index < len(search_results):
        result = search_results[index]
        success = edit_site(
            main_category_en=result['main_category_en'],
            sub_category_en=result['sub_category_en'],
            old_website=context.user_data.get('edit_old_name', result['website']),
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
                f"✅ تم التعديل بنجاح!\n\n"
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
    context.user_data.pop('editing_mode', None)
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

def create_html_report(data: list, title: str) -> str:
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

