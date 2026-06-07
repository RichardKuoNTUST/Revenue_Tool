import sqlite3

c = sqlite3.connect('revenue.db')
cursor = c.cursor()
cursor.execute("SELECT stock_id, data_year, data_month, diff_percent, ytd_diff_percent, remarks FROM monthly_revenue LIMIT 100")
rows = cursor.fetchall()
for r in rows:
    if r[5] and str(r[5]).strip() != '-' and str(r[5]).strip() != 'None' and str(r[5]).strip() != '0':
        print(r)
print("Done")
