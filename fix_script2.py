import re

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSiteWeb-main\script.js', 'r', encoding='utf-8') as f:
    content = f.read()

new_os = """    let os = "Unknown";
    if (ua.includes("iPhone") || ua.includes("iPad") || ua.includes("iPod") || ua.includes("iOS") || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)) {
        os = "iOS";
    } else if (ua.includes("Android")) {
        os = "Android";
    } else if (ua.includes("Windows")) {
        os = "Windows";
    } else if (ua.includes("Mac")) {
        os = "MacOS";
    } else if (ua.includes("Linux")) {
        os = "Linux";
    }"""
old_os = """    let os = "Unknown";
    if (ua.includes("Windows")) os = "Windows";
    else if (ua.includes("Mac")) os = "MacOS";
    else if (ua.includes("Linux")) os = "Linux";
    else if (ua.includes("Android")) os = "Android";
    else if (ua.includes("iOS") || ua.includes("iPhone")) os = "iOS";"""

content = content.replace(old_os, new_os)

new_fallback = """    if (!visitorIP) {
        visitorIP = "Hidden-IP-" + Math.floor(Math.random()*10000);
        locationData = "مخفي (VPN)";
    }"""
old_fallback = """    if (!visitorIP) {
        visitorIP = "unknown-" + Math.floor(Math.random()*10000);
    }"""

content = content.replace(old_fallback, new_fallback)

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSiteWeb-main\script.js', 'w', encoding='utf-8') as f:
    f.write(content)
