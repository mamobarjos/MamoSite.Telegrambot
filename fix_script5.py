import re

# Fix script.js
with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSiteWeb-main\script.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

# The error was two closing braces.
js_content = js_content.replace("""    setTimeout(() => {
        gate.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }, 420);
}
}""", """    setTimeout(() => {
        gate.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }, 420);
}""")

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSiteWeb-main\script.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

# Fix handlers.py
with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSite.Telegrambot-main\handlers.py', 'r', encoding='utf-8') as f:
    py_content = f.read()

# Replace the text of the buttons according to the user's latest request to avoid text wrapping.
py_content = py_content.replace('InlineKeyboardButton("إضافة موقع ➕", callback_data=\'start_add\')', 'InlineKeyboardButton("إضافة ➕", callback_data=\'start_add\')')
py_content = py_content.replace('InlineKeyboardButton("البحث 🔍", callback_data=\'search\')', 'InlineKeyboardButton("بحث 🔍", callback_data=\'search\')')
py_content = py_content.replace('InlineKeyboardButton("المسؤولين 👥", callback_data=\'manage_admins\')', 'InlineKeyboardButton("إدارة 👥", callback_data=\'manage_admins\')')
py_content = py_content.replace('InlineKeyboardButton("الأجهزة 📱", callback_data=\'manage_devices\')', 'InlineKeyboardButton("أجهزة 📱", callback_data=\'manage_devices\')')
py_content = py_content.replace('InlineKeyboardButton("كلمة المرور 🔑", callback_data=\'change_site_password\')', 'InlineKeyboardButton("رمز 🔑", callback_data=\'change_site_password\')')

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSite.Telegrambot-main\handlers.py', 'w', encoding='utf-8') as f:
    f.write(py_content)
