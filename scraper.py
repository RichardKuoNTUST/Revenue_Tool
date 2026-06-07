import requests
import time
import datetime
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from database import Database

class Scraper:
    def __init__(self, start_year_minguo: int = 109):
        # 109 Minguo is 2020
        self.start_year_minguo = start_year_minguo
        self.session = requests.Session()

    def get_current_minguo_year_month(self):
        now = datetime.datetime.now()
        minguo_year = now.year - 1911
        # If today is before the 10th, the previous month's data might not be fully available yet,
        # but we can try to fetch it anyway.
        return minguo_year, now.month

    def get_statutory_publish_date(self, minguo_year: int, month: int) -> str:
        # 營收公布法定期限為次月 10 日
        publish_year = minguo_year + 1911
        publish_month = month + 1
        if publish_month > 12:
            publish_month = 1
            publish_year += 1
        return f"{publish_year}-{publish_month:02d}-10"

    def fetch_revenue_details_for_month(self, stock_id: str, minguo_year: int, month: int) -> Dict[str, Any]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'encodeURIComponent': '1',
            'step': '1',
            'firstin': '1',
            'off': '1',
            'queryName': 'co_id',
            'inpuType': 'co_id',
            'TYPEK': 'all',
            'isnew': 'false',
            'co_id': stock_id,
            'year': str(minguo_year),
            'month': f"{month:02d}"
        }
        
        url = 'https://mopsov.twse.com.tw/mops/web/ajax_t05st10_ifrs'
        max_retries = 3
        for attempt in range(max_retries):
            try:
                r = self.session.post(url, headers=headers, data=data, timeout=15)
                
                # Check for rate limit or security block
                if '過於頻繁' in r.text or 'FOR SECURITY REASONS' in r.text:
                    print(f"Rate limited on {stock_id} {minguo_year}/{month}. Sleeping for 10s...")
                    time.sleep(10)
                    continue
                    
                if r.status_code != 200 or '查無資料' in r.text:
                    return {}
                    
                soup = BeautifulSoup(r.text, 'html.parser')
                tables = soup.find_all('table')
                if not tables:
                    return {}
                    
                break # Success, exit retry loop
                
            except Exception as e:
                print(f"Error fetching {stock_id} {minguo_year}/{month}: {e}")
                if attempt == max_retries - 1:
                    return {}
                time.sleep(5)
                
        else:
            return {}
            
        revenue_data = {}
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['th', 'td'])
                if len(cols) >= 2:
                    header = cols[0].get_text(strip=True)
                    val_str = cols[1].get_text(strip=True).replace(',', '')
                    try:
                        val = float(val_str) if '.' in val_str else int(val_str)
                    except ValueError:
                        val = val_str
                    
                    if '本月' in header and 'revenue_current' not in revenue_data:
                        revenue_data['revenue_current'] = val
                    elif '去年同期' in header and 'revenue_last_year' not in revenue_data:
                        revenue_data['revenue_last_year'] = val
                    elif '增減金額' in header and 'revenue_current' in revenue_data and 'diff_amount' not in revenue_data:
                        revenue_data['diff_amount'] = val
                    elif '增減百分比' in header and 'revenue_current' in revenue_data and 'diff_percent' not in revenue_data:
                        revenue_data['diff_percent'] = val
                    elif '本年累計' in header and 'ytd_current' not in revenue_data:
                        revenue_data['ytd_current'] = val
                    elif '去年累計' in header and 'ytd_last_year' not in revenue_data:
                        revenue_data['ytd_last_year'] = val
                    elif '增減金額' in header and 'ytd_current' in revenue_data and 'ytd_diff_amount' not in revenue_data:
                        revenue_data['ytd_diff_amount'] = val
                    elif '增減百分比' in header and 'ytd_current' in revenue_data and 'ytd_diff_percent' not in revenue_data:
                        revenue_data['ytd_diff_percent'] = val

            # Due to malformed HTML in TWSE (missing TR tags for remarks), find TH directly
            remark_th = soup.find(lambda tag: tag.name == 'th' and ('備註' in tag.text or '說明' in tag.text))
            if remark_th:
                remark_td = remark_th.find_next_sibling('td')
                if remark_td:
                    revenue_data['remarks'] = remark_td.get_text(strip=True).replace('\n', '').replace('\r', '')
                    
        return revenue_data
    def run_scraper(self, stock_list: List[str], db: Database):
        current_year, current_month = self.get_current_minguo_year_month()
        
        for stock_id in stock_list:
            print(f"========== Processing {stock_id} ==========")
            for year in range(self.start_year_minguo, current_year + 1):
                end_month = 12 if year < current_year else current_month
                
                for month in range(1, end_month + 1):
                    details = self.fetch_revenue_details_for_month(stock_id, year, month)
                    time.sleep(1.5) # Increased delay to avoid IP block
                    
                    if details and 'revenue_current' in details:
                        record = {
                            'stock_id': stock_id,
                            'data_year': year + 1911,
                            'data_month': month,
                            'revenue_current': details.get('revenue_current', 0),
                            'revenue_last_year': details.get('revenue_last_year', 0),
                            'diff_amount': details.get('diff_amount', 0),
                            'diff_percent': details.get('diff_percent', 0.0),
                            'ytd_current': details.get('ytd_current', 0),
                            'ytd_last_year': details.get('ytd_last_year', 0),
                            'ytd_diff_amount': details.get('ytd_diff_amount', 0),
                            'ytd_diff_percent': details.get('ytd_diff_percent', 0.0),
                            'remarks': str(details.get('remarks', '')),
                            'exact_publish_date': ''
                        }
                        db.upsert_revenue_data([record])
                    else:
                        print(f"  No data for {stock_id} {year}/{month}")

    def update_latest_revenue(self, stock_list: List[str], db: Database) -> bool:
        """
        Incremental scraper: only fetches the current month and the previous month.
        This ensures fast execution and automatically picks up new revenue data when it is published.
        Returns True if new data was found and written to the database, False otherwise.
        """
        current_year, current_month = self.get_current_minguo_year_month()
        
        # Calculate the previous month
        if current_month == 1:
            prev_year = current_year - 1
            prev_month = 12
        else:
            prev_year = current_year
            prev_month = current_month - 1
            
        # Calculate the month before previous (needed for MoM calculation of the previous month)
        if prev_month == 1:
            prev2_year = prev_year - 1
            prev2_month = 12
        else:
            prev2_year = prev_year
            prev2_month = prev_month - 1
            
        months_to_fetch = [
            (prev2_year, prev2_month),
            (prev_year, prev_month),
            (current_year, current_month)
        ]
        
        # Preload DB to check for differences
        all_data = db.get_all_data()
        existing_records = {}
        for r in all_data:
            key = (r['stock_id'], r['data_year'], r['data_month'])
            existing_records[key] = r.get('revenue_current', 0)
            
        has_new_data = False
        
        print("========== Incremental Update ==========")
        print(f"Fetching data for Minguo: {prev_year}/{prev_month} and {current_year}/{current_month}")
        for stock_id in stock_list:
            print(f"Updating {stock_id}...")
            for year, month in months_to_fetch:
                details = self.fetch_revenue_details_for_month(stock_id, year, month)
                time.sleep(1.5) # Gentle delay to avoid IP block
                
                if details and 'revenue_current' in details:
                    western_year = year + 1911
                    record = {
                        'stock_id': stock_id,
                        'data_year': western_year,
                        'data_month': month,
                        'revenue_current': details.get('revenue_current', 0),
                        'revenue_last_year': details.get('revenue_last_year', 0),
                        'diff_amount': details.get('diff_amount', 0),
                        'diff_percent': details.get('diff_percent', 0.0),
                        'ytd_current': details.get('ytd_current', 0),
                        'ytd_last_year': details.get('ytd_last_year', 0),
                        'ytd_diff_amount': details.get('ytd_diff_amount', 0),
                        'ytd_diff_percent': details.get('ytd_diff_percent', 0.0),
                        'remarks': str(details.get('remarks', '')),
                        'exact_publish_date': ''
                    }
                    
                    key = (stock_id, western_year, month)
                    if key not in existing_records or existing_records[key] != details.get('revenue_current', 0):
                        has_new_data = True
                        
                    db.upsert_revenue_data([record])
                    print(f"  Saved data for {stock_id} {year}/{month}")
                else:
                    print(f"  No data yet for {stock_id} {year}/{month}")
                    
        return has_new_data
