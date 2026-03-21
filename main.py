import logging
from telegram import Update
from telegram.ext import (
    Application,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from handlers import (
    start,
    handle_button,
    get_name,
    get_description,
    get_benefit,
    get_main_category,
    get_sub_category,
    confirm_data,
    cancel_conversation,
    perform_search,
    edit_name,
    edit_description,
    edit_benefit,
    NAME,
    DESCRIPTION,
    BENEFIT,
    MAIN_CATEGORY,
    SUB_CATEGORY,
    CONFIRM,
    SEARCH,
    VIEW_RESULT,
    EDIT_NAME,
    EDIT_DESCRIPTION,
    EDIT_BENEFIT,
    EXPORT_MENU,
    EXPORT_SMART_SEARCH,
    EXPORT_MAIN_CAT_SELECT,
    EXPORT_SUB_CAT_SELECT,
    handle_export_smart_search,
    export_get_main_category,
    export_get_sub_category,
)
from config import TOKEN

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    """تشغيل البوت"""
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()

    # إعداد المحادثة
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("search", perform_search),
        ],
        states={
            NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name),
                CallbackQueryHandler(handle_button),
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
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            CommandHandler("start", start),
        ],
    )

    # إضافة معالج المحادثة
    application.add_handler(conv_handler)

    # تسجيل عند بدء التشغيل
    logger.info("بدء تشغيل البوت...")

    # تشغيل البوت باستخدام polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()