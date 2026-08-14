import re

# Fix script.js
with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSiteWeb-main\script.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

# Replace (${_gateLocation}) with - ${_gateLocation}
js_content = js_content.replace('(${_gateLocation})', '- ${_gateLocation}')

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSiteWeb-main\script.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

# Fix handlers.py
with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSite.Telegrambot-main\handlers.py', 'r', encoding='utf-8') as f:
    py_content = f.read()

# Replace buttons layout
old_keys = """    keyboard.append([
        InlineKeyboardButton("إضافة ➕", callback_data='start_add'),
        InlineKeyboardButton("بحث 🔍", callback_data='search')
    ])
    
    # زر "إدارة المسؤولين" ثم "إدارة الأجهزة"
    row2 = []
    if update.effective_user.id == 1156962576:
        row2.append(InlineKeyboardButton("إدارة 👥", callback_data='manage_admins'))
    row2.append(InlineKeyboardButton("أجهزة 📱", callback_data='manage_devices'))
    keyboard.append(row2)
    
    # زر "تغيير كلمة المرور" ثم "تصدير البيانات"
    keyboard.append([
        InlineKeyboardButton("رمز 🔑", callback_data='change_site_password'),
        InlineKeyboardButton("تصدير 📥", callback_data='export_data')
    ])"""

new_keys = """    keyboard.append([InlineKeyboardButton("إضافة ➕", callback_data='start_add')])
    keyboard.append([InlineKeyboardButton("بحث 🔍", callback_data='search')])
    
    # إدارة المسؤولين والأجهزة
    if update.effective_user.id == 1156962576:
        keyboard.append([InlineKeyboardButton("إدارة 👥", callback_data='manage_admins')])
    keyboard.append([InlineKeyboardButton("أجهزة 📱", callback_data='manage_devices')])
    
    # تغيير كلمة المرور وتصدير البيانات
    keyboard.append([InlineKeyboardButton("رمز 🔑", callback_data='change_site_password')])
    keyboard.append([InlineKeyboardButton("تصدير 📥", callback_data='export_data')])"""

py_content = py_content.replace(old_keys, new_keys)

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSite.Telegrambot-main\handlers.py', 'w', encoding='utf-8') as f:
    f.write(py_content)
