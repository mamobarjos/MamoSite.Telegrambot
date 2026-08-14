import os

file_path = r'C:\Users\HOME\OneDrive\Desktop\MamoSite.Telegrambot-main\handlers.py'
with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

old_block = '''    if not items:
        text = "📱 *إدارة الأجهزة والوصول*\n\n⚠️ لا توجد أجهزة أو IPs مسجلة حالياً في النظام."
    else:
        text = (
            f"📱 *إدارة الأجهزة والوصول ({count})*\n\n"
            "من هنا يمكنك الاطلاع على الأجهزة/IPs وتغيير حالة الحظر أو حذفها:\n"
        )
        for row in items:
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

new_block = '''    if not items:
        text = "📱 *إدارة الأجهزة والوصول*\n\n⚠️ لا توجد أجهزة أو IPs مسجلة حالياً في النظام."
        keyboard.append([InlineKeyboardButton("لا توجد أجهزة مسجلة حالياً", callback_data="manage_devices")])
    else:
        text = (
            f"📱 *إدارة الأجهزة والوصول ({count})*\n\n"
            "من هنا يمكنك الاطلاع على الأجهزة/IPs وتغيير حالة الحظر أو حذفها:\n"
        )
        for row in items:
            ip = row.get('identifier', '')
            if not ip:
                ip = row.get('ip', '')
            if not ip:
                ip = str(row.get('device_id', ''))
                
            label = row.get('label', '') or 'جهاز'
            is_blocked = row.get('is_blocked', False)
            
            if is_blocked:
                info_label = f"🔴 محظور: {ip} ({label})"
                keyboard.append([InlineKeyboardButton(info_label, callback_data="manage_devices")])
                keyboard.append([
                    InlineKeyboardButton("🗑️ حذف الجهاز", callback_data=f"ask_del_ip:{ip}"),
                    InlineKeyboardButton("🔓 فك الحظر", callback_data=f"unblock_dev:{ip}")
                ])
            else:
                info_label = f"🟢 مسموح: {ip} ({label})"
                keyboard.append([InlineKeyboardButton(info_label, callback_data="manage_devices")])
                keyboard.append([
                    InlineKeyboardButton("🗑️ حذف الجهاز", callback_data=f"ask_del_ip:{ip}"),
                    InlineKeyboardButton("⛔ حظر الجهاز", callback_data=f"block_dev:{ip}")
                ])'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Handlers block replaced successfully.')
else:
    print('Error: Old block not found in file.')
