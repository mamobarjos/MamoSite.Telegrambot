import re

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSiteWeb-main\script.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

new_init_gate = """async function initIPGate() {
    const isAuth = localStorage.getItem('isAuth') === 'true';
    if (!isAuth) {
        removeLoader();
        showGate();
    }

    let visitorIP = null;
    let locationData = "Unknown";
    try {
        const res = await fetch('https://ipapi.co/json/', { signal: AbortSignal.timeout(5000) });
        const data = await res.json();
        visitorIP = data.ip;
        if(data.city && data.country_name) {
            let flag = data.country_code ? String.fromCodePoint(...[...data.country_code.toUpperCase()].map(c => c.charCodeAt() + 0x1F1A5)) : "";
            locationData = flag + " " + data.city + ", " + data.country_name;
        }
    } catch (_) {
        try {
            const res2 = await fetch('https://api.ipify.org?format=json', { signal: AbortSignal.timeout(5000) });
            const data2 = await res2.json();
            visitorIP = data2.ip;
        } catch(e) {}
    }

    let fallbackId = localStorage.getItem('mamo_fallback_id');
    if (!fallbackId) {
        fallbackId = Math.floor(Math.random()*10000);
        localStorage.setItem('mamo_fallback_id', fallbackId);
    }
    if (!visitorIP) {
        visitorIP = "Hidden-IP-" + fallbackId;
        locationData = "مخفي (VPN)";
    }

    window._gateVisitorIP = visitorIP;
    window._gateUserAgent = getBrowserInfo();
    window._gateLocation = locationData;

    try {
        if (visitorIP) {
            const { data, error } = await supabaseClient
                .from('devices')
                .select('is_blocked')
                .eq('device_id', visitorIP)
                .limit(1);

            if (!error && data && data.length > 0) {
                if (data[0].is_blocked) {
                    localStorage.removeItem('isAuth');
                    removeLoader();
                    showGate();
                    setGateMsg('error', '<i class="fas fa-ban"></i> تم حظر هذا الـ IP. يرجى التواصل مع مسؤول النظام.');
                    const pwdInput = document.getElementById('ip-gate-password');
                    const submitBtn = document.getElementById('ip-gate-submit');
                    if (pwdInput) pwdInput.disabled = true;
                    if (submitBtn) submitBtn.disabled = true;
                    return;
                }
                if (isAuth) {
                    removeLoader();
                    hideGate(false);
                    return;
                }
            } else {
                if (isAuth) {
                    localStorage.removeItem('isAuth');
                    removeLoader();
                    showGate();
                }
            }
        }
    } catch (err) {
        console.error(err);
        if (isAuth) {
            removeLoader();
            hideGate(false);
            return;
        }
    }

    removeLoader();
    if (!isAuth) {
        showGate();
    }
}"""

js_content = re.sub(r'async function initIPGate\(\) \{.*?(?=function removeLoader)', new_init_gate + '\n\n', js_content, flags=re.DOTALL)

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSiteWeb-main\script.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSite.Telegrambot-main\handlers.py', 'r', encoding='utf-8') as f:
    py_content = f.read()

new_keys = """    keyboard.append([
        InlineKeyboardButton("إضافة موقع ➕", callback_data='start_add'),
        InlineKeyboardButton("البحث 🔍", callback_data='search')
    ])
    
    # زر "إدارة المسؤولين" ثم "إدارة الأجهزة"
    row2 = []
    if update.effective_user.id == 1156962576:
        row2.append(InlineKeyboardButton("المسؤولين 👥", callback_data='manage_admins'))
    row2.append(InlineKeyboardButton("الأجهزة 📱", callback_data='manage_devices'))
    keyboard.append(row2)
    
    # زر "تغيير كلمة المرور" ثم "تصدير البيانات"
    keyboard.append([
        InlineKeyboardButton("كلمة المرور 🔑", callback_data='change_site_password'),
        InlineKeyboardButton("تصدير 📥", callback_data='export_data')
    ])"""

# We can replace the exact block in handlers.py
py_content = re.sub(r'    keyboard.append\(\[\n        InlineKeyboardButton\("ابدأ إضافة موقع ▶️", callback_data=\'start_add\'\),\n        InlineKeyboardButton\("البحث 🔍", callback_data=\'search\'\)\n    \]\)\n    \n    # زر "إدارة المسؤولين" ثم "إدارة الأجهزة"\n    row2 = \[\]\n    if update.effective_user.id == 1156962576:\n        row2.append\(InlineKeyboardButton\("👥 إدارة المسؤولين", callback_data=\'manage_admins\'\)\)\n    row2.append\(InlineKeyboardButton\("📱 إدارة الأجهزة", callback_data=\'manage_devices\'\)\)\n    keyboard.append\(row2\)\n    \n    # زر "تغيير كلمة المرور" ثم "تصدير البيانات"\n    keyboard.append\(\[\n        InlineKeyboardButton\("🔑 تغيير كلمة المرور", callback_data=\'change_site_password\'\),\n        InlineKeyboardButton\("تصدير البيانات 📤", callback_data=\'export_data\'\)\n    \]\)', new_keys, py_content, flags=re.DOTALL)

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSite.Telegrambot-main\handlers.py', 'w', encoding='utf-8') as f:
    f.write(py_content)
