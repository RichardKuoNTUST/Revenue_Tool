import sqlite3
import pandas as pd

def check_progress():
    try:
        conn = sqlite3.connect('revenue.db')
        df = pd.read_sql_query("SELECT stock_id as '公司代號', COUNT(*) as '已抓取月數' FROM monthly_revenue GROUP BY stock_id", conn)
        
        print("========================================")
        print("Database Progress:")
        print("========================================")
        print(df.to_string(index=False))
        print("========================================")
        print(f"Total Rows: {df['已抓取月數'].sum()}")
        
        conn.close()
    except Exception as e:
        print("Error: ", e)

if __name__ == '__main__':
    check_progress()
