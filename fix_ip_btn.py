import os

file_path = r'C:\Users\HOME\OneDrive\Desktop\MamoSite.Telegrambot-main\handlers.py'
with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

old_block = '''        for row in items:
            ident = row.get('identifier', '')
            label = row.get('label', '') or 'جهاز'
            is_blocked = row.get('is_blocked', False)
            
            if is_blocked:
                btn_label = f"🔴 محظور: {ident} ({label})"
                keyboard.append([
                    InlineKeyboardButton(btn_label, callback_data=f"unblock_dev:{ident}"),
                    InlineKeyboardButton("🗑️ مسح", callback_data=f"ask_del_ip:{ident}")
                ])
            else:
                btn_label = f"🟢 مسموح: {ident} ({label})"
                keyboard.append([
                    InlineKeyboardButton(btn_label, callback_data=f"ask_del_ip:{ident}"),
                    InlineKeyboardButton("⛔ حظر", callback_data=f"block_dev:{ident}")
                ])'''

new_block = '''        for row in items:
            ip = row.get('identifier', '')
            if not ip:
                ip = row.get('ip', '')
            if not ip:
                ip = str(row.get('device_id', ''))
                
            label = row.get('label', '') or 'جهاز'
            is_blocked = row.get('is_blocked', False)
            
            if is_blocked:
                btn_label = f"🔴 محظور: {ip} ({label})"
                keyboard.append([
                    InlineKeyboardButton(btn_label, callback_data=f"unblock_dev:{ip}"),
                    InlineKeyboardButton("🗑️ مسح", callback_data=f"ask_del_ip:{ip}")
                ])
            else:
                btn_label = f"🟢 مسموح: {ip} ({label})"
                keyboard.append([
                    InlineKeyboardButton(btn_label, callback_data=f"ask_del_ip:{ip}"),
                    InlineKeyboardButton("⛔ حظر", callback_data=f"block_dev:{ip}")
                ])'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Block replaced successfully.')
else:
    print('Error: Old block not found in file.')
