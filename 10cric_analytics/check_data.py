import os
import json
import sys

# Ensure console output uses UTF-8 to prevent UnicodeEncodeError on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

path = r"C:\Users\kadam\Desktop\scraper\10cric\json"
print("Verifying collected data from JSON files:\n" + "=" * 60)

for f in os.listdir(path):
    if f.endswith('.json') and f != 'execution_summary.json':
        file_path = os.path.join(path, f)
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            print(f"File: {f}")
            print(f"  Page URL:   {data.get('page_url')}")
            print(f"  Page Title: {data.get('page_title')}")
            print(f"  Categories (sample): {data.get('categories')[:5]} (Total: {len(data.get('categories'))})")
            print(f"  Public Content (sample): {data.get('public_content')[:5]} (Total: {len(data.get('public_content'))})")
            print(f"  Headings (sample): {[h.get('text') for h in data.get('headings')[:3]]} (Total: {len(data.get('headings'))})")
            print("-" * 60)
