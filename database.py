import sqlite3
from typing import List, Dict, Any

class Database:
    def __init__(self, db_name: str = 'revenue.db'):
        self.db_name = db_name
        self.conn = None
        self._create_table()

    def _get_connection(self):
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_name)
        return self.conn

    def _create_table(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # We will keep the table and use UPSERT
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monthly_revenue (
                stock_id TEXT,
                data_year INTEGER,
                data_month INTEGER,
                revenue_current INTEGER,
                revenue_last_year INTEGER,
                diff_amount INTEGER,
                diff_percent REAL,
                ytd_current INTEGER,
                ytd_last_year INTEGER,
                ytd_diff_amount INTEGER,
                ytd_diff_percent REAL,
                remarks TEXT,
                exact_publish_date TEXT,
                UNIQUE(stock_id, data_year, data_month)
            )
        ''')
        conn.commit()

    def upsert_revenue_data(self, records: List[Dict[str, Any]]):
        if not records:
            return
            
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.executemany('''
            INSERT INTO monthly_revenue (
                stock_id, data_year, data_month, revenue_current, revenue_last_year,
                diff_amount, diff_percent, ytd_current, ytd_last_year, ytd_diff_amount, ytd_diff_percent,
                remarks, exact_publish_date
            )
            VALUES (
                :stock_id, :data_year, :data_month, :revenue_current, :revenue_last_year,
                :diff_amount, :diff_percent, :ytd_current, :ytd_last_year, :ytd_diff_amount, :ytd_diff_percent,
                :remarks, :exact_publish_date
            )
            ON CONFLICT(stock_id, data_year, data_month) DO UPDATE SET
                revenue_current=excluded.revenue_current,
                revenue_last_year=excluded.revenue_last_year,
                diff_amount=excluded.diff_amount,
                diff_percent=excluded.diff_percent,
                ytd_current=excluded.ytd_current,
                ytd_last_year=excluded.ytd_last_year,
                ytd_diff_amount=excluded.ytd_diff_amount,
                ytd_diff_percent=excluded.ytd_diff_percent,
                remarks=excluded.remarks,
                exact_publish_date=excluded.exact_publish_date
        ''', records)
        conn.commit()

    def get_all_data(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM monthly_revenue ORDER BY stock_id, data_year, data_month')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
        
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
