import gspread
from gspread_dataframe import set_with_dataframe
import pandas as pd
import json
import os

def upload_summary_to_gsheets(df_dict: dict, spreadsheet_url: str):
    """
    df_dict: A dictionary where keys are sheet names (e.g., '2026年5月') and values are DataFrames.
    spreadsheet_url: The URL of the Google Sheet.
    """
    print("Authenticating with Google Sheets...")
    
    # Check if we are in Github Actions or local
    # We expect the JSON content to be passed via env var or a local file
    creds_file = 'service_account.json'
    if 'GCP_CREDENTIALS' in os.environ:
        creds_info = json.loads(os.environ['GCP_CREDENTIALS'])
        gc = gspread.service_account_from_dict(creds_info)
    elif os.path.exists(creds_file):
        gc = gspread.service_account(filename=creds_file)
    else:
        print("Error: Google Credentials not found. Please provide service_account.json or GCP_CREDENTIALS env var.")
        return

    try:
        sh = gc.open_by_url(spreadsheet_url)
    except Exception as e:
        print(f"Error opening Spreadsheet: {e}")
        return

    print(f"Successfully opened spreadsheet: {sh.title}")
    
    existing_worksheets = {ws.title: ws for ws in sh.worksheets()}
    
    for sheet_name, df in df_dict.items():
        print(f"Uploading data for {sheet_name}...")
        
        # Check if worksheet exists, if not create it
        if sheet_name in existing_worksheets:
            ws = existing_worksheets[sheet_name]
            ws.clear()
        else:
            # Create a new worksheet with enough rows and columns
            ws = sh.add_worksheet(title=sheet_name, rows=str(len(df) + 10), cols=str(len(df.columns) + 5))
            
        # Convert any numpy types hidden in object columns to native python types
        # This prevents "TypeError: Object of type int64 is not JSON serializable"
        df_clean = df.applymap(lambda x: x.item() if hasattr(x, 'item') else x)
            
        # Write dataframe
        set_with_dataframe(ws, df_clean)
        print(f"  Done uploading {sheet_name}.")

    print("All Google Sheets updates complete.")
