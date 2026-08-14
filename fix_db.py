import os

db_path = r'C:\Users\HOME\OneDrive\Desktop\MamoSite.Telegrambot-main\db.py'

with open(db_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_block_logic = """
    try:
        client = get_client()
        try:
            client.table("devices").upsert({
                "device_id": identifier_str,
                "user_id": identifier_str,
                "is_blocked": is_blocked,
                "failed_attempts": 5 if is_blocked else 0
            }, on_conflict="device_id").execute()
        except Exception as e:
            logger.warning(f"خطأ تحديث devices: {e}")
            
        return True
"""
new_block_logic = """
    try:
        client = get_client()
        try:
            client.table("devices").upsert({
                "device_id": identifier_str,
                "user_id": identifier_str,
                "is_blocked": is_blocked,
                "failed_attempts": 5 if is_blocked else 0
            }, on_conflict="device_id").execute()
        except Exception as e:
            logger.warning(f"خطأ تحديث devices: {e}")

        # Update allowed_ips as well to enforce session invalidation
        try:
            # If the IP is in allowed_ips, update its block status
            client.table("allowed_ips").update({
                "is_blocked": is_blocked
            }).eq("ip", identifier_str).execute()
        except Exception as e:
            logger.warning(f"خطأ تحديث allowed_ips: {e}")
            
        return True
"""

if old_block_logic.strip() in content.strip():
    content = content.replace(old_block_logic.strip(), new_block_logic.strip())
    with open(db_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("db.py updated successfully.")
else:
    print("Could not find the block logic in db.py.")

