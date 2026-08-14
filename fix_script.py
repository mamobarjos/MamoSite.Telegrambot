import re

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSiteWeb-main\script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace getBrowserInfo
new_browser_info = """function getBrowserInfo() {
    const ua = navigator.userAgent;
    let browser = "Unknown";
    if (ua.includes("Chrome") && !ua.includes("Edg")) browser = "Chrome";
    else if (ua.includes("Safari") && !ua.includes("Chrome")) browser = "Safari";
    else if (ua.includes("Firefox")) browser = "Firefox";
    else if (ua.includes("Edg")) browser = "Edge";
    
    let os = "Unknown";
    if (ua.includes("Windows")) os = "Windows";
    else if (ua.includes("Mac")) os = "MacOS";
    else if (ua.includes("Linux")) os = "Linux";
    else if (ua.includes("Android")) os = "Android";
    else if (ua.includes("iOS") || ua.includes("iPhone")) os = "iOS";
    
    let resolution = "Unknown";
    if (window.screen) {
        resolution = window.screen.width + "x" + window.screen.height;
    }
    
    let lang = navigator.language || "Unknown";
    
    return "متصفح " + browser + " | " + os + " | " + resolution;
}"""
content = re.sub(r'function getBrowserInfo\(\) \{.*?(?=\nasync function initIPGate)', new_browser_info + '\n\n', content, flags=re.DOTALL)

# Replace generateUUID
content = re.sub(r'function generateUUID\(\) \{.*?(?=\nfunction getBrowserInfo)', '', content, flags=re.DOTALL)

# Replace initIPGate UUID usage
new_init_ip_gate = """async function initIPGate() {
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

    if (!visitorIP) {
        visitorIP = "unknown-" + Math.floor(Math.random()*10000);
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
                    localStorage.removeItem(DEVICE_APPROVED_KEY);
                    showGate();
                    setGateMsg('error', '<i class="fas fa-ban"></i> تم حظر هذا الـ IP. يرجى التواصل مع مسؤول النظام.');
                    const pwdInput = document.getElementById('ip-gate-password');
                    const submitBtn = document.getElementById('ip-gate-submit');
                    if (pwdInput) pwdInput.disabled = true;
                    if (submitBtn) submitBtn.disabled = true;
                    return;
                }
                if (localStorage.getItem(DEVICE_APPROVED_KEY) === 'approved') {
                    hideGate(false);
                    return;
                }
            } else {
                localStorage.removeItem(DEVICE_APPROVED_KEY);
            }
        }
    } catch (_) {
        if (localStorage.getItem(DEVICE_APPROVED_KEY) === 'approved') {
            hideGate(false);
            return;
        }
    }

    showGate();
}"""
content = re.sub(r'async function initIPGate\(\) \{.*?(?=\n\/\*\*)', new_init_ip_gate + '\n\n', content, flags=re.DOTALL)

# Replace showGate login logic
new_login_logic = """            const visitorIP = window._gateVisitorIP;
            const userAgent = window._gateUserAgent;
            const location = window._gateLocation;

            if (entered === data.value) {
                setGateMsg('success', '<i class="fas fa-check-circle"></i> تم التحقق! جاري الدخول...');

                if (visitorIP) {
                    await supabaseClient.from('devices').upsert({ 
                        device_id: visitorIP, 
                        user_id: visitorIP, 
                        failed_attempts: 0, 
                        is_blocked: false,
                        user_agent: userAgent,
                        location: location
                    }, { onConflict: 'device_id' });
                }

                localStorage.setItem(DEVICE_APPROVED_KEY, 'approved');
                setTimeout(() => hideGate(true), 900);
            } else {
                if (visitorIP) {
                    let currentFailed = 0;
                    const { data: devData } = await supabaseClient.from('devices').select('failed_attempts').eq('device_id', visitorIP).single();
                    if (devData) { currentFailed = devData.failed_attempts || 0; }
                    currentFailed++;
                    
                    const isBlocked = currentFailed >= 5;
                    await supabaseClient.from('devices').upsert({ 
                        device_id: visitorIP, 
                        user_id: visitorIP, 
                        failed_attempts: currentFailed, 
                        is_blocked: isBlocked,
                        user_agent: userAgent,
                        location: location
                    }, { onConflict: 'device_id' });
                    
                    if (isBlocked) {
                        const errMsg = '<i class="fas fa-ban"></i> <b>تنبيه أمني:</b> تم حظر هذا الـ IP. يرجى التواصل مع مسؤول النظام.';
                        setGateMsg('error', errMsg);
                        const errElem = document.getElementById('error-message');
                        if (errElem) errElem.innerHTML = errMsg;
                        newSubmitBtn.disabled = true;
                        newSubmitBtn.innerHTML = 'محظور';
                        newPwdInput.disabled = true;
                        return;
                    } else {
                        const remaining = 5 - currentFailed;
                        const errMsg = `<i class="fas fa-times-circle"></i> كلمة المرور غير صحيحة (متبقي ${remaining} محاولات).`;
                        setGateMsg('error', errMsg);
                        const errElem = document.getElementById('error-message');
                        if (errElem) errElem.innerHTML = errMsg;
                    }
                }
                
                newPwdInput.value = '';
                newPwdInput.focus();
                newSubmitBtn.disabled = false;
                newSubmitBtn.innerHTML = '<span>دخول</span><i class="fas fa-arrow-left"></i>';
            }"""
content = re.sub(r'            const deviceId = window._gateDeviceID;.*?newSubmitBtn\.innerHTML = \'<span>دخول</span><i class="fas fa-arrow-left"></i>\';\n            }', new_login_logic, content, flags=re.DOTALL)

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSiteWeb-main\script.js', 'w', encoding='utf-8') as f:
    f.write(content)
