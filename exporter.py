import pandas as pd
from database import Database

class Exporter:
    def __init__(self, output_file: str = 'Memory_Companies_Revenue.xlsx'):
        self.output_file = output_file

    def export_to_excel(self, db: Database):
        print(f"Exporting data from database to {self.output_file}...")
        data = db.get_all_data()
        
        if not data:
            print("No data to export.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Rename columns to match the requested format
        # We drop exact_publish_date so there is no K column
        df.rename(columns={
            'stock_id': '公司代號',
            'data_year': '資料年份',
            'data_month': '資料月份',
            'revenue_current': '本月營收',
            'revenue_last_year': '去年同期',
            'diff_amount': '增減金額',
            'diff_percent': '增減百分比',
            'ytd_current': '本年累積',
            'ytd_last_year': '去年累計',
            'ytd_diff_amount': '累積增減金額',
            'ytd_diff_percent': '累積增減百分比',
            'remarks': '備註'
        }, inplace=True)
        
        # Drop exact_publish_date
        if 'exact_publish_date' in df.columns:
            df.drop(columns=['exact_publish_date'], inplace=True)
        
        # Sort by year and month descending for better view
        df.sort_values(by=['資料年份', '資料月份'], ascending=[False, False], inplace=True)

        try:
            with pd.ExcelWriter(self.output_file, engine='openpyxl') as writer:
                # Group by stock_id
                grouped = df.groupby('公司代號')
                for stock_id, group in grouped:
                    # Drop the '公司代號' column as it's redundant in the individual sheet
                    sheet_data = group.drop(columns=['公司代號'])
                    sheet_data.to_excel(writer, sheet_name=str(stock_id), index=False)
            print(f"Successfully exported data to {self.output_file}.")
        except Exception as e:
            print(f"Error exporting to Excel: {e}")

import requests
from bs4 import BeautifulSoup
import time

def get_company_name(stock_id):
    """
    Crawls the company Chinese name from MOPS to satisfy the user's request.
    """
    url = 'https://mopsov.twse.com.tw/mops/web/ajax_t05st10_ifrs'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
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
        'year': '113',
        'month': '01'
    }
    try:
        r = requests.post(url, headers=headers, data=data, timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        comp_td = soup.find('td', class_='compName')
        if comp_td:
            text = comp_td.get_text(strip=True)
            if ')' in text and '公司提供' in text:
                name = text.split(')')[1].split('公司提供')[0].strip().replace('\u3000', '')
                return name
    except Exception as e:
        print(f"Error getting name for {stock_id}: {e}")
    return ""

def export_summary(db: Database, stock_list: list, output_filename: str = 'Memory_Revenue_Summary.xlsx'):
    data = db.get_all_data()
    if not data:
        print("No data available to generate summary.")
        return

    df = pd.DataFrame(data)
    
    # Reorder stock_list so 4967 is first
    if '4967' in stock_list:
        stock_list = ['4967'] + [s for s in stock_list if s != '4967']
        
    # Hardcode company names to avoid hitting MOPS API limits
    HARDCODED_NAMES = {
        '4967': '十銓',
        '3260': '威剛',
        '2451': '創見',
        '5289': '宜鼎',
        '8271': '宇瞻',
        '4973': '廣穎',
        '3135': '凌航',
        '2408': '南亞科',
        '8299': '群聯',
        '2344': '華邦電',
        '2337': '旺宏',
        '3006': '晶豪科',
        '5351': '鈺創'
    }
    
    print("Assigning company names...")
    company_names = {}
    for stock_id in stock_list:
        name = HARDCODED_NAMES.get(stock_id, "")
        if name:
            company_names[stock_id] = f"{stock_id} {name}"
        else:
            company_names[stock_id] = f"{stock_id}"

    # Get all distinct year, month sorted descending
    distinct_ym = df[['data_year', 'data_month']].drop_duplicates().sort_values(by=['data_year', 'data_month'], ascending=[False, False])
    
    print(f"Generating summary with multiple sheets to {output_filename}...")
    
    df_dict = {}

    with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
        for _, row in distinct_ym.iterrows():
            year = int(row['data_year'])
            month = int(row['data_month'])
            
            # Calculate previous month
            if month == 1:
                prev_year = year - 1
                prev_month = 12
            else:
                prev_year = year
                prev_month = month - 1
                
            # Prepare rows
            summary_data = {
                '公司': [
                    '當月營收',
                    '上月營收',
                    '去年當月營收',
                    '上月比較增減(%)',
                    '去年同月增減(%)',
                    '當月累積營收',
                    '去年累積營收',
                    '前期比較增減',
                    '備註'
                ]
            }
            
            for stock_id in stock_list:
                stock_df = df[df['stock_id'] == stock_id]
                
                # Current month data
                curr_data = stock_df[(stock_df['data_year'] == year) & (stock_df['data_month'] == month)]
                
                # Previous month data
                prev_data = stock_df[(stock_df['data_year'] == prev_year) & (stock_df['data_month'] == prev_month)]
                
                if not curr_data.empty:
                    curr_row = curr_data.iloc[0]
                    curr_rev = curr_row['revenue_current']
                    last_yr_rev = curr_row['revenue_last_year']
                    yoy_pct = curr_row['diff_percent']
                    ytd_curr = curr_row['ytd_current']
                    ytd_last = curr_row['ytd_last_year']
                    ytd_yoy_pct = curr_row['ytd_diff_percent']
                    remarks = curr_row.get('remarks', '')
                else:
                    curr_rev = 'N/A'
                    last_yr_rev = 'N/A'
                    yoy_pct = 'N/A'
                    ytd_curr = 'N/A'
                    ytd_last = 'N/A'
                    ytd_yoy_pct = 'N/A'
                    remarks = ''
                    
                if not prev_data.empty:
                    prev_row = prev_data.iloc[0]
                    prev_rev = prev_row['revenue_current']
                else:
                    prev_rev = 'N/A'
                    
                # Calculate MoM %
                if curr_rev != 'N/A' and prev_rev != 'N/A' and prev_rev != 0:
                    try:
                        mom_pct = round((float(curr_rev) - float(prev_rev)) / float(prev_rev) * 100, 2)
                    except:
                        mom_pct = 'N/A'
                else:
                    mom_pct = 'N/A'
                    
                col_name = company_names.get(stock_id, stock_id)
                summary_data[col_name] = [
                    curr_rev,
                    prev_rev,
                    last_yr_rev,
                    mom_pct,
                    yoy_pct,
                    ytd_curr,
                    ytd_last,
                    ytd_yoy_pct,
                    remarks
                ]
                
            summary_df = pd.DataFrame(summary_data)
            
            # Use western year + month for sheet name (e.g. "2026年5月")
            sheet_name = f"{year}年{month}月"
            
            summary_df.to_excel(writer, sheet_name=sheet_name, index=False)
            df_dict[sheet_name] = summary_df
            
    print(f"Successfully generated summary: {output_filename}")
    return df_dict
