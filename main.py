from database import Database
from scraper import Scraper
from exporter import Exporter

MEMORY_COMPANIES = [
    '2408', # 南亞科
    '2344', # 華邦電
    '2337', # 旺宏
    '3260', # 威剛
    '2451', # 創見
    '8271', # 宇瞻
    '4967', # 十銓
    '8299', # 群聯
    '5289', # 宜鼎
    '3006', # 晶豪科
    '5351'  # 鈺創
]

def main():
    print("=========================================")
    print("Starting Precise Revenue Scraper")
    print("=========================================")
    
    # 1. Initialize Database
    db = Database()
    
    # 2. Run Scraper (Incremental mode by default)
    # The scraper fetches only the latest 2 months to save time.
    scraper = Scraper(start_year_minguo=109)
    # If a full historical backfill is needed, you can use:
    # scraper.run_scraper(MEMORY_COMPANIES, db)
    has_new_data = scraper.update_latest_revenue(MEMORY_COMPANIES, db)
    
    # 3. Export full data to Excel
    exporter = Exporter()
    exporter.export_to_excel(db)
    
    # 4. Generate Summary Excel (One file, multiple sheets for each month)
    from exporter import export_summary
    df_dict = export_summary(db, MEMORY_COMPANIES)
    
    # 5. Upload to Google Sheets if there's new data
    from google_sheets import upload_summary_to_gsheets
    import os
    
    SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1U7hktAzdQ3pXQcC5zXJl2quolKaowkJTUnBgAZ00Udc/edit?gid=0#gid=0'
    
    if has_new_data:
        print("New data found! Uploading to Google Sheets...")
        upload_summary_to_gsheets(df_dict, SPREADSHEET_URL)
    else:
        # Check if running in GitHub Actions. If so, don't skip upload for the first run or manual triggers
        # Or we can just skip it to save API calls. Let's just always upload if 'FORCE_UPLOAD' is set.
        if os.environ.get('FORCE_UPLOAD') == '1':
            print("Force upload flag detected. Uploading to Google Sheets...")
            upload_summary_to_gsheets(df_dict, SPREADSHEET_URL)
        else:
            print("No new data found. Skipping Google Sheets upload to save API quotas.")
    
    print("=========================================")
    print("Scraping and Export Complete!")
    print("=========================================")

if __name__ == '__main__':
    main()
