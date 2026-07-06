import os
import json
import pandas as pd
from datetime import datetime

json_path = r"C:\Users\kadam\Desktop\scraper\10cric\json"
excel_output_path = r"C:\Users\kadam\Desktop\scraper\10cric\10cric_Scraper_Report.xlsx"

print("Compiling scraper JSON outputs into a professional Excel report...")

summary_list = []
detailed_list = []

# Load summary first if exists
execution_summary_file = os.path.join(json_path, "execution_summary.json")
if os.path.exists(execution_summary_file):
    with open(execution_summary_file, 'r', encoding='utf-8') as f:
        summary_list = json.load(f)

# Collect detailed lists from each page
for f in os.listdir(json_path):
    if f.endswith('.json') and f != 'execution_summary.json':
        file_path = os.path.join(json_path, f)
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            page_name = f.split('_2026')[0].replace('_', ' ').title()
            
            # Add to detailed sheet
            categories = data.get('categories', [])
            public_content = data.get('public_content', [])
            headings = [h.get('text') for h in data.get('headings', [])]
            
            # Pad lists to equal length to make a clean dataframe
            max_len = max(len(categories), len(public_content), len(headings))
            for i in range(max_len):
                detailed_list.append({
                    "Page": page_name,
                    "Heading": headings[i] if i < len(headings) else "",
                    "Category": categories[i] if i < len(categories) else "",
                    "Public Content/Games": public_content[i] if i < len(public_content) else ""
                })

# Create Excel Writer
with pd.ExcelWriter(excel_output_path, engine='openpyxl') as writer:
    # 1. Write Execution Summary Sheet
    if summary_list:
        df_summary = pd.DataFrame(summary_list)
        df_summary.columns = [c.replace('_', ' ').title() for c in df_summary.columns]
        df_summary.to_excel(writer, sheet_name='Scrape Summary', index=False)
        print("Written 'Scrape Summary' sheet.")
        
    # 2. Write Details Sheet
    if detailed_list:
        df_details = pd.DataFrame(detailed_list)
        df_details.to_excel(writer, sheet_name='Extracted Content Details', index=False)
        print("Written 'Extracted Content Details' sheet.")

print(f"Excel report successfully generated at: {excel_output_path}")
