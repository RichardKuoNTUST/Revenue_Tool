from database import Database
from scraper import Scraper
from exporter import Exporter, export_summary

MEMORY_COMPANIES = [
    '2408', '2344', '2337', '3260', '2451', '8271',
    '4967', '8299', '5289', '3006', '5351'
]

def main():
    print("=========================================")
    print("Starting Historical Backfill for Remarks")
    print("=========================================")
    
    db = Database()
    
    # Run full scraper to fetch missing remarks
    scraper = Scraper(start_year_minguo=109)
    scraper.run_scraper(MEMORY_COMPANIES, db)
    
    # Export full data
    exporter = Exporter()
    exporter.export_to_excel(db)
    
    # Generate Summary
    export_summary(db, MEMORY_COMPANIES)
    
    print("=========================================")
    print("Historical Backfill Complete!")
    print("=========================================")

if __name__ == '__main__':
    main()
