import re

# 1. Update index.html
with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSiteWeb-main\index.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# Add loading overlay and hide ip-gate by default
loading_html = """
    <!-- ======= Loading Overlay ======= -->
    <div id="mamo-loader" style="position: fixed; inset: 0; background: #0f172a; z-index: 999999; display: flex; align-items: center; justify-content: center; flex-direction: column; transition: opacity 0.4s ease;">
        <i class="fas fa-circle-notch fa-spin" style="font-size: 3rem; color: #6366f1; margin-bottom: 1rem;"></i>
        <h3 style="color: #fff; font-family: 'Cairo', sans-serif;">جاري التحقق...</h3>
    </div>
    <!-- ======= End Loading Overlay ======= -->

    <!-- ======= IP Gate Overlay ======= -->
    <div id="ip-gate" class="ip-gate-overlay hidden">
"""
html_content = html_content.replace('    <!-- ======= IP Gate Overlay ======= -->\n    <div id="ip-gate" class="ip-gate-overlay">', loading_html)

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSiteWeb-main\index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

# 2. Update script.js
with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSiteWeb-main\script.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

# Fix hideGate to reset overflow explicitly
new_hide_gate = """function hideGate(animate = true) {
    const gate = document.getElementById('ip-gate');
    if (!gate) return;
    if (!animate) {
        gate.classList.add('hidden');
        document.body.style.overflow = 'auto';
        return;
    }
    gate.classList.add('fading');
    setTimeout(() => {
        gate.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }, 420);
}"""
js_content = re.sub(r'function hideGate\(animate = true\) \{.*?(?=\n\}|\n//|\n\n)', new_hide_gate, js_content, flags=re.DOTALL)


# Fix Device ID persistence, OS detection Safari fix, Session Persistence, and Loader removal
new_init_gate = """async function initIPGate() {
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
                if (localStorage.getItem('isAuth') === 'true') {
                    removeLoader();
                    hideGate(false);
                    return;
                }
            } else {
                localStorage.removeItem('isAuth');
            }
        }
    } catch (_) {
        if (localStorage.getItem('isAuth') === 'true') {
            removeLoader();
            hideGate(false);
            return;
        }
    }

    removeLoader();
    showGate();
}

function removeLoader() {
    const loader = document.getElementById('mamo-loader');
    if (loader) {
        loader.style.opacity = '0';
        setTimeout(() => loader.remove(), 400);
    }
}"""
js_content = re.sub(r'async function initIPGate\(\) \{.*?(?=\n\/\*\*)', new_init_gate + '\n\n', js_content, flags=re.DOTALL)

# Fix login success saving 'isAuth' to 'true'
js_content = js_content.replace("localStorage.setItem(DEVICE_APPROVED_KEY, 'approved');", "localStorage.setItem('isAuth', 'true');")

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSiteWeb-main\script.js', 'w', encoding='utf-8') as f:
    f.write(js_content)
