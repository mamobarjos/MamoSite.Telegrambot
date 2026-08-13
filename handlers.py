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

# ط¥ط¹ط¯ط§ط¯ ط§ظ„طھط³ط¬ظٹظ„
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def escape_md(text):
    """طھظ‡ط±ظٹط¨ ط§ظ„ط±ظ…ظˆط² ط§ظ„ط®ط§طµط© ظپظٹ Markdown"""
    for ch in ['_', '*', '`', '[']:
        text = str(text).replace(ch, f'\\{ch}')
    return text

# --- ط§ظ„طھط­ظ‚ظ‚ ط§ظ„ط£ظ…ظ†ظٹ (Middleware) ---
async def auth_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    
    from db import is_device_blocked
    if is_device_blocked(str(user_id)):
        if update.message:
            await update.message.reply_text("â›” ط¹ط°ط±ط§ظ‹طŒ ط­ط³ط§ط¨ظƒ/ط¬ظ‡ط§ط²ظƒ ظ…ط­ط¸ظˆط± ظ…ظ† ط§ط³طھط®ط¯ط§ظ… ط§ظ„ط¨ظˆطھ ط¨ط³ط¨ط¨ طھظƒط±ط§ط± ط§ظ„ظ…ط­ط§ظˆظ„ط§طھ ط§ظ„ظپط§ط´ظ„ط©.\nظٹط±ط¬ظ‰ ط§ظ„طھظˆط§طµظ„ ظ…ط¹ ظ…ط³ط¤ظˆظ„ ط§ظ„ظ†ط¸ط§ظ… ظ„ظپظƒ ط§ظ„ط­ط¸ط±.")
        elif update.callback_query:
            await update.callback_query.answer("â›” ط­ط³ط§ط¨ظƒ/ط¬ظ‡ط§ط²ظƒ ظ…ط­ط¸ظˆط± ظ…ظ† ط§ظ„ط§ط³طھط®ط¯ط§ظ…!", show_alert=True)
        raise ApplicationHandlerStop()

    if update.message and update.message.text and update.message.text.startswith('/login'):
        return
        
    if not is_admin(user_id):
        if update.message:
            await update.message.reply_text("â›” ط¹ط°ط±ط§ظ‹طŒ ظ‡ط°ط§ ط§ظ„ط¨ظˆطھ ظ…ط®طµطµ ظ„ظ„ط¥ط¯ط§ط±ط© ط§ظ„ظ…ط±ظƒط²ظٹط© ظپظ‚ط·.\nظٹط±ط¬ظ‰ ط§ظ„طھظˆط§طµظ„ ظ…ط¹ ط§ظ„ظ…ط³ط¤ظˆظ„ ظ„ظ„ط­طµظˆظ„ ط¹ظ„ظ‰ طµظ„ط§ط­ظٹط© ط§ظ„ظˆطµظˆظ„.")
        raise ApplicationHandlerStop()

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    from db import is_device_blocked, record_login_attempt, set_device_block_status, add_admin, get_access_password
    
    # ط§ظ„طھط­ظ‚ظ‚ ظ…ظ…ط§ ط¥ط°ط§ ظƒط§ظ† ط§ظ„ط¬ظ‡ط§ط² ظ…ط­ط¸ظˆط±ط§ظ‹
    if is_device_blocked(str(user_id)):
        await update.message.reply_text("â›” **ط­ط³ط§ط¨ظƒ/ط¬ظ‡ط§ط²ظƒ ظ…ط­ط¸ظˆط± ظ…ظ† ظ…ط­ط§ظˆظ„ط§طھ ط§ظ„طھط³ط¬ظٹظ„!**\nطھط¬ط§ظˆط²طھ ط§ظ„ط­ط¯ ط§ظ„ظ…ط³ظ…ظˆط­ ظ„ظ„ظ…ط­ط§ظˆظ„ط§طھ ط§ظ„ط®ط§ط·ط¦ط©. ظٹط±ط¬ظ‰ ط§ظ„طھظˆط§طµظ„ ظ…ط¹ ط§ظ„ظ…ط³ط¤ظˆظ„ ظ„ظپظƒ ط§ظ„ط­ط¸ط±.")
        return

    # طھط³ط¬ظٹظ„ ط§ظ„ط¯ط®ظˆظ„ ظ…ط®طµطµ ظپظ‚ط· ظ„ظ„ظ…ط§ظ„ظƒ ط£ظˆ ط§ظ„ظ…ط¯ط±ط§ط، ط§ظ„ظ…طµط±ط­ ظ„ظ‡ظ…
    if user_id != 1156962576 and not is_admin(user_id):
        await update.message.reply_text("â›” ظ‡ط°ط§ ط§ظ„ط£ظ…ط± ظ…ط®طµطµ ظ„ظ„ظ…ط³ط¤ظˆظ„ظٹظ† ظپظ‚ط·.\nظٹط±ط¬ظ‰ ط§ظ„طھظˆط§طµظ„ ظ…ط¹ ط§ظ„ظ…ط§ظ„ظƒ ظ„ط¥ط¶ط§ظپطھظƒ.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("âڑ ï¸ڈ ظٹط±ط¬ظ‰ ط¥ط¯ط®ط§ظ„ ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ظ…ط¹ ط§ظ„ط£ظ…ط±طŒ ظ…ط«ط§ظ„:\n`/login PASSWORD`", parse_mode='Markdown')
        return
        
    entered_password = args[0].strip()
    current_password = get_access_password() or ADMIN_PASSWORD

    if entered_pas    else:
        failed_count = record_login_attempt(str(user_id), success=False)
        if failed_count >= 5:
            set_device_block_status(str(user_id), is_blocked=True)
            await update.message.reply_text(
                "â‌Œ **ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط؛ظٹط± طµط­ظٹط­ط©.**\n\n"
                "â›” **طھظ†ط¨ظٹظ‡ ط£ظ…ظ†ظٹ:** ظ„ظ‚ط¯ طھط¬ط§ظˆط²طھ 5 ظ…ط­ط§ظˆظ„ط§طھ ط®ط§ط·ط¦ط© ظ…طھطھط§ظ„ظٹط©! طھظ… ط­ط¸ط± ط­ط³ط§ط¨ظƒ/ط¬ظ‡ط§ط²ظƒ ظ…ظ† ط§ظ„ظ†ط¸ط§ظ…."
            )
        else:
            remaining = max(0, 5 - failed_count)
            await update.message.reply_text(
                f"â‌Œ **ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط؛ظٹط± طµط­ظٹط­ط©.**\n"
                f"âڑ ï¸ڈ ظٹطھط¨ظ‚ظ‰ ظ„ظƒ {remaining} ظ…ط­ط§ظˆظ„ط§طھ ظ‚ط¨ظ„ ط­ط¸ط± ط§ظ„ط¬ظ‡ط§ط²."
            )

# طھط¹ط±ظٹظپ ط­ط§ظ„ط§طھ ط§ظ„ظ…ط­ط§ط¯ط«ط©
NAME, DESCRIPTION, BENEFIT, MAIN_CATEGORY, SUB_CATEGORY, CONFIRM, SEARCH, VIEW_RESULT, EDIT_NAME, EDIT_DESCRIPTION, EDIT_BENEFIT, EXPORT_MENU, EXPORT_SMART_SEARCH, EXPORT_MAIN_CAT_SELECT, EXPORT_SUB_CAT_SELECT, ADD_ADMIN_STATE, IP_MENU, ADD_IP_STATE, ADD_IP_LABEL_STATE, CHANGE_PASSWORD_STATE, OLD_PWD_STATE, NEW_PWD_STATE, CONFIRM_PWD_STATE = range(23)


# ط¯ط§ظ„ط© ظ„ط¨ظ†ط§ط، ظ„ظˆط­ط© ظ…ظپط§طھظٹط­ طھظپط§ط¹ظ„ظٹط© ظ„ظ„طھطµظ†ظٹظپط§طھ ط§ظ„ظپط±ط¹ظٹط©
def build_keyboard(options, row_size=2):
    keyboard = [
        [InlineKeyboardButton(SUB_CATEGORY_TRANSLATION.get(opt, opt), callback_data=opt) for opt in options[i:i + row_size]]
        for i in range(0, len(options), row_size)
    ]
    return InlineKeyboardMarkup(keyboard)

# ط¯ط§ظ„ط© ظ„ط¨ظ†ط§ط، ظ„ظˆط­ط© ظ…ظپط§طھظٹط­ طھظپط§ط¹ظ„ظٹط© ظ„ظ„طھطµظ†ظٹظپط§طھ ط§ظ„ط±ط¦ظٹط³ظٹط©
def build_main_category_keyboard(options, row_size=2):
    keyboard = [
        [InlineKeyboardButton(CATEGORY_TRANSLATION.get(opt, opt), callback_data=opt) for opt in options[i:i + row_size]]
        for i in range(0, len(options), row_size)
    ]
    return InlineKeyboardMarkup(keyboard)

# ط¥ظ†ط´ط§ط، ظ„ظˆط­ط© ط§ظ„ظ…ظپط§طھظٹط­ ط§ظ„طھظپط§ط¹ظ„ظٹط©
start_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("ط§ط¨ط¯ط£ ط§ظ„ط¢ظ† â–¶ï¸ڈ", callback_data='start')],
    [InlineKeyboardButton("طھطµط¯ظٹط± ط§ظ„ط¨ظٹط§ظ†ط§طھ ًں“¤", callback_data='export_data')],
    [InlineKeyboardButton("ط§ظ„ط¨ط­ط« ًں”چ", callback_data='search')]
])

confirm_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("ظ†ط¹ظ…", callback_data='yes'), InlineKeyboardButton("ظ„ط§", callback_data='no')]
])

# ظ„ظˆط­ط© ظ…ظپط§طھظٹط­ ظ„ط¹ط±ط¶ ط§ظ„ظ†طھط§ط¦ط¬
def result_options_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ط±ط¬ظˆط¹ â¬…ï¸ڈ", callback_data='back_to_results'),
            InlineKeyboardButton("طھط¹ط¯ظٹظ„ âœڈï¸ڈ", callback_data='edit_result'),
            InlineKeyboardButton("ط­ط°ظپ ًں—‘ï¸ڈ", callback_data='delete_result')
        ],
        [
            InlineKeyboardButton("ًں”چ ط¨ط­ط« ط¬ط¯ظٹط¯", callback_data='search'),
            InlineKeyboardButton("ًںڈ  ط§ظ„ظ‚ط§ط¦ظ…ط©", callback_data='main_menu')
        ]
    ])

# ط¯ط§ظ„ط© ط¥ظ„ط؛ط§ط، ط§ظ„ظ…ط­ط§ط¯ط«ط©
async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("ًںڑ« طھظ… ط¥ظ„ط؛ط§ط، ط§ظ„ط¹ظ…ظ„ظٹط©.")
    context.user_data.clear()
    return ConversationHandler.END

# ط¯ط§ظ„ط© ط¥ط¶ط§ظپط© ظ…ط³ط¤ظˆظ„ ط¬ط¯ظٹط¯ ط¹ط¨ط± Telegram ID
async def handle_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    
    try:
        new_id = int(text)
    except ValueError:
        await update.message.reply_text("â‌Œ ظٹط±ط¬ظ‰ ط¥ط¯ط®ط§ظ„ ط§ظ„ظ€ Telegram ID ظƒط±ظ‚ظ… طµط­ظٹط­ ظپظ‚ط· (ط¨ط¯ظˆظ† ط£ط­ط±ظپ).\n\nط£ط¹ط¯ ط§ظ„ظ…ط­ط§ظˆظ„ط© ط£ظˆ ط§ط¶ط؛ط· /start ظ„ظ„ط¹ظˆط¯ط©.")
        return ADD_ADMIN_STATE
    
    # ط§ظ„طھط­ظ‚ظ‚ ظ…ظ† ط¹ط¯ظ… ط¥ط¶ط§ظپطھظ‡ ظ…ط³ط¨ظ‚ط§ظ‹
    if is_admin(new_id):
        await update.message.reply_text(f"âڑ ï¸ڈ ط§ظ„ظ…ط³طھط®ط¯ظ… `{new_id}` ظ…ط³ط¬ظ„ ظ…ط³ط¨ظ‚ط§ظ‹ ظƒظ…ط³ط¤ظˆظ„.", parse_mode='Markdown')
        context.user_data.pop('awaiting_admin_id', None)
        return await start(update, context)
    
    success, error_msg = add_admin(new_id, f"Admin {new_id}")
    if success:
        await update.message.reply_text(f"âœ… طھظ…طھ ط¥ط¶ط§ظپط© ط§ظ„ظ…ط³ط¤ظˆظ„ ط§ظ„ط¬ط¯ظٹط¯ ط¨ظ†ط¬ط§ط­!\n\nTelegram ID: `{new_id}`\n\nط§ظ„ط¢ظ† ظٹظ…ظƒظ†ظ‡ ظپطھط­ ط§ظ„ط¨ظˆطھ ظˆط§ط³طھط®ط¯ط§ظ…ظ‡ ظ…ط¨ط§ط´ط±ط©.", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"âڑ ï¸ڈ ط­ط¯ط« ط®ط·ط£ ط£ط«ظ†ط§ط، ط§ظ„ط¥ط¶ط§ظپط©.\n\nط§ظ„ط®ط·ط£: {error_msg}")
    
    context.user_data.pop('awaiting_admin_id', None)
    return await start(update, context)

# --- ط¥ط¯ط§ط±ط© ط§ظ„ط£ط¬ظ‡ط²ط© ط§ظ„ظ…ط³ظ…ظˆط­ط© ظˆط§ظ„ظ…ط­ط¸ظˆط±ط© ---
async def handle_manage_devices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ط¹ط±ط¶ ط¥ط¯ط§ط±ط© ط§ظ„ط£ط¬ظ‡ط²ط© ظˆط§ظ„ظ€ IPs ط§ظ„ظ…ط³ظ…ظˆط­ط© ظˆط§ظ„ظ…ط­ط¸ظˆط±ط© ظˆط§ظ„طھط­ظƒظ… ط¨ظ‡ط§"""
    from db import fetch_all_devices_and_ips
    items = fetch_all_devices_and_ips()
    count = len(items)
    
    keyboard = []
    if not items:
        text = "ًں“± *ط¥ط¯ط§ط±ط© ط§ظ„ط£ط¬ظ‡ط²ط© ظˆط§ظ„ظˆطµظˆظ„*\n\nâڑ ï¸ڈ ظ„ط§ طھظˆط¬ط¯ ط£ط¬ظ‡ط²ط© ط£ظˆ IPs ظ…ط³ط¬ظ„ط© ط­ط§ظ„ظٹط§ظ‹ ظپظٹ ط§ظ„ظ†ط¸ط§ظ…."
    else:
        text = (
            f"ًں“± *ط¥ط¯ط§ط±ط© ط§ظ„ط£ط¬ظ‡ط²ط© ظˆط§ظ„ظˆطµظˆظ„ ({count})*\n\n"
            "ظ…ظ† ظ‡ظ†ط§ ظٹظ…ظƒظ†ظƒ ط§ظ„ط§ط·ظ„ط§ط¹ ط¹ظ„ظ‰ ط§ظ„ط£ط¬ظ‡ط²ط©/IPs ظˆطھط؛ظٹظٹط± ط­ط§ظ„ط© ط§ظ„ط­ط¸ط± ط£ظˆ ط­ط°ظپظ‡ط§:\n"
        )
        for row in items:
            ident = row.get('identifier', '') or 'IP ط؛ظٹط± ظ…ط­ط¯ط¯'
            label = row.get('label', '') or 'طھظ„ظ‚ط§ط¦ظٹ'
            is_blocked = row.get('is_blocked', False)
            
            if is_blocked:
                btn_label = f"ًں”´ ظ…ط­ط¸ظˆط±: {ident} ({label})"
                keyboard.append([
                    InlineKeyboardButton(btn_label, callback_data=f"unblock_dev:{ident}"),
                    InlineKeyboardButton("ًں—‘ï¸ڈ ظ…ط³ط­", callback_data=f"ask_del_ip:{ident}")
                ])
            else:
                btn_label = f"ًںں¢ ظ…ط³ظ…ظˆط­: {ident} ({label})"
                keyboard.append([
                    InlineKeyboardButton(btn_label, callback_data=f"ask_del_ip:{ident}"),
                    InlineKeyboardButton("â›” ط­ط¸ط±", callback_data=f"block_dev:{ident}")
                ])
            
    keyboard.append([InlineKeyboardButton("â‍• ط¥ط¶ط§ظپط© IP ط¬ط¯ظٹط¯", callback_data='add_ip')])
    keyboard.append([InlineKeyboardButton("ًںڈ  ط§ظ„ظ‚ط§ط¦ظ…ط© ط§ظ„ط±ط¦ظٹط³ظٹط©", callback_data='main_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return NAME

# --- ظ†ط¸ط§ظ… طھط؛ظٹظٹط± ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ---
async def start_password_change_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ط¨ط¯ط، ط¹ظ…ظ„ظٹط© طھط؛ظٹظٹط± ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ظˆط·ظ„ط¨ ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ظ‚ط¯ظٹظ…ط©"""
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("â‌Œ ط¥ظ„ط؛ط§ط،", callback_data='main_menu')]])
    text = (
        "ًں”‘ **طھط؛ظٹظٹط± ظƒظ„ظ…ط© ظ…ط±ظˆط± ط§ظ„ظ…ظˆظ‚ط¹**\n\n"
        "ط§ظ„ط®ط·ظˆط© 1/3: ظٹط±ط¬ظ‰ ط¥ط¯ط®ط§ظ„ **ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ظ‚ط¯ظٹظ…ط© (ط§ظ„ط­ط§ظ„ظٹط©)**:"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    return OLD_PWD_STATE

async def handle_old_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ط§ظ„طھط­ظ‚ظ‚ ظ…ظ† ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ظ‚ط¯ظٹظ…ط©"""
    entered = update.message.text.strip()
    from db import get_access_password
    current_pwd = get_access_password() or ADMIN_PASSWORD
    
    if entered != current_pwd and entered != ADMIN_PASSWORD:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("â‌Œ ط¥ظ„ط؛ط§ط،", callback_data='main_menu')]])
        await update.message.reply_text(
            "â‌Œ **ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ظ‚ط¯ظٹظ…ط© ط؛ظٹط± طµط­ظٹط­ط©.**\n\nظٹط±ط¬ظ‰ ط¥ط¹ط§ط¯ط© ط§ظ„ظ…ط­ط§ظˆظ„ط© ط£ظˆ ط§ط¶ط؛ط· ط¥ظ„ط؛ط§ط، ظ„ظ„ط¹ظˆط¯ط©:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return OLD_PWD_STATE
        
    context.user_data['old_pwd_verified'] = True
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("â‌Œ ط¥ظ„ط؛ط§ط،", callback_data='main_menu')]])
    await update.message.reply_text(
        "âœ… **طھظ… ط§ظ„طھط­ظ‚ظ‚ ظ…ظ† ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ظ‚ط¯ظٹظ…ط© ط¨ظ†ط¬ط§ط­!**\n\nط§ظ„ط®ط·ظˆط© 2/3: ظٹط±ط¬ظ‰ ط¥ط¯ط®ط§ظ„ **ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ط¬ط¯ظٹط¯ط©** (4 ط£ط­ط±ظپ ط¹ظ„ظ‰ ط§ظ„ط£ظ‚ظ„):",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    return NEW_PWD_STATE

async def handle_new_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ط§ط³طھظ‚ط¨ط§ظ„ ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ط¬ط¯ظٹط¯ط© ظˆط·ظ„ط¨ ط§ظ„طھظƒط±ط§ط± ظ„ظ„طھط£ظƒظٹط¯"""
    new_pwd = update.message.text.strip()
    if len(new_pwd) < 4:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("â‌Œ ط¥ظ„ط؛ط§ط،", callback_data='main_menu')]])
        await update.message.reply_text(
            "â‌Œ ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ظ‚طµظٹط±ط© ط¬ط¯ط§ظ‹ (4 ط£ط­ط±ظپ ط¹ظ„ظ‰ ط§ظ„ط£ظ‚ظ„).\nط£ط¹ط¯ ط¥ط¯ط®ط§ظ„ ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ط¬ط¯ظٹط¯ط©:",
            reply_markup=keyboard
        )
        return NEW_PWD_STATE
        
    context.user_data['pending_new_pwd'] = new_pwd
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("â‌Œ ط¥ظ„ط؛ط§ط،", callback_data='main_menu')]])
    await update.message.reply_text(
        f"ًں”‘ ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ط¬ط¯ظٹط¯ط©: `{escape_md(new_pwd)}`\n\nط§ظ„ط®ط·ظˆط© 3/3: ظٹط±ط¬ظ‰ **ط¥ط¹ط§ط¯ط© ط¥ط¯ط®ط§ظ„ ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ط¬ط¯ظٹط¯ط© ظ„طھط£ظƒظٹط¯ظ‡ط§**:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    return CONFIRM_PWD_STATE

async def handle_confirm_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """طھط£ظƒظٹط¯ ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ظˆط­ظپط¸ظ‡ط§ ظپظٹ ظ‚ط§ط¹ط¯ط© ط§ظ„ط¨ظٹط§ظ†ط§طھ"""
    confirm_pwd = update.message.text.strip()
    pending_pwd = context.user_data.get('pending_new_pwd', '')
    
    if confirm_pwd != pending_pwd:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("â‌Œ ط¥ظ„ط؛ط§ط،", callback_data='main_menu')]])
        await update.message.reply_text(
            "â‌Œ **ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط؛ظٹط± ظ…طھط·ط§ط¨ظ‚ط©!**\n\nظٹط±ط¬ظ‰ ط¥ط¹ط§ط¯ط© ظƒطھط§ط¨ط© ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ط¬ط¯ظٹط¯ط© ظ„طھط£ظƒظٹط¯ظ‡ط§:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return CONFIRM_PWD_STATE
        
    from db import set_access_password
    success = set_access_password(confirm_pwd)
    context.user_data.pop('pending_new_pwd', None)
    context.user_data.pop('old_pwd_verified', None)
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("ًںڈ  ط§ظ„ظ‚ط§ط¦ظ…ط© ط§ظ„ط±ط¦ظٹط³ظٹط©", callback_data='main_menu')]])
    if success:
        await update.message.reply_text(
            f"âœ… **طھظ… طھط؛ظٹظٹط± ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط¨ظ†ط¬ط§ط­!**\n\nًں”‘ ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ط¬ط¯ظٹط¯ط©: `{escape_md(confirm_pwd)}`\n\nطھظ… طھط·ط¨ظٹظ‚ ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ط¬ط¯ظٹط¯ط© ظپظٹ ظ‚ط§ط¹ط¯ط© ط§ظ„ط¨ظٹط§ظ†ط§طھ.",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("â‌Œ ط­ط¯ط« ط®ط·ط£ ط£ط«ظ†ط§ط، ط­ظپط¸ ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ط¬ط¯ظٹط¯ط©.", reply_markup=keyboard)
    return NAME

# --- ظ…ط¹ط§ظ„ط¬ط§طھ ط§ظ„ط£ظˆط§ظ…ط± ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    logger.info(f"ط¨ط¯ط، ط§ظ„ظ…ط­ط§ط¯ط«ط© ظ…ط¹ ط§ظ„ظ…ط³طھط®ط¯ظ… {update.effective_user.id}")
    
    from db import fetch_pending_suggestions
    suggestions = fetch_pending_suggestions()
    count = len(suggestions)
    
    keyboard = []
    if count > 0:
        keyboard.append([InlineKeyboardButton(f"ًں“© ظ…ط±ط§ط¬ط¹ط© ط§ظ„ط§ظ‚طھط±ط§ط­ط§طھ ({count})", callback_data='review_suggestions')])
    
    # ط§ظ„طµظپ ط§ظ„ط£ظˆظ„: ط²ط± "ط§ط¨ط¯ط£ ط¥ط¶ط§ظپط© ظ…ظˆظ‚ط¹" ظˆط¨ط¬ط§ظ†ط¨ظ‡ ط²ط± "ط§ظ„ط¨ط­ط«"
    keyboard.append([
        InlineKeyboardButton("ط§ط¨ط¯ط£ ط¥ط¶ط§ظپط© ظ…ظˆظ‚ط¹ â–¶ï¸ڈ", callback_data='start_add'),
        InlineKeyboardButton("ط§ظ„ط¨ط­ط« ًں”چ", callback_data='search')
    ])
    
    # ط§ظ„طµظپ ط§ظ„ط«ط§ظ†ظٹ: ط²ط± "ط¥ط¯ط§ط±ط© ط§ظ„ظ…ط³ط¤ظˆظ„ظٹظ†" ظˆط¨ط¬ط§ظ†ط¨ظ‡ ط²ط± "ط¥ط¯ط§ط±ط© ط§ظ„ط£ط¬ظ‡ط²ط©"
    row2 = []
    if update.effective_user.id == 1156962576:
        row2.append(InlineKeyboardButton("ًں‘¥ ط¥ط¯ط§ط±ط© ط§ظ„ظ…ط³ط¤ظˆظ„ظٹظ†", callback_data='manage_admins'))
    row2.append(InlineKeyboardButton("ًں“± ط¥ط¯ط§ط±ط© ط§ظ„ط£ط¬ظ‡ط²ط©", callback_data='manage_devices'))
    keyboard.append(row2)
    
    # ط§ظ„طµظپ ط§ظ„ط«ط§ظ„ط«: ط²ط± "طھط؛ظٹظٹط± ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط±" ظˆط²ط± "طھطµط¯ظٹط± ط§ظ„ط¨ظٹط§ظ†ط§طھ" ظپظٹ طµظپ ظˆط§ط­ط¯ ط¬ظ†ط¨ط§ظ‹ ط¥ظ„ظ‰ ط¬ظ†ط¨
    keyboard.append([
        InlineKeyboardButton("ًں”‘ طھط؛ظٹظٹط± ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط±", callback_data='change_site_password'),
        InlineKeyboardButton("طھطµط¯ظٹط± ط§ظ„ط¨ظٹط§ظ†ط§طھ ًں“¤", callback_data='export_data')
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    start_text = (
        "ًں“‹ *ط§ظ„ظ‚ط§ط¦ظ…ط© ط§ظ„ط±ط¦ظٹط³ظٹط© â€” ط§ط®طھط± ط£ط­ط¯ ط§ظ„ط®ظٹط§ط±ط§طھ ط§ظ„طھط§ظ„ظٹط©:* \n"
        "â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(start_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(start_text, reply_markup=reply_markup, parse_mode='Markdown')
    return NAMEˆط± ط§ظ„ط¬ط¯ظٹط¯ط© ظپظٹ ظ‚ط§ط¹ط¯ط© ط§ظ„ط¨ظٹط§ظ†ط§طھ.",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("â‌Œ ط­ط¯ط« ط®ط·ط£ ط£ط«ظ†ط§ط، ط­ظپط¸ ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ط¬ط¯ظٹط¯ط©.", reply_markup=keyboard)
    return NAME

# --- ظ…ط¹ط§ظ„ط¬ط§طھ ط§ظ„ط£ظˆط§ظ…ط± ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    logger.info(f"ط¨ط¯ط، ط§ظ„ظ…ط­ط§ط¯ط«ط© ظ…ط¹ ط§ظ„ظ…ط³طھط®ط¯ظ… {update.effective_user.id}")
    
    from db import fetch_pending_suggestions
    suggestions = fetch_pending_suggestions()
    count = len(suggestions)
    
    keyboard = []
    if count > 0:
        keyboard.append([InlineKeyboardButton(f"ًں“© ظ…ط±ط§ط¬ط¹ط© ط§ظ„ط§ظ‚طھط±ط§ط­ط§طھ ({count})", callback_data='review_suggestions')])
    
    # ط§ظ„طµظپ ط§ظ„ط£ظˆظ„: ط²ط± "ط§ط¨ط¯ط£ ط¥ط¶ط§ظپط© ظ…ظˆظ‚ط¹" ظˆط¨ط¬ط§ظ†ط¨ظ‡ ط²ط± "ط§ظ„ط¨ط­ط«"
    keyboard.append([
        InlineKeyboardButton("ط§ط¨ط¯ط£ ط¥ط¶ط§ظپط© ظ…ظˆظ‚ط¹ â–¶ï¸ڈ", callback_data='start_add'),
        InlineKeyboardButton("ط§ظ„ط¨ط­ط« ًں”چ", callback_data='search')
    ])
    
    # ط§ظ„طµظپ ط§ظ„ط«ط§ظ†ظٹ: ط²ط± "ط¥ط¯ط§ط±ط© ط§ظ„ظ…ط³ط¤ظˆظ„ظٹظ†" ظˆط¨ط¬ط§ظ†ط¨ظ‡ ط²ط± "ط¥ط¯ط§ط±ط© ط§ظ„ط£ط¬ظ‡ط²ط©"
    row2 = []
    if update.effective_user.id == 1156962576:
        row2.append(InlineKeyboardButton("ًں‘¥ ط¥ط¯ط§ط±ط© ط§ظ„ظ…ط³ط¤ظˆظ„ظٹظ†", callback_data='manage_admins'))
    row2.append(InlineKeyboardButton("ًں“± ط¥ط¯ط§ط±ط© ط§ظ„ط£ط¬ظ‡ط²ط©", callback_data='manage_devices'))
    keyboard.append(row2)
    
    # ط§ظ„طµظپ ط§ظ„ط«ط§ظ„ط«: ط²ط± "طھط؛ظٹظٹط± ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط±" (ظ„ظˆط­ط¯ظ‡ ظپظٹ ط§ظ„ظ…ظ†طھطµظپ)
    keyboard.append([InlineKeyboardButton("ًں”‘ طھط؛ظٹظٹط± ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط±", callback_data='change_site_password')])
    
    # ط§ظ„طµظپ ط§ظ„ط±ط§ط¨ط¹: ط²ط± "طھطµط¯ظٹط± ط§ظ„ط¨ظٹط§ظ†ط§طھ" (ظ„ظˆط­ط¯ظ‡ ظپظٹ ط§ظ„ظ…ظ†طھطµظپ)
    keyboard.append([InlineKeyboardButton("طھطµط¯ظٹط± ط§ظ„ط¨ظٹط§ظ†ط§طھ ًں“¤", callback_data='export_data')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    start_text = (
        "ًں“‹ *ط§ظ„ظ‚ط§ط¦ظ…ط© ط§ظ„ط±ط¦ظٹط³ظٹط© â€” ط§ط®طھط± ط£ط­ط¯ ط§ظ„ط®ظٹط§ط±ط§طھ ط§ظ„طھط§ظ„ظٹط©:* \n"
        "â•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گâ•گ"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(start_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(start_text, reply_markup=reply_markup, parse_mode='Markdown')
    return NAME

# --- ط¯ط§ظ„ط© ظ…ط³ط§ط¹ط¯ط© ظ„ط¹ط±ط¶ ط§ظ‚طھط±ط§ط­ ---
async def show_suggestion(query, context, prefix=""):
    """ط¹ط±ط¶ ط§ظ‚طھط±ط§ط­ ط¨ط§ظ„ظپظ‡ط±ط³ ط§ظ„ط­ط§ظ„ظٹ ظ…ط¹ ط£ط²ط±ط§ط± ط§ظ„طھظ†ظ‚ظ„ ظˆظƒط´ظپ ط§ظ„طھظƒط±ط§ط±"""
    suggestions = context.user_data.get('suggestions_list', [])
    idx = context.user_data.get('sug_index', 0)
    total = len(suggestions)
    
    if not suggestions or idx >= total:
        await query.edit_message_text("ًں“­ ظ„ط§ ظٹظˆط¬ط¯ ط§ظ‚طھط±ط§ط­ط§طھ ظ…ط¹ظ„ظ‚ط©.")
        return
    
    sug = suggestions[idx]
    website = sug.get('website', '')
    
    text = (f"{prefix}ًں“© ط§ظ‚طھط±ط§ط­ ({idx + 1}/{total}):\n\n"
            f"ًںŒگ ط§ظ„ظ…ظˆظ‚ط¹: {escape_md(website)}\n"
            f"ًں“‚ ط§ظ„طھطµظ†ظٹظپ: {escape_md(sug.get('main_category', ''))} > {escape_md(sug.get('sub_category', 'ط؛ظٹط± ظ…ط­ط¯ط¯'))}\n"
            f"ًں“‌ ط§ظ„ظˆطµظپ: {escape_md(sug.get('description', ''))}\n"
            f"ًں’، ط§ظ„ظپط§ط¦ط¯ط©: {escape_md(sug.get('benefit', 'ظ„ط§ ظٹظˆط¬ط¯'))}")
    
    # --- ظƒط´ظپ ط§ظ„طھظƒط±ط§ط± ---
    duplicates = check_duplicate(website)
    has_duplicate = bool(duplicates)
    
    if has_duplicate:
        dup = duplicates[0]  # ط£ظˆظ„ طھط·ط§ط¨ظ‚
        dup_main_ar = CATEGORY_TRANSLATION.get(dup.get('main_category', ''), dup.get('main_category', ''))
        dup_sub_ar = SUB_CATEGORY_TRANSLATION.get(dup.get('sub_category', ''), dup.get('sub_category', ''))
        text += (
            f"\n\nâڑ ï¸ڈ *ظ‡ط°ط§ ط§ظ„ظ…ظˆظ‚ط¹ ظ…ظˆط¬ظˆط¯ ظ…ط³ط¨ظ‚ط§ظ‹ ظپظٹ ظ‚ط§ط¹ط¯ط© ط§ظ„ط¨ظٹط§ظ†ط§طھ!*\n"
            f"â‍–â‍–â‍–â‍–â‍–â‍–â‍–â‍–\n"
            f"ًں“Œ *ط§ظ„ظ…ظˆظ‚ط¹ ط§ظ„ظ…ظˆط¬ظˆط¯:*\n"
            f"ًںŒگ ط§ظ„ط§ط³ظ…/ط§ظ„ط±ط§ط¨ط·: {escape_md(dup.get('website', 'ظ„ط§ ظٹظˆط¬ط¯'))}\n"
            f"ًں“‚ ط§ظ„طھطµظ†ظٹظپ: {escape_md(dup_main_ar)} \\> {escape_md(dup_sub_ar)}\n"
            f"ًں“‌ ط§ظ„ظˆطµظپ: {escape_md(dup.get('description', 'ظ„ط§ ظٹظˆط¬ط¯'))}\n"
            f"ًں’، ط§ظ„ظپط§ط¦ط¯ط©: {escape_md(dup.get('benefit', 'ظ„ط§ ظٹظˆط¬ط¯'))}"
        )
        # ط­ظپط¸ ط¨ظٹط§ظ†ط§طھ ط§ظ„ظ…ظˆظ‚ط¹ ط§ظ„ظ…ظˆط¬ظˆط¯ ظ„ط§ط³طھط®ط¯ط§ظ…ظ‡ط§ ظ„ط§ط­ظ‚ط§ظ‹ ط¹ظ†ط¯ طھط¹ط¯ظٹظ„ظ‡
        context.user_data['dup_existing_site'] = dup
    else:
        context.user_data.pop('dup_existing_site', None)
    
    # --- ط¨ظ†ط§ط، ط§ظ„ط£ط²ط±ط§ط± ---
    row1 = [
        InlineKeyboardButton("âœ… ظ…ظˆط§ظپظ‚ط©", callback_data=f"app_{sug['id']}"),
        InlineKeyboardButton("â‌Œ ط±ظپط¶", callback_data=f"rej_{sug['id']}")
    ]
    
    rows = [row1]
    
    # ط¯ظ…ط¬ ط£ط²ط±ط§ط± ط§ظ„طھط¹ط¯ظٹظ„ ظپظٹ طµظپ ظˆط§ط­ط¯ ظ„طھط¬ظ†ط¨ ظ‚طµ ط§ظ„ظ†طµ ط¹ظ„ظ‰ ط§ظ„طھظ„ظپظˆظ†
    if has_duplicate:
        rows.append([
            InlineKeyboardButton("âœڈï¸ڈ طھط¹ط¯ظٹظ„ ط§ظ„ط§ظ‚طھط±ط§ط­", callback_data=f"sug_edit_{sug['id']}"),
            InlineKeyboardButton("ًں”§ طھط¹ط¯ظٹظ„ ط§ظ„ظ…ظˆط¬ظˆط¯", callback_data=f"dup_edit_{sug['id']}")
        ])
    else:
        rows.append([InlineKeyboardButton("âœڈï¸ڈ طھط¹ط¯ظٹظ„ ط§ظ„ط§ظ‚طھط±ط§ط­", callback_data=f"sug_edit_{sug['id']}")])
    
    # ط£ط²ط±ط§ط± ط§ظ„طھظ†ظ‚ظ„
    nav_buttons = []
    if idx > 0:
        nav_buttons.append(InlineKeyboardButton("â—€ï¸ڈ ط§ظ„ط³ط§ط¨ظ‚", callback_data="sug_prev"))
    if idx < total - 1:
        nav_buttons.append(InlineKeyboardButton("ط§ظ„طھط§ظ„ظٹ â–¶ï¸ڈ", callback_data="sug_next"))
    if nav_buttons:
        rows.append(nav_buttons)
    
    rows.append([InlineKeyboardButton("ًںڈ  ط±ط¬ظˆط¹ ظ„ظ„ظ‚ط§ط¦ظ…ط©", callback_data='main_menu')])
    
    keyboard = InlineKeyboardMarkup(rows)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

# --- ظ…ط¹ط§ظ„ط¬ط© ط§ظ„ظ†ظ‚ط± ط¹ظ„ظ‰ ط§ظ„ط²ط± ---
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    logger.info(f"ط§ط³طھظ‚ط¨ط§ظ„ callback_query: {query.data} ظ…ظ† ط§ظ„ظ…ط³طھط®ط¯ظ… {update.effective_user.id}")
    await query.answer()

    if query.data == 'start_add':
        context.user_data.clear()
        await query.edit_message_text("ًں“‌ ط§ط³ظ… ط§ظ„ظ…ظˆظ‚ط¹ ط£ظˆ ط§ظ„ط±ط§ط¨ط·:")
        return NAME
    elif query.data == 'main_menu':
        context.user_data.clear()
        return await start(update, context)
    elif query.data in ['manage_devices', 'manage_access']:
        return await handle_manage_devices(update, context)
    elif query.data.startswith("ask_del_ip:"):
        target_ip = query.data.split("ask_del_ip:")[1]
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("âœ… ظ†ط¹ظ…طŒ ط§ط­ط°ظپ ط§ظ„ط¬ظ‡ط§ط²", callback_data=f"confirm_del_ip:{target_ip}")],
            [InlineKeyboardButton("â‌Œ ط¥ظ„ط؛ط§ط،", callback_data='manage_devices')]
        ])
        await query.edit_message_text(
            f"âڑ ï¸ڈ *طھط£ظƒظٹط¯ ط­ط°ظپ ط§ظ„ط¬ظ‡ط§ط²/IP*\n\n"
            f"ظ‡ظ„ ط£ظ†طھ طھط£ظƒط¯ ظ…ظ† ط±ط؛ط¨طھظƒ ظپظٹ ط­ط°ظپ ظˆطµظ„ط§ط­ظٹط© ط§ظ„ط¬ظ‡ط§ط² ط§ظ„طھط§ظ„ظٹط©:\n`{target_ip}`طں",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return NAME
    elif query.data.startswith("confirm_del_ip:"):
        from db import remove_allowed_ip
        target_ip = query.data.split("confirm_del_ip:")[1]
        success = remove_allowed_ip(target_ip)
        if success:
            await query.answer(f"âœ… طھظ… ط­ط°ظپ ط§ظ„ط¬ظ‡ط§ط² {target_ip} ط¨ظ†ط¬ط§ط­", show_alert=True)
        else:
            await query.answer("â‌Œ ط­ط¯ط« ط®ط·ط£ ط£ط«ظ†ط§ط، ط­ط°ظپ ط§ظ„ط¬ظ‡ط§ط²", show_alert=True)
        return await handle_manage_devices(update, context)
    elif query.data.startswith("block_dev:"):
        from db import set_device_block_status
        target_id = query.data.split("block_dev:")[1]
        set_device_block_status(target_id, True)
        await query.answer("â›” طھظ… ط­ط¸ط± ط§ظ„ط¬ظ‡ط§ط² ط¨ظ†ط¬ط§ط­", show_alert=True)
        return await handle_manage_devices(update, context)
    elif query.data.startswith("unblock_dev:"):
        from db import set_device_block_status
        target_id = query.data.split("unblock_dev:")[1]
        set_device_block_status(target_id, False)
        await query.answer("ًں”“ طھظ… ظپظƒ ط§ظ„ط­ط¸ط± ط¹ظ† ط§ظ„ط¬ظ‡ط§ط² ط¨ظ†ط¬ط§ط­", show_alert=True)
        return await handle_manage_devices(update, context)
    elif query.data == 'add_ip':
        await query.edit_message_text(
            "â‍• **ط¥ط¶ط§ظپط© ط¬ظ‡ط§ط² / IP ط¬ط¯ظٹط¯**\n\n"
            "ط£ط¯ط®ظ„ ط¹ظ†ظˆط§ظ† ط§ظ„ظ€ IP ط§ظ„ظ…ط³ظ…ظˆط­ ظ„ظ‡ ط¨ط§ظ„ط¯ط®ظˆظ„ (ظ…ط«ط§ظ„: `203.0.113.45`):\n\n"
            "ط£ظˆ ط£ط±ط³ظ„ /start ظ„ظ„ط¥ظ„ط؛ط§ط، ظˆط§ظ„ط¹ظˆط¯ط© ظ„ظ„ظ‚ط§ط¦ظ…ط©.",
            parse_mode='Markdown'
        )
        return ADD_IP_STATE
    elif query.data == 'change_site_password':
        return await start_password_change_flow(update, context)
        
    # --- ظ‚ط³ظ… ط§ظ„ط§ظ‚طھط±ط§ط­ط§طھ ---
    elif query.data == 'review_suggestions':
        from db import fetch_pending_suggestions
        suggestions = fetch_pending_suggestions()
        if not suggestions:
            await query.edit_message_text("ًں“­ ظ„ط§ ظٹظˆط¬ط¯ ط§ظ‚طھط±ط§ط­ط§طھ ظ…ط¹ظ„ظ‚ط© ط­ط§ظ„ظٹط§ظ‹.")
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
            await query.edit_message_text("âڑ ï¸ڈ ظ„ظ… ظٹطھظ… ط§ظ„ط¹ط«ظˆط± ط¹ظ„ظ‰ ط§ظ„ط§ظ‚طھط±ط§ط­.")
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
            # طھط­ط¯ظٹط« ط§ظ„ظ‚ط§ط¦ظ…ط© ظˆط¹ط±ط¶ ط§ظ„طھط§ظ„ظٹ
            updated = fetch_pending_suggestions()
            context.user_data['suggestions_list'] = updated
            if updated:
                context.user_data['sug_index'] = 0
                await show_suggestion(query, context, prefix="âœ… طھظ… ظ‚ط¨ظˆظ„ ظˆط¥ط¶ط§ظپط© ط§ظ„ظ…ظˆظ‚ط¹!\n\n")
            else:
                await query.edit_message_text("âœ… طھظ… ظ‚ط¨ظˆظ„ ظˆط¥ط¶ط§ظپط© ط§ظ„ظ…ظˆظ‚ط¹!\n\nًں“­ ظ„ط§ ظٹظˆط¬ط¯ ط§ظ‚طھط±ط§ط­ط§طھ ط£ط®ط±ظ‰ ظ…ط¹ظ„ظ‚ط©.")
                await asyncio.sleep(1)
                return await start(update, context)
            return NAME
        else:
            context.user_data['name'] = sug.get('website', '')
            context.user_data['description'] = sug.get('description', '')
            context.user_data['benefit'] = sug.get('benefit', '')
            
            options = list(CATEGORIES.keys())
            reply_markup = build_main_category_keyboard(options)
            await query.edit_message_text(f"طھظ… ظ‚ط¨ظˆظ„ {sug.get('website', '')}!\n\nâڑ ï¸ڈ ط§ظ„طھطµظ†ظٹظپط§طھ ظ„ظ… طھطھط¹ط±ظپ طھظ„ظ‚ط§ط¦ظٹط§ظ‹.\nًں“‚ ظٹط±ط¬ظ‰ ط§ط®طھظٹط§ط± ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ ظ„ط¥ط¶ط§ظپطھظ‡:", reply_markup=reply_markup)
            return MAIN_CATEGORY

    elif query.data.startswith("rej_"):
        from db import update_suggestion_status, fetch_pending_suggestions
        sug_id = query.data.split("_")[1]
        update_suggestion_status(sug_id, "rejected")
        
        # طھط­ط¯ظٹط« ط§ظ„ظ‚ط§ط¦ظ…ط© ظˆط¹ط±ط¶ ط§ظ„طھط§ظ„ظٹ
        updated = fetch_pending_suggestions()
        context.user_data['suggestions_list'] = updated
        if updated:
            context.user_data['sug_index'] = 0
            await show_suggestion(query, context, prefix="âœ… طھظ… ط§ظ„ط±ظپط¶!\n\n")
        else:
            await query.edit_message_text("âœ… طھظ… ط§ظ„ط±ظپط¶!\n\nًں“­ ظ„ط§ ظٹظˆط¬ط¯ ط§ظ‚طھط±ط§ط­ط§طھ ط£ط®ط±ظ‰ ظ…ط¹ظ„ظ‚ط©.")
            await asyncio.sleep(1)
            return await start(update, context)
        return NAME

    elif query.data.startswith("sug_edit_"):
        sug_id = query.data.split("sug_edit_")[1]
        suggestions = context.user_data.get('suggestions_list', [])
        sug = next((s for s in suggestions if str(s['id']) == sug_id), None)
        if not sug:
            await query.edit_message_text("âڑ ï¸ڈ ظ„ظ… ظٹطھظ… ط§ظ„ط¹ط«ظˆط± ط¹ظ„ظ‰ ط§ظ„ط§ظ‚طھط±ط§ط­.")
            await asyncio.sleep(1)
            return await start(update, context)
        
        # ط­ظپط¸ ط¨ظٹط§ظ†ط§طھ ط§ظ„ط§ظ‚طھط±ط§ط­ ظ„ظ„طھط¹ط¯ظٹظ„
        context.user_data['editing_suggestion_id'] = sug_id
        context.user_data['edit_old_name'] = sug.get('website', '')
        context.user_data['edit_old_description'] = sug.get('description', '')
        context.user_data['edit_old_benefit'] = sug.get('benefit', '')
        context.user_data['editing_mode'] = 'suggestion'
        
        old_name = sug.get('website', '')
        await query.edit_message_text(
            f"âœڈï¸ڈ **طھط¹ط¯ظٹظ„ ط¨ظٹط§ظ†ط§طھ ط§ظ„ط§ظ‚طھط±ط§ط­**\n\n"
            f"ًں“‌ **ط§ظ„ط§ط³ظ…/ط§ظ„ط±ط§ط¨ط· ط§ظ„ط­ط§ظ„ظٹ:**\n`{old_name}`\n\n"
            f"ط£ط¯ط®ظ„ ط§ظ„ط§ط³ظ… ط§ظ„ط¬ط¯ظٹط¯ ط£ظˆ ط£ط±ط³ظ„ **-** ظ„ظ„ط¥ط¨ظ‚ط§ط، ط¹ظ„ظ‰ ط§ظ„ط­ط§ظ„ظٹ:",
            parse_mode='Markdown'
        )
        return EDIT_NAME

    elif query.data.startswith("dup_edit_"):
        # طھط¹ط¯ظٹظ„ ط§ظ„ظ…ظˆظ‚ط¹ ط§ظ„ظ…ظˆط¬ظˆط¯ (ط§ظ„ظ…ظƒط±ط±) ظپظٹ ظ‚ط§ط¹ط¯ط© ط§ظ„ط¨ظٹط§ظ†ط§طھ
        dup = context.user_data.get('dup_existing_site')
        if not dup:
            await query.answer("âڑ ï¸ڈ ظ„ظ… ظٹطھظ… ط§ظ„ط¹ط«ظˆط± ط¹ظ„ظ‰ ط¨ظٹط§ظ†ط§طھ ط§ظ„ظ…ظˆظ‚ط¹ ط§ظ„ظ…ظˆط¬ظˆط¯.", show_alert=True)
            return NAME
        
        # طھط¬ظ‡ظٹط² ط¨ظٹط§ظ†ط§طھ ط§ظ„ظ…ظˆظ‚ط¹ ط§ظ„ظ…ظˆط¬ظˆط¯ ظ„ظ„طھط¹ط¯ظٹظ„
        context.user_data['edit_old_name'] = dup.get('website', '')
        context.user_data['edit_old_description'] = dup.get('description', '')
        context.user_data['edit_old_benefit'] = dup.get('benefit', '')
        context.user_data['edit_main_category_en'] = dup.get('main_category', '')
        context.user_data['edit_sub_category_en'] = dup.get('sub_category', '')
        context.user_data['editing_mode'] = 'site'
        # ط­ظپط¸ ظ…ط¤ط´ط± ط§ظ„ط§ظ‚طھط±ط§ط­ ظ„ظ„ط¹ظˆط¯ط© ط¥ظ„ظٹظ‡ ظ„ط§ط­ظ‚ط§ظ‹
        context.user_data['return_to_suggestions'] = True
        
        old_name = dup.get('website', '')
        dup_main_ar = CATEGORY_TRANSLATION.get(dup.get('main_category', ''), dup.get('main_category', ''))
        dup_sub_ar = SUB_CATEGORY_TRANSLATION.get(dup.get('sub_category', ''), dup.get('sub_category', ''))
        
        text = (
            f"ًں”§ طھط¹ط¯ظٹظ„ ط§ظ„ظ…ظˆظ‚ط¹ ط§ظ„ظ…ظˆط¬ظˆط¯\n\n"
            f"ًں“‚ ط§ظ„طھطµظ†ظٹظپ: {dup_main_ar} > {dup_sub_ar}\n\n"
            f"ًں“‌ ط§ظ„ط§ط³ظ…/ط§ظ„ط±ط§ط¨ط· ط§ظ„ط­ط§ظ„ظٹ:\n{old_name}\n\n"
            f"ط£ط¯ط®ظ„ ط§ظ„ط§ط³ظ… ط§ظ„ط¬ط¯ظٹط¯ ط£ظˆ ط£ط±ط³ظ„ - ظ„ظ„ط¥ط¨ظ‚ط§ط، ط¹ظ„ظ‰ ط§ظ„ط­ط§ظ„ظٹ:"
        )
        
        try:
            await query.edit_message_text(text)
        except Exception as e:
            logger.error(f"Error editing message in dup_edit_: {e}")
            await query.message.reply_text(text)
            
        return EDIT_NAME
    
    # --- ظ‚ط³ظ… ط¥ط¯ط§ط±ط© ط§ظ„ظ…ط³ط¤ظˆظ„ظٹظ† ---
    elif query.data == 'manage_admins':
        if update.effective_user.id != 1156962576:
            await query.edit_message_text("â›” ظپظ‚ط· ط§ظ„ظ…ط§ظ„ظƒ ظٹظ…ظƒظ†ظ‡ ط¥ط¯ط§ط±ط© ط§ظ„ظ…ط³ط¤ظˆظ„ظٹظ†")
            await asyncio.sleep(1)
            return await start(update, context)
        
        admins = fetch_all_admins()
        text = "ًں‘¥ **ط¥ط¯ط§ط±ط© ط§ظ„ظ…ط³ط¤ظˆظ„ظٹظ†**\n\n"
        if admins:
            for i, admin in enumerate(admins, 1):
                owner_badge = " ًں‘‘" if admin.get('telegram_id') == 1156962576 else ""
                text += f"{i}. {escape_md(admin.get('name', 'ط؛ظٹط± ظ…ط¹ط±ظپ'))} (`{admin.get('telegram_id', '?')}`){owner_badge}\n"
        else:
            text += "ظ„ط§ ظٹظˆط¬ط¯ ظ…ط³ط¤ظˆظ„ظˆظ† ظ…ط³ط¬ظ„ظˆظ† ط­ط§ظ„ظٹط§ظ‹.\n"
        
        text += "\nâ”پâ”پâ”پâ”پâ”پâ”پâ”پâ”پâ”پâ”پâ”پâ”پâ”پâ”پâ”پâ”پâ”پâ”پ\n"
        text += "ًں“Œ **ظƒظٹظپظٹط© ط¥ط¶ط§ظپط© ظ…ط³ط¤ظˆظ„ ط¬ط¯ظٹط¯:**\n"
        text += "1ï¸ڈâƒ£ ط£ط±ط³ظ„ ظ„طµط¯ظٹظ‚ظƒ ط±ط§ط¨ط· ط§ظ„ط¨ظˆطھ: @userinfobot\n"
        text += "2ï¸ڈâƒ£ ط§ط·ظ„ط¨ ظ…ظ†ظ‡ ظٹظپطھط­ظ‡ ظˆظٹط±ط³ظ„ ط£ظٹ ط±ط³ط§ظ„ط©\n"
        text += "3ï¸ڈâƒ£ ط³ظٹط¸ظ‡ط± ظ„ظ‡ ط±ظ‚ظ… `Id:` â€” ظ‡ط°ط§ ظ‡ظˆ ط§ظ„ظ€ Telegram ID\n"
        text += "4ï¸ڈâƒ£ ظٹط±ط³ظ„ ظ„ظƒ ظ‡ط°ط§ ط§ظ„ط±ظ‚ظ…\n"
        text += "5ï¸ڈâƒ£ ط§ط¶ط؛ط· â‍• ط¥ط¶ط§ظپط© ظ…ط³ط¤ظˆظ„ ظˆط£ط¯ط®ظ„ ط§ظ„ط±ظ‚ظ…\n"
        text += "âœ… **ط¨ط¹ط¯ظ‡ط§ ط³ظٹط¹ظ…ظ„ ط§ظ„ط¨ظˆطھ ظ…ط¹ظ‡ ظ…ط¨ط§ط´ط±ط©!**\n\n"
        text += "ًں—‘ï¸ڈ **ظƒظٹظپظٹط© ط­ط°ظپ ظ…ط³ط¤ظˆظ„:**\n"
        text += "ط§ط¶ط؛ط· ط­ط°ظپ ظ…ط³ط¤ظˆظ„ ظˆط§ط®طھط± ط§ظ„ط´ط®طµ ط§ظ„ظ…ط±ط§ط¯ ط­ط°ظپظ‡."
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("â‍• ط¥ط¶ط§ظپط© ظ…ط³ط¤ظˆظ„", callback_data='add_admin_start'),
             InlineKeyboardButton("ًں—‘ï¸ڈ ط­ط°ظپ ظ…ط³ط¤ظˆظ„", callback_data='del_admin_list')],
            [InlineKeyboardButton("ًںڈ  ط§ظ„ظ‚ط§ط¦ظ…ط© ط§ظ„ط±ط¦ظٹط³ظٹط©", callback_data='main_menu')]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return NAME
    
    elif query.data == 'add_admin_start':
        await query.edit_message_text("âœڈï¸ڈ ط£ط¯ط®ظ„ ط±ظ‚ظ… **Telegram ID** ظ„ظ„ط´ط®طµ ط§ظ„ط°ظٹ طھط±ظٹط¯ ط¥ط¶ط§ظپطھظ‡ ظƒظ…ط³ط¤ظˆظ„:\n\n(ظٹظ…ظƒظ†ظ‡ ظ…ط¹ط±ظپط© ط±ظ‚ظ…ظ‡ ط¨ط¥ط±ط³ط§ظ„ ط£ظٹ ط±ط³ط§ظ„ط© ظ„ط¨ظˆطھ @userinfobot)", parse_mode='Markdown')
        context.user_data['awaiting_admin_id'] = True
        return ADD_ADMIN_STATE
    
    elif query.data == 'del_admin_list':
        admins = fetch_all_admins()
        admins = [a for a in admins if a.get('telegram_id') != 1156962576]  # ظ„ط§ طھط³ظ…ط­ ط¨ط­ط°ظپ ط§ظ„ظ…ط§ظ„ظƒ
        if not admins:
            await query.edit_message_text("âœ… ظ„ط§ ظٹظˆط¬ط¯ ظ…ط³ط¤ظˆظ„ظˆظ† ظٹظ…ظƒظ† ط­ط°ظپظ‡ظ….")
            await asyncio.sleep(1)
            return await start(update, context)
        
        keyboard = []
        for admin in admins:
            name = admin.get('name', 'ط؛ظٹط± ظ…ط¹ط±ظپ')
            tid = admin.get('telegram_id', '?')
            keyboard.append([InlineKeyboardButton(f"â‌Œ {name} ({tid})", callback_data=f"rmadm_{tid}")])
        keyboard.append([InlineKeyboardButton("ط±ط¬ظˆط¹ â¬…ï¸ڈ", callback_data='manage_admins')])
        
        await query.edit_message_text("ط§ط®طھط± ط§ظ„ظ…ط³ط¤ظˆظ„ ط§ظ„ط°ظٹ طھط±ظٹط¯ ط­ط°ظپظ‡:", reply_markup=InlineKeyboardMarkup(keyboard))
        return NAME
    
    elif query.data.startswith("rmadm_"):
        from db import remove_admin
        tid = int(query.data.split("_")[1])
        if remove_admin(tid):
            await query.answer(f"âœ… طھظ… ط­ط°ظپ ط§ظ„ظ…ط³ط¤ظˆظ„ {tid} ط¨ظ†ط¬ط§ط­", show_alert=True)
        else:
            await query.answer("âڑ ï¸ڈ ط­ط¯ط« ط®ط·ط£ ط£ط«ظ†ط§ط، ط§ظ„ط­ط°ظپ", show_alert=True)
        # ط¹ط±ط¶ ظ‚ط§ط¦ظ…ط© ط§ظ„ظ…ط³ط¤ظˆظ„ظٹظ† ط§ظ„ظ…ط­ط¯ط«ط© ظ…ط¨ط§ط´ط±ط©
        admins = fetch_all_admins()
        text = "ًں‘¥ **ط¥ط¯ط§ط±ط© ط§ظ„ظ…ط³ط¤ظˆظ„ظٹظ†**\n\n"
        if admins:
            for i, admin in enumerate(admins, 1):
                owner_badge = " ًں‘‘" if admin.get('telegram_id') == 1156962576 else ""
                text += f"{i}. {escape_md(admin.get('name', 'ط؛ظٹط± ظ…ط¹ط±ظپ'))} (`{admin.get('telegram_id', '?')}`){owner_badge}\n"
        else:
            text += "ظ„ط§ ظٹظˆط¬ط¯ ظ…ط³ط¤ظˆظ„ظˆظ† ظ…ط³ط¬ظ„ظˆظ† ط­ط§ظ„ظٹط§ظ‹.\n"
        text += "\nâœ… طھظ… طھط­ط¯ظٹط« ط§ظ„ظ‚ط§ط¦ظ…ط©."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("â‍• ط¥ط¶ط§ظپط© ظ…ط³ط¤ظˆظ„", callback_data='add_admin_start'),
             InlineKeyboardButton("ًں—‘ï¸ڈ ط­ط°ظپ ظ…ط³ط¤ظˆظ„", callback_data='del_admin_list')],
            [InlineKeyboardButton("ًںڈ  ط§ظ„ظ‚ط§ط¦ظ…ط© ط§ظ„ط±ط¦ظٹط³ظٹط©", callback_data='main_menu')]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return NAME
    # ----------------------
    elif query.data == 'export_data':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("طھطµط¯ظٹط± ط§ظ„ظƒظ„ (ظƒظ„ ط§ظ„ظ…ظˆط§ظ‚ط¹) ًں“¦", callback_data='export_all')],
            [InlineKeyboardButton("ظپظ„طھط±ط© ط°ظƒظٹط© ط¨ظƒظ„ظ…ط© ط¨ط­ط« ًں”چ", callback_data='export_smart')],
            [InlineKeyboardButton("ظپظ„طھط±ط© ط­ط³ط¨ ط§ظ„طھطµظ†ظٹظپ ًں“‚", callback_data='export_category')],
            [InlineKeyboardButton("ط¥ظ„ط؛ط§ط، ًںڑ«", callback_data='main_menu')]
        ])
        await query.edit_message_text("ًں“¥ ط®ظٹط§ط±ط§طھ طھطµط¯ظٹط± ط§ظ„ط¨ظٹط§ظ†ط§طھ:\nط§ط®طھط± ظƒظٹظپ طھط±ظٹط¯ ط§ط³طھط®ط±ط§ط¬ ط§ظ„ط¨ظٹط§ظ†ط§طھ:", reply_markup=keyboard)
        return EXPORT_MENU
    elif query.data == 'export_all':
        await query.edit_message_text("âڈ³ ط¬ط§ط±ظٹ طھط¬ظ‡ظٹط² ظƒظ„ ط§ظ„ط¨ظٹط§ظ†ط§طھ...")
        data = load_site_data()
        flat_data = []
        for main_cat_en, content in data.get('main_categories', {}).items():
            main_cat_ar = CATEGORY_TRANSLATION.get(main_cat_en, main_cat_en)
            for sub_cat_en, sites in content.get('sub_categories', {}).items():
                sub_cat_ar = SUB_CATEGORY_TRANSLATION.get(sub_cat_en, sub_cat_en)
                for site in sites:
                    flat_data.append({
                        "ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ": main_cat_ar,
                        "ط§ظ„طھطµظ†ظٹظپ ط§ظ„ظپط±ط¹ظٹ": sub_cat_ar,
                        "ط§ظ„ظ…ظˆظ‚ط¹": site.get("website", ""),
                        "ط§ظ„ظˆطµظپ": site.get("description", ""),
                        "ط§ظ„ظپط§ط¦ط¯ط©": site.get("benefit", "")
                    })
        await generate_and_send_excel(query.message, flat_data, 'sites_all.xlsx', "âœ… طھظ… ط§ظ„طھطµط¯ظٹط± ط§ظ„ظƒط§ظ…ظ„")
        return await start(update, context)
    elif query.data == 'export_smart':
        await query.edit_message_text("âœچï¸ڈ ط§ظƒطھط¨ ط§ظ„ظƒظ„ظ…ط© ط§ظ„ط§ظپطھطھط§ط­ظٹط© ط£ظˆ ط§ظ„ظپط§ط¦ط¯ط© ط§ظ„طھظٹ طھط¨ط­ط« ط¹ظ†ظ‡ط§ (ظ…ط«ط§ظ„: ظ…ظˆظ†طھط§ط¬طŒ طھطµظ…ظٹظ…طŒ ط°ظƒط§ط، ط§طµط·ظ†ط§ط¹ظٹ):")
        return EXPORT_SMART_SEARCH
    elif query.data == 'export_category':
        main_categories = list(CATEGORIES.keys())
        reply_markup = build_main_category_keyboard(main_categories)
        await query.edit_message_text("ًں“‚ ط§ط®طھط± ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ ط§ظ„ط°ظٹ طھط±ظٹط¯ طھطµط¯ظٹط±ظ‡:", reply_markup=reply_markup)
        return EXPORT_MAIN_CAT_SELECT
    elif query.data == 'search':
        context.user_data.clear()
        await query.edit_message_text("ًں”چ ط§ظƒطھط¨ ظ…ط§ طھط¨ط­ط« ط¹ظ†ظ‡:")
        return SEARCH
    elif query.data.startswith('view_'):
        try:
            index = int(query.data.split('_')[1])
            search_results = context.user_data.get('search_results', [])
            logger.info(f"ظ…ط­ط§ظˆظ„ط© ط¹ط±ط¶ ط§ظ„ظ†طھظٹط¬ط© ط±ظ‚ظ… {index}. ط¹ط¯ط¯ ط§ظ„ظ†طھط§ط¦ط¬: {len(search_results)}")
            if not search_results:
                logger.error("ظ‚ط§ط¦ظ…ط© search_results ظپط§ط±ط؛ط©")
                await query.answer("âڑ ï¸ڈ ط§ظ„ظ†طھط§ط¦ط¬ ط؛ظٹط± ظ…طھظˆظپط±ط©. ط­ط§ظˆظ„ ط§ظ„ط¨ط­ط« ظ…ط±ط© ط£ط®ط±ظ‰.", show_alert=True)
                return await start(update, context)
            if 0 <= index < len(search_results):
                context.user_data['current_result_index'] = index
                result = search_results[index]
                logger.info(f"ط¹ط±ط¶ ط§ظ„ظ†طھظٹط¬ط©: {result['website']}")
                await query.edit_message_text(
                    f"ًں“Œ ط§ظ„ظ†طھظٹط¬ط©:\n\n"
                    f"ط§ظ„ظ…ظˆظ‚ط¹: {result['website']}\n"
                    f"ط§ظ„ظˆطµظپ: {result['description']}\n"
                    f"ط§ظ„ظپط§ط¦ط¯ط©: {result['benefit']}\n"
                    f"ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ: {result['main_category_ar']}\n"
                    f"ط§ظ„طھطµظ†ظٹظپ ط§ظ„ظپط±ط¹ظٹ: {result['sub_category_ar']}",
                    reply_markup=result_options_keyboard()
                )
            else:
                logger.error(f"ط§ظ„ظپظ‡ط±ط³ {index} ط®ط§ط±ط¬ ط§ظ„ظ†ط·ط§ظ‚")
                await query.answer("âڑ ï¸ڈ ط§ظ„ظ†طھظٹط¬ط© ط؛ظٹط± ظ…ظˆط¬ظˆط¯ط©.", show_alert=True)
                return await start(update, context)
        except Exception as e:
            logger.error(f"ط®ط·ط£ ط£ط«ظ†ط§ط، ط¹ط±ط¶ ط§ظ„ظ†طھظٹط¬ط©: {e}")
            await query.answer("âڑ ï¸ڈ ط­ط¯ط« ط®ط·ط£ ط£ط«ظ†ط§ط، ط¹ط±ط¶ ط§ظ„ظ†طھظٹط¬ط©.", show_alert=True)
            return await start(update, context)
    elif query.data == 'back_to_results':
        search_results = context.user_data.get('search_results', [])
        if search_results:
            keyboard = [[InlineKeyboardButton(match['website'], callback_data=f"view_{i}")] for i, match in enumerate(search_results)]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("ًں”چ ط§ط®طھط± ط§ظ„ظ†طھظٹط¬ط© ط§ظ„ظ…ط·ظ„ظˆط¨ط©:", reply_markup=reply_markup)
            return VIEW_RESULT
        else:
            await query.answer("âڑ ï¸ڈ ظ„ط§ طھظˆط¬ط¯ ظ†طھط§ط¦ط¬.", show_alert=True)
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
                f"âœڈï¸ڈ **طھط¹ط¯ظٹظ„ ط§ظ„ظ…ظˆظ‚ط¹**\n\n"
                f"ًں“‌ **ط§ظ„ط§ط³ظ…/ط§ظ„ط±ط§ط¨ط· ط§ظ„ط­ط§ظ„ظٹ:**\n`{escape_md(old_name)}`\n\n"
                f"ط£ط¯ط®ظ„ ط§ظ„ط§ط³ظ… ط§ظ„ط¬ط¯ظٹط¯ ط£ظˆ ط£ط±ط³ظ„ **-** ظ„ظ„ط¥ط¨ظ‚ط§ط، ط¹ظ„ظ‰ ط§ظ„ط­ط§ظ„ظٹ:",
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
                await query.answer("ًں—‘ï¸ڈ طھظ… ط­ط°ظپ ط§ظ„ظ…ظˆظ‚ط¹ ط¨ظ†ط¬ط§ط­.", show_alert=True)
                return await start(update, context)
            else:
                await query.answer("âڑ ï¸ڈ ظپط´ظ„ ظپظٹ ط­ط°ظپ ط§ظ„ظ…ظˆظ‚ط¹.", show_alert=True)
                return await start(update, context)
    elif query.data == 'continue_add':
        # ط§ظ„ظ…طھط§ط¨ط¹ط© ط¨ط¥ط¶ط§ظپط© ظ…ظˆظ‚ط¹ ظ…ظƒط±ط±
        await query.edit_message_text("âœچï¸ڈ ظˆطµظپ ط§ظ„ظ…ظˆظ‚ط¹:")
        return DESCRIPTION
    elif query.data == 'cancel_add':
        context.user_data.clear()
        await query.answer("ًںڑ« طھظ… ط§ظ„ط¥ظ„ط؛ط§ط،.", show_alert=True)
        return await start(update, context)
    return NAME

# --- ظ…ط¹ط§ظ„ط¬ط© ط§ط³ظ… ط§ظ„ظ…ظˆظ‚ط¹ ---
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("âڑ ï¸ڈ ط§ظ„ط±ط¬ط§ط، ط¥ط¯ط®ط§ظ„ ط§ط³ظ… ط§ظ„ظ…ظˆظ‚ط¹ ط£ظˆ ط§ظ„ط±ط§ط¨ط·:")
        return NAME
    context.user_data['name'] = update.message.text.strip()
    logger.info(f"طھظ… ط¥ط¯ط®ط§ظ„ ط§ظ„ط§ط³ظ…: {context.user_data['name']}")

    # ظپط­طµ ط§ظ„طھظƒط±ط§ط± ط§ظ„ظ…ط¨ظƒط±
    duplicates = check_duplicate(context.user_data['name'])
    if duplicates:
        dup_lines = []
        for dup in duplicates:
            dup_main_ar = CATEGORY_TRANSLATION.get(dup.get('main_category', ''), dup.get('main_category', ''))
            dup_sub_ar = SUB_CATEGORY_TRANSLATION.get(dup.get('sub_category', ''), dup.get('sub_category', ''))
            dup_desc = dup.get('description', '')[:60]
            dup_lines.append(f"ًں“‚ {dup_main_ar} > {dup_sub_ar}\nًں“‌ {dup_desc}")

        dup_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("âœ… ظ…طھط§ط¨ط¹ط© ط§ظ„ط¥ط¶ط§ظپط©", callback_data='continue_add'),
             InlineKeyboardButton("â‌Œ ط¥ظ„ط؛ط§ط،", callback_data='cancel_add')]
        ])
        await update.message.reply_text(
            f"âڑ ï¸ڈ ظ‡ط°ط§ ط§ظ„ظ…ظˆظ‚ط¹ ظ…ظˆط¬ظˆط¯ ظ…ط³ط¨ظ‚ط§ظ‹:\n\n"
            + "\n\n".join(dup_lines)
            + "\n\nظ‡ظ„ طھط±ظٹط¯ ط§ظ„ظ…طھط§ط¨ط¹ط© ظˆط¥ط¶ط§ظپطھظ‡ ظپظٹ طھطµظ†ظٹظپ ط¢ط®ط±طں",
            reply_markup=dup_keyboard
        )
        return NAME  # ظٹط¨ظ‚ظ‰ ظپظٹ ظ†ظپط³ ط§ظ„ط­ط§ظ„ط© ط­طھظ‰ ظٹط®طھط§ط± ط§ظ„ظ…ط³طھط®ط¯ظ…

    await update.message.reply_text("âœچï¸ڈ ظˆطµظپ ط§ظ„ظ…ظˆظ‚ط¹:")
    return DESCRIPTION

# --- ظ…ط¹ط§ظ„ط¬ط© ط§ظ„ظˆطµظپ ---
async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("âڑ ï¸ڈ ط§ظ„ط±ط¬ط§ط، ط¥ط¯ط®ط§ظ„ ظˆطµظپ ط§ظ„ظ…ظˆظ‚ط¹:")
        return DESCRIPTION
    context.user_data['description'] = update.message.text.strip()
    logger.info(f"طھظ… ط¥ط¯ط®ط§ظ„ ط§ظ„ظˆطµظپ: {context.user_data['description']}")
    await update.message.reply_text("âœچï¸ڈ ط§ظƒطھط¨ ظپط§ط¦ط¯ط© ط§ظ„ظ…ظˆظ‚ط¹:")
    return BENEFIT

# --- ظ…ط¹ط§ظ„ط¬ط© ط§ظ„ظپط§ط¦ط¯ط© ---
async def get_benefit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("âڑ ï¸ڈ ط§ظ„ط±ط¬ط§ط، ط¥ط¯ط®ط§ظ„ ظپط§ط¦ط¯ط© ط§ظ„ظ…ظˆظ‚ط¹:")
        return BENEFIT
    context.user_data['benefit'] = update.message.text.strip()
    logger.info(f"طھظ… ط¥ط¯ط®ط§ظ„ ط§ظ„ظپط§ط¦ط¯ط©: {context.user_data['benefit']}")
    main_categories = list(CATEGORIES.keys())
    reply_markup = build_main_category_keyboard(main_categories)
    await update.message.reply_text("ًں“‚ ط§ط®طھط± ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ:", reply_markup=reply_markup)
    return MAIN_CATEGORY

# --- ط§ط³طھظ‚ط¨ط§ظ„ ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ ---
async def get_main_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    main_category = query.data
    logger.info(f"طھظ… ط§ط®طھظٹط§ط± ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ: {main_category}")

    if main_category not in CATEGORIES:
        await query.answer("âڑ ï¸ڈ ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ ط؛ظٹط± ظ…ظˆط¬ظˆط¯.", show_alert=True)
        return await start(update, context)

    context.user_data['main_category'] = main_category
    sub_categories = CATEGORIES.get(main_category, [])
    if sub_categories:
        reply_markup = build_keyboard(sub_categories)
        await query.edit_message_text(f"ًں“‚ ط§ط®طھط± ط§ظ„طھطµظ†ظٹظپ ط§ظ„ظپط±ط¹ظٹ ظ„ظ€ {CATEGORY_TRANSLATION.get(main_category, main_category)}:", reply_markup=reply_markup)
        return SUB_CATEGORY
    else:
        context.user_data['sub_category'] = None
        await query.edit_message_text(
            f"âœ… ط§ظ„ط¨ظٹط§ظ†ط§طھ ط§ظ„ظ…ط¯ط®ظ„ط©:\n\n"
            f"ط§ظ„ط§ط³ظ…: {context.user_data['name']}\n"
            f"ط§ظ„ظˆطµظپ: {context.user_data['description']}\n"
            f"ط§ظ„ظپط§ط¦ط¯ط©: {context.user_data['benefit']}\n"
            f"ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ: {CATEGORY_TRANSLATION.get(main_category, main_category)}\n"
            "ظ‡ظ„ طھط±ظٹط¯ ط­ظپط¸ظ‡ط§طں",
            reply_markup=confirm_keyboard
        )
        return CONFIRM

# --- ط§ط³طھظ‚ط¨ط§ظ„ ط§ظ„طھطµظ†ظٹظپ ط§ظ„ظپط±ط¹ظٹ ---
async def get_sub_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    sub_category_en = query.data
    logger.info(f"طھظ… ط§ط®طھظٹط§ط± ط§ظ„طھطµظ†ظٹظپ ط§ظ„ظپط±ط¹ظٹ: {sub_category_en}")

    main_category = context.user_data.get('main_category')
    if not main_category or main_category not in CATEGORIES:
        await query.answer("âڑ ï¸ڈ ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ ط؛ظٹط± ظ…ظˆط¬ظˆط¯.", show_alert=True)
        return await start(update, context)

    sub_categories = CATEGORIES.get(main_category, [])
    if sub_category_en not in sub_categories and sub_categories:
        await query.answer("âڑ ï¸ڈ ط§ظ„طھطµظ†ظٹظپ ط§ظ„ظپط±ط¹ظٹ ط؛ظٹط± ظ…ظˆط¬ظˆط¯.", show_alert=True)
        return await start(update, context)

    context.user_data['sub_category'] = sub_category_en
    main_category_ar = CATEGORY_TRANSLATION.get(main_category, main_category)
    sub_category_ar = SUB_CATEGORY_TRANSLATION.get(sub_category_en, sub_category_en)

    await query.edit_message_text(
        f"âœ… ط§ظ„ط¨ظٹط§ظ†ط§طھ ط§ظ„ظ…ط¯ط®ظ„ط©:\n\n"
        f"ط§ظ„ط§ط³ظ…: {context.user_data['name']}\n"
        f"ط§ظ„ظˆطµظپ: {context.user_data['description']}\n"
        f"ط§ظ„ظپط§ط¦ط¯ط©: {context.user_data['benefit']}\n"
        f"ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ: {main_category_ar}\n"
        f"ط§ظ„طھطµظ†ظٹظپ ط§ظ„ظپط±ط¹ظٹ: {sub_category_ar}\n"
        "ظ‡ظ„ طھط±ظٹط¯ ط­ظپط¸ظ‡ط§طں",
        reply_markup=confirm_keyboard
    )
    return CONFIRM

# --- طھط£ظƒظٹط¯ ط§ظ„ط­ظپط¸ ---
async def confirm_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_response = query.data
    logger.info(f"طھط£ظƒظٹط¯ ط§ظ„ط¨ظٹط§ظ†ط§طھ: {user_response}")

    required_keys = ['name', 'description', 'benefit', 'main_category']
    if not all(key in context.user_data for key in required_keys):
        await query.answer("âڑ ï¸ڈ ظ‡ظ†ط§ظƒ ط®ط·ط£ ظپظٹ ط§ظ„ط¨ظٹط§ظ†ط§طھ.", show_alert=True)
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
        await query.answer("ًں’¾ طھظ… ط§ظ„ط­ظپط¸ ط¨ظ†ط¬ط§ط­.", show_alert=True)
        context.user_data.clear()
        return await start(update, context)
    else:
        await query.answer("ًںڑ« طھظ… ط§ظ„ط¥ظ„ط؛ط§ط،.", show_alert=True)
        context.user_data.clear()
        return await start(update, context)

# --- طھظ†ظپظٹط° ط§ظ„ط¨ط­ط« ---
async def perform_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("âڑ ï¸ڈ ط§ظ„ط±ط¬ط§ط، ط¥ط¯ط®ط§ظ„ ظ†طµ ط§ظ„ط¨ط­ط«:")
        return SEARCH

    search_query = update.message.text.strip()
    logger.info(f"طھظ†ظپظٹط° ط§ظ„ط¨ط­ط« ط¹ظ†: {search_query}")

    # ط±ط³ط§ظ„ط© طھط­ظ…ظٹظ„
    loading_msg = await update.message.reply_text("ًں”چ ط¬ط§ط±ظٹ ط§ظ„ط¨ط­ط«...")

    # ظپظ‡ط±ط³ط© ط§ظ„ط¨ظٹط§ظ†ط§طھ
    indexed_data = index_data()
    
    # طھظ†ظپظٹط° ط§ظ„ط¨ط­ط«
    matches = smart_search(search_query, indexed_data)
    
    if matches:
        context.user_data['search_results'] = matches
        keyboard = [[InlineKeyboardButton(match['website'], callback_data=f"view_{i}")] for i, match in enumerate(matches)]
        keyboard.append([
            InlineKeyboardButton("ًں”چ ط¨ط­ط« ط¬ط¯ظٹط¯", callback_data='search'),
            InlineKeyboardButton("ًںڈ  ط§ظ„ظ‚ط§ط¦ظ…ط©", callback_data='main_menu')
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await loading_msg.edit_text("ًں”چ ط§ط®طھط± ط§ظ„ظ†طھظٹط¬ط© ط§ظ„ظ…ط·ظ„ظˆط¨ط©:", reply_markup=reply_markup)
    else:
        await loading_msg.edit_text("âڑ ï¸ڈ ظ„ط§ طھظˆط¬ط¯ ظ†طھط§ط¦ط¬.")
    return VIEW_RESULT

# --- ظ…ط¹ط§ظ„ط¬ط© طھط¹ط¯ظٹظ„ ط§ط³ظ… ط§ظ„ظ…ظˆظ‚ط¹ ---
async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("âڑ ï¸ڈ ط§ظ„ط±ط¬ط§ط، ط¥ط¯ط®ط§ظ„ ط§ط³ظ… ط§ظ„ظ…ظˆظ‚ط¹ ط§ظ„ط¬ط¯ظٹط¯:")
        return EDIT_NAME
    
    user_input = update.message.text.strip()
    old_name = context.user_data.get('edit_old_name', '')
    context.user_data['edit_name'] = old_name if user_input == '-' else user_input
    
    old_desc = context.user_data.get('edit_old_description', '')
    await update.message.reply_text(
        f"âœڈï¸ڈ **ط§ظ„ظˆطµظپ ط§ظ„ط­ط§ظ„ظٹ:**\n{escape_md(old_desc)}\n\n"
        f"ط£ط¯ط®ظ„ ط§ظ„ظˆطµظپ ط§ظ„ط¬ط¯ظٹط¯ ط£ظˆ ط£ط±ط³ظ„ **-** ظ„ظ„ط¥ط¨ظ‚ط§ط، ط¹ظ„ظ‰ ط§ظ„ط­ط§ظ„ظٹ:",
        parse_mode='Markdown'
    )
    return EDIT_DESCRIPTION

# --- ظ…ط¹ط§ظ„ط¬ط© طھط¹ط¯ظٹظ„ ط§ظ„ظˆطµظپ ---
async def edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("âڑ ï¸ڈ ط§ظ„ط±ط¬ط§ط، ط¥ط¯ط®ط§ظ„ ط§ظ„ظˆطµظپ ط§ظ„ط¬ط¯ظٹط¯:")
        return EDIT_DESCRIPTION
    
    user_input = update.message.text.strip()
    old_desc = context.user_data.get('edit_old_description', '')
    context.user_data['edit_description'] = old_desc if user_input == '-' else user_input
    
    old_benefit = context.user_data.get('edit_old_benefit', '')
    await update.message.reply_text(
        f"âœڈï¸ڈ **ط§ظ„ظپط§ط¦ط¯ط© ط§ظ„ط­ط§ظ„ظٹط©:**\n{escape_md(old_benefit)}\n\n"
        f"ط£ط¯ط®ظ„ ط§ظ„ظپط§ط¦ط¯ط© ط§ظ„ط¬ط¯ظٹط¯ط© ط£ظˆ ط£ط±ط³ظ„ **-** ظ„ظ„ط¥ط¨ظ‚ط§ط، ط¹ظ„ظ‰ ط§ظ„ط­ط§ظ„ظٹط©:",
        parse_mode='Markdown'
    )
    return EDIT_BENEFIT

# --- ظ…ط¹ط§ظ„ط¬ط© طھط¹ط¯ظٹظ„ ط§ظ„ظپط§ط¦ط¯ط© ظˆطھط£ظƒظٹط¯ ط§ظ„طھط¹ط¯ظٹظ„ ---
async def edit_benefit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("âڑ ï¸ڈ ط§ظ„ط±ط¬ط§ط، ط¥ط¯ط®ط§ظ„ ط§ظ„ظپط§ط¦ط¯ط© ط§ظ„ط¬ط¯ظٹط¯ط©:")
        return EDIT_BENEFIT
    
    user_input = update.message.text.strip()
    old_benefit = context.user_data.get('edit_old_benefit', '')
    context.user_data['edit_benefit'] = old_benefit if user_input == '-' else user_input
    
    editing_mode = context.user_data.get('editing_mode', 'site')
    
    if editing_mode == 'suggestion':
        # طھط¹ط¯ظٹظ„ ط§ظ‚طھط±ط§ط­
        from db import update_suggestion_data, fetch_pending_suggestions
        sug_id = context.user_data.get('editing_suggestion_id', '')
        success = update_suggestion_data(
            sug_id,
            context.user_data['edit_name'],
            context.user_data['edit_description'],
            context.user_data['edit_benefit']
        )
        if success:
            await update.message.reply_text("âœ… طھظ… طھط¹ط¯ظٹظ„ ط¨ظٹط§ظ†ط§طھ ط§ظ„ط§ظ‚طھط±ط§ط­ ط¨ظ†ط¬ط§ط­!")
        else:
            await update.message.reply_text("âڑ ï¸ڈ ط­ط¯ط« ط®ط·ط£ ط£ط«ظ†ط§ط، ط§ظ„طھط¹ط¯ظٹظ„.")
        
        # ط¥ط¹ط§ط¯ط© طھط­ظ…ظٹظ„ ط§ظ„ط§ظ‚طھط±ط§ط­ط§طھ ظˆط§ظ„ط¹ظˆط¯ط©
        updated = fetch_pending_suggestions()
        context.user_data['suggestions_list'] = updated
        context.user_data['sug_index'] = 0
        context.user_data.pop('editing_mode', None)
        context.user_data.pop('editing_suggestion_id', None)
        return await start(update, context)
    
    # طھط¹ط¯ظٹظ„ ظ…ظˆظ‚ط¹ ظ…ظˆط¬ظˆط¯ (ط§ظ„ظ…ظƒط±ط±) ظ‚ط§ط¯ظ… ظ…ظ† ظ…ط±ط§ط¬ط¹ط© ط§ظ„ط§ظ‚طھط±ط§ط­ط§طھ
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
                f"âœ… طھظ… طھط¹ط¯ظٹظ„ ط§ظ„ظ…ظˆظ‚ط¹ ط§ظ„ظ…ظˆط¬ظˆط¯ ط¨ظ†ط¬ط§ط­!\n\n"
                f"ًں“Œ ط§ظ„ظ…ظˆظ‚ط¹ ط§ظ„ظ…ط¹ط¯ظ„:\n"
                f"ًںŒگ {context.user_data['edit_name']}\n"
                f"ًں“‌ {context.user_data['edit_description']}\n"
                f"ًں’، {context.user_data['edit_benefit']}"
            )
        else:
            await update.message.reply_text("âڑ ï¸ڈ ط­ط¯ط« ط®ط·ط£ ط£ط«ظ†ط§ط، طھط¹ط¯ظٹظ„ ط§ظ„ظ…ظˆظ‚ط¹ ط§ظ„ظ…ظˆط¬ظˆط¯.")
        
        # طھظ†ط¸ظٹظپ ظˆط¥ط¹ط§ط¯ط© ط¨ظٹط§ظ†ط§طھ ط§ظ„ط§ظ‚طھط±ط§ط­ط§طھ
        context.user_data.pop('return_to_suggestions', None)
        context.user_data.pop('edit_main_category_en', None)
        context.user_data.pop('edit_sub_category_en', None)
        context.user_data.pop('editing_mode', None)
        updated = fetch_pending_suggestions()
        context.user_data['suggestions_list'] = updated
        context.user_data['sug_index'] = 0
        return await start(update, context)
    
    # طھط¹ط¯ظٹظ„ ظ…ظˆظ‚ط¹ ظ…ظ† ظ†طھط§ط¦ط¬ ط§ظ„ط¨ط­ط«

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
            # طھط­ط¯ظٹط« ط§ظ„ظ†طھظٹط¬ط© ظپظٹ ط§ظ„ظ‚ط§ط¦ظ…ط©
            result['website'] = context.user_data['edit_name']
            result['description'] = context.user_data['edit_description']
            result['benefit'] = context.user_data['edit_benefit']
            search_results[index] = result
            context.user_data['search_results'] = search_results
            await update.message.reply_text(
                f"âœ… طھظ… ط§ظ„طھط¹ط¯ظٹظ„ ط¨ظ†ط¬ط§ط­!\n\n"
                f"ًں“Œ ط§ظ„ظ†طھظٹط¬ط© ط§ظ„ظ…ط¹ط¯ظ„ط©:\n\n"
                f"ط§ظ„ظ…ظˆظ‚ط¹: {result['website']}\n"
                f"ط§ظ„ظˆطµظپ: {result['description']}\n"
                f"ط§ظ„ظپط§ط¦ط¯ط©: {result['benefit']}\n"
                f"ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ: {result['main_category_ar']}\n"
                f"ط§ظ„طھطµظ†ظٹظپ ط§ظ„ظپط±ط¹ظٹ: {result['sub_category_ar']}",
                reply_markup=result_options_keyboard()
            )
        else:
            await update.message.reply_text("âڑ ï¸ڈ ظپط´ظ„ ظپظٹ طھط¹ط¯ظٹظ„ ط§ظ„ظ…ظˆظ‚ط¹.")
            return await start(update, context)
    context.user_data.pop('editing_mode', None)
    return VIEW_RESULT

# --- ظ…ط¹ط§ظ„ط¬ط© ط§ظ„طھطµط¯ظٹط± ط§ظ„ط°ظƒظٹ ط¨ط§ظ„ط¨ط­ط« ---
async def handle_export_smart_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text.strip():
        await update.message.reply_text("âڑ ï¸ڈ ط§ظ„ط±ط¬ط§ط، ظƒطھط§ط¨ط© ط§ظ„ظƒظ„ظ…ط© ط§ظ„ط§ظپطھطھط§ط­ظٹط© ظ„ظ„طھطµط¯ظٹط±:")
        return EXPORT_SMART_SEARCH
    
    term = update.message.text.strip()
    loading_msg = await update.message.reply_text(f"ًں”چ ط¬ط§ط±ظٹ ط³ط­ط¨ ظƒظ„ ط§ظ„ظ…ظˆط§ظ‚ط¹ ط§ظ„ظ…ط±طھط¨ط·ط© ط¨ظ€ ({term})...")
    
    indexed_data = index_data()
    
    # ظپظ„طھط±ط© ظƒظ„ ط§ظ„ط¨ظٹط§ظ†ط§طھ (ظ„ط§ ظ†ظ‚طھطµط± ط¹ظ„ظ‰ 5 ظ†طھط§ط¦ط¬ ظپظ‚ط· ظƒط§ظ„ط¨ط­ط« ط§ظ„ط¹ط§ط¯ظٹ)
    term_lower = term.strip().lower()
    import re
    term_clean = re.sub(r'[ظ‹ظŒظچظژظڈظگظ‘ظ’]', '', term_lower)
    
    flat_data = []
    for item in indexed_data:
        search_text = item['search_text']
        website_lower = item['website'].lower()
        desc_lower = item['description'].lower()
        benefit_lower = item['benefit'].lower() if item['benefit'] else ''
        
        # ط¨ط­ط« ط´ط§ظ…ظ„
        if term_clean in website_lower or term_clean in desc_lower or term_clean in benefit_lower or term_clean in search_text:
            flat_data.append({
                "ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ": item['main_category_ar'],
                "ط§ظ„طھطµظ†ظٹظپ ط§ظ„ظپط±ط¹ظٹ": item['sub_category_ar'],
                "ط§ظ„ظ…ظˆظ‚ط¹": item['website'],
                "ط§ظ„ظˆطµظپ": item['description'],
                "ط§ظ„ظپط§ط¦ط¯ط©": item['benefit']
            })
            continue
            
        # ط¥ط¶ط§ظپط© ط§ظ„ظپظ„طھط±ط© ط§ظ„طھظ‚ط±ظٹط¨ظٹط© (Fuzzy) ظ„ظƒظ† ط¨ط¹طھط¨ط© ط¹ط§ظ„ظٹط© ظ„ظ„ط­ظپط§ط¸ ط¹ظ„ظ‰ ط¬ظˆط¯ط© ط§ظ„طھطµط¯ظٹط±
        from fuzzywuzzy import fuzz
        text = f"{desc_lower} {benefit_lower}"
        if fuzz.partial_ratio(term_clean, text) >= 85:
             flat_data.append({
                "ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ": item['main_category_ar'],
                "ط§ظ„طھطµظ†ظٹظپ ط§ظ„ظپط±ط¹ظٹ": item['sub_category_ar'],
                "ط§ظ„ظ…ظˆظ‚ط¹": item['website'],
                "ط§ظ„ظˆطµظپ": item['description'],
                "ط§ظ„ظپط§ط¦ط¯ط©": item['benefit']
            })

    if not flat_data:
        await loading_msg.edit_text(f"âڑ ï¸ڈ ظ„ظ… ظٹطھظ… ط§ظ„ط¹ط«ظˆط± ط¹ظ„ظ‰ ط£ظٹ ظ…ظˆط§ظ‚ط¹ طھط·ط§ط¨ظ‚ ({term}).", reply_markup=start_keyboard)
        return NAME

    await loading_msg.delete()
    await generate_and_send_excel(update.message, flat_data, f'sites_{term_clean}.xlsx', f"âœ… طھظ… طھطµط¯ظٹط± {len(flat_data)} ظ…ظˆظ‚ط¹ ظٹط®طµ ({term})")
    await update.message.reply_text("ط§ط®طھط± ط£ط­ط¯ ط§ظ„ط®ظٹط§ط±ط§طھ:", reply_markup=start_keyboard)
    return NAME

# --- ظ…ط¹ط§ظ„ط¬ط© ط§ظ„ظپظ„طھط±ط© ط¨ط§ظ„طھطµظ†ظٹظپ ظ„ظ„طھطµط¯ظٹط± ---
async def export_get_main_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'main_menu':
        await query.edit_message_text("ط§ط®طھط± ط£ط­ط¯ ط§ظ„ط®ظٹط§ط±ط§طھ:", reply_markup=start_keyboard)
        return NAME

    main_category_en = query.data
    context.user_data['export_main_category'] = main_category_en
    main_category_ar = CATEGORY_TRANSLATION.get(main_category_en, main_category_en)
    
    sub_categories = CATEGORIES.get(main_category_en, [])
    
    keyboard = [[InlineKeyboardButton(f"ًں“¦ طھطµط¯ظٹط± ظƒظ„ ({main_category_ar})", callback_data='export_this_main')]]
    if sub_categories:
        keyboard.append([InlineKeyboardButton("ًں“‚ ظˆط§طµظ„ ط§ظ„ظپظ„طھط±ط© ط¨ط§ظ„طھطµظ†ظٹظپ ط§ظ„ظپط±ط¹ظٹ", callback_data='filter_sub')])
    keyboard.append([InlineKeyboardButton("ط±ط¬ظˆط¹ â¬…ï¸ڈ", callback_data='export_data')])
    
    await query.edit_message_text(f"ًں“¥ ط®ظٹط§ط±ط§طھ طھطµط¯ظٹط± ظ„ظ€ ({main_category_ar}):", reply_markup=InlineKeyboardMarkup(keyboard))
    return EXPORT_SUB_CAT_SELECT

async def export_get_sub_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    main_category_en = context.user_data.get('export_main_category', '')
    main_category_ar = CATEGORY_TRANSLATION.get(main_category_en, main_category_en)
    
    if query.data == 'export_data':
        # ط§ظ„ط¹ظˆط¯ط© ظ„ظ„ظ‚ط§ط¦ظ…ط© ط§ظ„ط£ظˆظ„ظ‰
        return await handle_button(update, context) # ط³ظٹطھط¹ط§ظ…ظ„ ظ…ط¹ export_data
        
    elif query.data == 'export_this_main':
        await query.edit_message_text(f"âڈ³ ط¬ط§ط±ظٹ طھط¬ظ‡ظٹط² ظƒظ„ ظ…ظˆط§ظ‚ط¹ ({main_category_ar})...")
        flat_data = get_data_for_export(main_category_en)
        if not flat_data:
            await query.edit_message_text(f"âڑ ï¸ڈ ظ„ط§ طھظˆط¬ط¯ ظ…ظˆط§ظ‚ط¹ ظپظٹ ظ‡ط°ط§ ط§ظ„طھطµظ†ظٹظپ.")
        else:
            await generate_and_send_excel(query.message, flat_data, f'sites_{main_category_en}.xlsx', f"âœ… طھظ… طھطµط¯ظٹط± ظƒظ„ ظ…ظˆط§ظ‚ط¹ ({main_category_ar})")
        await query.message.reply_text("ط§ط®طھط± ط£ط­ط¯ ط§ظ„ط®ظٹط§ط±ط§طھ:", reply_markup=start_keyboard)
        return NAME
        
    elif query.data == 'filter_sub':
        sub_categories = CATEGORIES.get(main_category_en, [])
        reply_markup = build_keyboard(sub_categories)
        await query.edit_message_text(f"ًں“‚ ط§ط®طھط± ط§ظ„طھطµظ†ظٹظپ ط§ظ„ظپط±ط¹ظٹ ظ…ظ† ({main_category_ar}) ط§ظ„ط°ظٹ طھط±ظٹط¯ طھطµط¯ظٹط±ظ‡:", reply_markup=reply_markup)
        return EXPORT_SUB_CAT_SELECT
        
    else:
        # ط§ظ„ظ…ط³طھط®ط¯ظ… ط§ط®طھط§ط± طھطµظ†ظٹظپ ظپط±ط¹ظٹ ظ…ط¹ظٹظ† ظ„طھطµط¯ظٹط±ظ‡
        sub_category_en = query.data
        sub_category_ar = SUB_CATEGORY_TRANSLATION.get(sub_category_en, sub_category_en)
        await query.edit_message_text(f"âڈ³ ط¬ط§ط±ظٹ طھط¬ظ‡ظٹط² ظ…ظˆط§ظ‚ط¹ ({sub_category_ar})...")
        
        flat_data = get_data_for_export(main_category_en, sub_category_en)
        if not flat_data:
            await query.edit_message_text(f"âڑ ï¸ڈ ظ„ط§ طھظˆط¬ط¯ ظ…ظˆط§ظ‚ط¹ ظپظٹ ظ‡ط°ط§ ط§ظ„طھطµظ†ظٹظپ ط§ظ„ظپط±ط¹ظٹ.")
        else:
            await generate_and_send_excel(query.message, flat_data, f'sites_{sub_category_en}.xlsx', f"âœ… طھظ… طھطµط¯ظٹط± ظ…ظˆط§ظ‚ظ€ط¹ ({sub_category_ar})")
        await query.message.reply_text("ط§ط®طھط± ط£ط­ط¯ ط§ظ„ط®ظٹط§ط±ط§طھ:", reply_markup=start_keyboard)
        return NAME

# ط¯ظˆط§ظ„ ظ…ط³ط§ط¹ط¯ط© ظ„ظ„طھطµط¯ظٹط±
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
                    "ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ": main_cat_ar,
                    "ط§ظ„طھطµظ†ظٹظپ ط§ظ„ظپط±ط¹ظٹ": sub_cat_ar,
                    "ط§ظ„ظ…ظˆظ‚ط¹": site.get("website", ""),
                    "ط§ظ„ظˆطµظپ": site.get("description", ""),
                    "ط§ظ„ظپط§ط¦ط¯ط©": site.get("benefit", "")
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
    <div class="stats">ط¥ط¬ظ…ط§ظ„ظٹ ط§ظ„ظ…ظˆط§ظ‚ط¹: {len(data)}</div>
"""
    for item in data:
        html += f"""
    <div class="card">
        <div class="site-name"><a href="{item.get('ط§ظ„ظ…ظˆظ‚ط¹','')}" target="_blank">{item.get('ط§ظ„ظ…ظˆظ‚ط¹','')}</a></div>
        <div class="badges">
            <span class="badge">{item.get('ط§ظ„طھطµظ†ظٹظپ ط§ظ„ط±ط¦ظٹط³ظٹ','')}</span>
            <span class="badge">{item.get('ط§ظ„طھطµظ†ظٹظپ ط§ظ„ظپط±ط¹ظٹ','')}</span>
        </div>
        <div class="desc">ًں“‌ <b>ط§ظ„ظˆطµظپ:</b> {item.get('ط§ظ„ظˆطµظپ','')}</div>
"""
        if item.get('ط§ظ„ظپط§ط¦ط¯ط©',''):
            html += f'        <div class="benefit">ًں’، <b>ط§ظ„ظپط§ط¦ط¯ط©:</b> {item.get("ط§ظ„ظپط§ط¦ط¯ط©","")}</div>\n'
        html += '    </div>\n'
    
    html += "</body>\n</html>"
    return html

async def generate_and_send_excel(message, flat_data, filename, success_text):
    if not flat_data:
        await message.reply_text("â‌Œ ظ„ظ… ظٹطھظ… ط§ظ„ط¹ط«ظˆط± ط¹ظ„ظ‰ ط¨ظٹط§ظ†ط§طھ ظ„ظ„طھطµط¯ظٹط±.")
        return
    try:
        from telegram import InputMediaDocument
        
        # 1. ط¥ط¹ط¯ط§ط¯ Excel
        df = pd.DataFrame(flat_data)
        excel_filename = filename
        with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sites')
            worksheet = writer.sheets['Sites']
            worksheet.sheet_view.rightToLeft = True # ط¯ط¹ظ… ط§ظ„ظ„ط؛ط© ط§ظ„ط¹ط±ط¨ظٹط©
            # طھظˆط³ط¹ط© ط§ظ„ط£ط¹ظ…ط¯ط©
            for column_cells in worksheet.columns:
                length = max(len(str(cell.value)) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 60)
                
        # 2. ط¥ط¹ط¯ط§ط¯ HTML
        title_hdr = success_text.replace("âœ… ", "").replace("", "")
        html_content = create_html_report(flat_data, title_hdr)
        html_filename = filename.replace('.xlsx', '.html')
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        # 3. ط¥ط±ط³ط§ظ„ ط§ظ„ظ…ظ„ظپظٹظ† ظƒظ€ Media Group
        with open(excel_filename, 'rb') as f_xl, open(html_filename, 'rb') as f_html:
            await message.reply_media_group([
                InputMediaDocument(f_xl, caption="ًں“ٹ ظ…ظ„ظپ Excel (ظٹط¯ط¹ظ… ط§ظ„ط¹ط±ط¨ظٹط©)"),
                InputMediaDocument(f_html, caption="ًںŒگ طµظپط­ط© HTML طھظپط§ط¹ظ„ظٹط© ظˆظ…ظ…طھط§ط²ط© ظ„ظ„ط¬ظˆط§ظ„")
            ])
        await message.reply_text(success_text)
            
    except Exception as e:
        logger.error(f"ط®ط·ط£ ط£ط«ظ†ط§ط، ط¥ظ†ط´ط§ط، ظ…ظ„ظپط§طھ ط§ظ„طھطµط¯ظٹط±: {e}")
        await message.reply_text("âڑ ï¸ڈ ط­ط¯ط« ط®ط·ط£ ط£ط«ظ†ط§ط، طھط¬ظ‡ظٹط² ظ…ظ„ظپط§طھ ط§ظ„طھطµط¯ظٹط±.")
    finally:
        import os
        # طھظ†ط¸ظٹظپ ط§ظ„ظ…ظ„ظپط§طھ ط§ظ„ظ…ط¤ظ‚طھط©
        for temp_file in [filename, filename.replace('.xlsx', '.html')]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logger.error(f"ظپط´ظ„ ظپظٹ ظ…ط³ط­ ط§ظ„ظ…ظ„ظپ ط§ظ„ظ…ط¤ظ‚طھ {temp_file}: {e}")


# ================================================================
# === ط¥ط¯ط§ط±ط© ط§ظ„ظˆطµظˆظ„ ط¹ط¨ط± IP â€” Access Control Handlers
# ================================================================

async def handle_ip_menu(query, context) -> int:
    """ط¹ط±ط¶ ظ‚ط§ط¦ظ…ط© ط¥ط¯ط§ط±ط© ط§ظ„ظˆطµظˆظ„ ط§ظ„ط±ط¦ظٹط³ظٹط©"""
    from db import fetch_allowed_ips
    ips = fetch_allowed_ips()
    count = len(ips)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"ًں“‹ ظ‚ط§ط¦ظ…ط© ط§ظ„ط£ط¬ظ‡ط²ط© ط§ظ„ظ…ط³ظ…ظˆط­ط© ({count})", callback_data='list_ips')],
        [
            InlineKeyboardButton("â‍• ط¥ط¶ط§ظپط© IP", callback_data='add_ip'),
            InlineKeyboardButton("ًں—‘ï¸ڈ ط­ط°ظپ IP", callback_data='remove_ip_menu')
        ],
        [InlineKeyboardButton("ًں”‘ طھط؛ظٹظٹط± ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط±", callback_data='change_password')],
        [InlineKeyboardButton("â¬…ï¸ڈ ط±ط¬ظˆط¹ ظ„ظ„ظ‚ط§ط¦ظ…ط©", callback_data='main_menu')]
    ])
    await query.edit_message_text(
        "ًں”گ *ط¥ط¯ط§ط±ط© ط§ظ„ظˆطµظˆظ„ ط¥ظ„ظ‰ ط§ظ„ظ…ظˆظ‚ط¹*\n\n"
        "ظ…ظ† ظ‡ظ†ط§ طھطھط­ظƒظ… ظپظٹ ط§ظ„ط£ط¬ظ‡ط²ط© ط§ظ„ظ…ط³ظ…ظˆط­ ظ„ظ‡ط§ ط¨ط§ظ„ط¯ط®ظˆظ„ ظˆظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط±.\n\n"
        f"ًں“± ط§ظ„ط£ط¬ظ‡ط²ط© ط§ظ„ظ…ط³ظ…ظˆط­ط© ط­ط§ظ„ظٹط§ظ‹: `{count}`",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    return IP_MENU


async def handle_list_ips(query, context) -> int:
    """ط¹ط±ط¶ ظ‚ط§ط¦ظ…ط© ط§ظ„ظ€ IPs ط§ظ„ظ…ط³ظ…ظˆط­ ظ„ظ‡ط§"""
    from db import fetch_allowed_ips
    ips = fetch_allowed_ips()
    if not ips:
        text = "ًں“‹ *ظ‚ط§ط¦ظ…ط© ط§ظ„ط£ط¬ظ‡ط²ط© ط§ظ„ظ…ط³ظ…ظˆط­ط©*\n\nâڑ ï¸ڈ ظ„ط§ طھظˆط¬ط¯ ط£ط¬ظ‡ط²ط© ظ…ط³ظ…ظˆط­ط© ط­ط§ظ„ظٹط§ظ‹."
    else:
        text = f"ًں“‹ *ظ‚ط§ط¦ظ…ط© ط§ظ„ط£ط¬ظ‡ط²ط© ط§ظ„ظ…ط³ظ…ظˆط­ط© ({len(ips)}):*\n\n"
        for i, row in enumerate(ips, 1):
            label = row.get('label', '') or 'ط¨ط¯ظˆظ† ظˆطµظپ'
            date = (row.get('created_at', '') or '')[:10]
            text += f"`{i}.` `{row['ip']}` â€” {escape_md(label)}"
            if date:
                text += f" _({date})_"
            text += "\n"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("â¬…ï¸ڈ ط±ط¬ظˆط¹", callback_data='manage_access')]])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    return IP_MENU


async def handle_remove_ip_menu(query, context) -> int:
    """ط¹ط±ط¶ ظ‚ط§ط¦ظ…ط© ط­ط°ظپ ط§ظ„ظ€ IPs"""
    from db import fetch_allowed_ips
    ips = fetch_allowed_ips()
    if not ips:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("â¬…ï¸ڈ ط±ط¬ظˆط¹", callback_data='manage_access')]])
        await query.edit_message_text("âڑ ï¸ڈ ظ„ط§ طھظˆط¬ط¯ ط£ط¬ظ‡ط²ط© ظ„ط­ط°ظپظ‡ط§.", reply_markup=keyboard)
        return IP_MENU
    buttons = []
    for row in ips[:20]:
        label = row.get('label', '') or row['ip']
        buttons.append([InlineKeyboardButton(
            f"ًں—‘ï¸ڈ {row['ip']} â€” {label}",
            callback_data=f"del_ip:{row['ip']}"
        )])
    buttons.append([InlineKeyboardButton("â¬…ï¸ڈ ط±ط¬ظˆط¹", callback_data='manage_access')])
    await query.edit_message_text(
        "ًں—‘ï¸ڈ *ط­ط°ظپ ط¬ظ‡ط§ط²*\n\nط§ط®طھط± ط§ظ„ظ€ IP ط§ظ„ط°ظٹ طھط±ظٹط¯ ط­ط°ظپظ‡:\n\n"
        "âڑ ï¸ڈ طھظ†ط¨ظٹظ‡: ط§ظ„ط£ط¬ظ‡ط²ط© ط§ظ„طھظٹ ط³ط¨ظ‚ ظ…ظ†ط­ظ‡ط§ ط§ظ„ط¥ط°ظ† ظˆطھط°ظƒظ‘ط± ظ…طھطµظپط­ظ‡ط§ ط³طھط¸ظ„ طھط¯ط®ظ„ ط­طھظ‰ ظٹظ…ط³ط­ ط§ظ„ظƒط§ط´.",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='Markdown'
    )
    return IP_MENU


async def handle_add_ip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ظ…ط¹ط§ظ„ط¬ط© ط¥ط¯ط®ط§ظ„ IP ط§ظ„ط¬ط¯ظٹط¯"""
    import re
    ip = update.message.text.strip()
    # طھط­ظ‚ظ‚ ط¨ط³ظٹط· ظ…ظ† طµظٹط؛ط© IP (IPv4 ط£ظˆ IPv6)
    if not re.match(r'^[0-9a-fA-F.:]+$', ip) or len(ip) < 7:
        await update.message.reply_text(
            "â‌Œ طµظٹط؛ط© ط§ظ„ظ€ IP ط؛ظٹط± طµط­ظٹط­ط©.\n\nظ…ط«ط§ظ„ طµط­ظٹط­: `203.0.113.45`\n\nط£ط¹ط¯ ط§ظ„ط¥ط±ط³ط§ظ„ ط£ظˆ /start ظ„ظ„ط¥ظ„ط؛ط§ط،:",
            parse_mode='Markdown'
        )
        return ADD_IP_STATE

    context.user_data['pending_ip'] = ip
    await update.message.reply_text(
        f"âœ… ط§ظ„ظ€ IP: `{ip}`\n\n"
        "ط£ط±ط³ظ„ ظˆطµظپط§ظ‹ ظ„ظ„ط¬ظ‡ط§ط² (ظ…ط«ط§ظ„: *ط¬ظ‡ط§ط² ط§ظ„ظ…ظ†ط²ظ„* ط£ظˆ *ظ…ظˆط¨ط§ظٹظ„ ط£ط­ظ…ط¯*)طŒ "
        "ط£ظˆ ط£ط±ط³ظ„ `-` ظ„ظ„طھط®ط·ظٹ:",
        parse_mode='Markdown'
    )
    return ADD_IP_LABEL_STATE


async def handle_add_ip_label(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ظ…ط¹ط§ظ„ط¬ط© طھط³ظ…ظٹط© ط§ظ„ط¬ظ‡ط§ط² ظˆط¥طھظ…ط§ظ… ط§ظ„ط¥ط¶ط§ظپط©"""
    from db import add_allowed_ip
    label = update.message.text.strip()
    if label == '-':
        label = ''
    ip = context.user_data.pop('pending_ip', '')
    success, msg = add_allowed_ip(ip, label)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("â¬…ï¸ڈ ط¥ط¯ط§ط±ط© ط§ظ„ظˆطµظˆظ„", callback_data='manage_access')]])
    if success:
        await update.message.reply_text(
            f"âœ… طھظ…طھ ط¥ط¶ط§ظپط© ط§ظ„ط¬ظ‡ط§ط² ط¨ظ†ط¬ط§ط­!\n\n"
            f"ًںŒگ IP: `{ip}`\n"
            f"ًں“± ط§ظ„ظˆطµظپ: {escape_md(label) if label else 'ط¨ط¯ظˆظ† ظˆطµظپ'}\n\n"
            "ط§ظ„ط¬ظ‡ط§ط² ط§ظ„ط¢ظ† ظ…ط³ظ…ظˆط­ ظ„ظ‡ ط¨ط§ظ„ط¯ط®ظˆظ„ ظ…ط¨ط§ط´ط±ط©ظ‹.",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"âڑ ï¸ڈ `{ip}` ظ…ظˆط¬ظˆط¯ ظ…ط³ط¨ظ‚ط§ظ‹ ظپظٹ ط§ظ„ظ‚ط§ط¦ظ…ط© ط£ظˆ ط­ط¯ط« ط®ط·ط£.\n\nط§ظ„ط®ط·ط£: {msg}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    return IP_MENU


async def handle_change_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """طھط؛ظٹظٹط± ظƒظ„ظ…ط© ظ…ط±ظˆط± ط§ظ„ظ…ظˆظ‚ط¹"""
    from db import set_access_password
    new_pwd = update.message.text.strip()
    if len(new_pwd) < 4:
        await update.message.reply_text(
            "â‌Œ ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ظ‚طµظٹط±ط© ط¬ط¯ط§ظ‹ (4 ط£ط­ط±ظپ ط¹ظ„ظ‰ ط§ظ„ط£ظ‚ظ„).\nط£ط¹ط¯ ط§ظ„ط¥ط±ط³ط§ظ„:"
        )
        return CHANGE_PASSWORD_STATE
    success = set_access_password(new_pwd)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("â¬…ï¸ڈ ط¥ط¯ط§ط±ط© ط§ظ„ظˆطµظˆظ„", callback_data='manage_access')]])
    if success:
        await update.message.reply_text(
            f"âœ… طھظ… طھط؛ظٹظٹط± ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط¨ظ†ط¬ط§ط­!\n\n"
            f"ًں”‘ ظƒظ„ظ…ط© ط§ظ„ظ…ط±ظˆط± ط§ظ„ط¬ط¯ظٹط¯ط©: `{escape_md(new_pwd)}`\n\n"
            "ط§ظ„ط²ظˆط§ط± ط§ظ„ط¬ط¯ط¯ ط³ظٹط­طھط§ط¬ظˆظ† ط¥ظ„ظ‰ ظ‡ط°ظ‡ ط§ظ„ظƒظ„ظ…ط© ظ„ظ„ط¯ط®ظˆظ„.",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("â‌Œ ط­ط¯ط« ط®ط·ط£ ط£ط«ظ†ط§ط، ط§ظ„طھط؛ظٹظٹط±.", reply_markup=keyboard)
    return IP_MENU


