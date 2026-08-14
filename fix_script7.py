import re

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSite.Telegrambot-main\db.py', 'r', encoding='utf-8') as f:
    py_content = f.read()

# Replace the label concatenation logic
old_logic = """                  label = f"{user_ip} - {user_agent}"
                  if location:
                      label += f" ({location})\""""

new_logic = """                  label = f"{user_ip} - {user_agent}"
                  if location:
                      if "(" in location and ")" in location:
                          label += f" {location}"
                      else:
                          label += f" ({location})\""""

py_content = py_content.replace(old_logic, new_logic)

with open(r'C:\Users\HOME\OneDrive\Desktop\MamoSite.Telegrambot-main\db.py', 'w', encoding='utf-8') as f:
    f.write(py_content)
