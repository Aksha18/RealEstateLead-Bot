# google_sheets.py
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os

def setup_google_sheets():
    """
    Setup Google Sheets API
    
    Prerequisites:
    1. Go to https://console.cloud.google.com
    2. Create a project
    3. Enable Google Sheets API
    4. Create Service Account
    5. Download credentials JSON
    6. Share your Google Sheet with the service account email
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Load credentials from JSON file
    creds = Credentials.from_service_account_file(
        'credentials.json',  # Your downloaded service account JSON
        scopes=SCOPES
    )
    
    client = gspread.authorize(creds)
    return client


def save_to_google_sheets(lead_data):
    """
    Save lead data to Google Sheets
    Auto-creates headers if missing
    """
    try:
        client = setup_google_sheets()
        sheet = client.open("Real Estate Leads").sheet1

        # ---- Header check (the correct way) ----
        headers = sheet.row_values(1)

        if not headers or all(cell.strip() == "" for cell in headers):
            headers = [
                'Timestamp', 'Name', 'Phone', 'Email', 'Property Type',
                'Purpose', 'Budget', 'Location', 'Bedrooms',
                'Timeline', 'Source', 'Status'
            ]

            # Always force them into row 1
            sheet.insert_row(headers, 1)

            # Format header row
            sheet.format('A1:L1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.4, 'green': 0.6, 'blue': 0.8}
            })

            print("✓ Headers created")

        # ---- Prepare row data ----
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            lead_data.get('name', ''),
            lead_data.get('phone') or '',
            lead_data.get('email') or '',
            lead_data.get('property_type', ''),
            '',  # purpose
            lead_data.get('budget', ''),
            lead_data.get('location', ''),
            '',  # bedrooms
            '',  # timeline
            'AI Chatbot',
            'New'
        ]

        # ---- Append lead ----
        sheet.append_row(row)
        print("✓ Saved to Google Sheets!")
        return True

    except Exception as e:
        print(f"✗ Google Sheets error: {e}")
        return False

def create_headers_if_needed():
    """
    Create headers in Google Sheet if it's empty
    Run this once to set up your sheet
    """
    try:
        client = setup_google_sheets()
        sheet = client.open("Real Estate Leads").sheet1
        
        # Check if sheet is empty
        if not sheet.row_values(1):
            headers = [
                'Timestamp',
                'Name',
                'Phone',
                'Email',
                'Property Type',
                'Purpose',
                'Budget',
                'Location',
                'Bedrooms',
                'Timeline',
                'Source',
                'Status'
            ]
            sheet.append_row(headers)
            
            # Format header row
            sheet.format('A1:L1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.4, 'green': 0.6, 'blue': 0.8}
            })
            
            print("✓ Headers created!")
            
    except Exception as e:
        print(f"✗ Error creating headers: {e}")

# Alternative: Using gspread-dataframe for easier data handling
def save_to_sheets_advanced(lead_data):
    """
    Advanced version using pandas for better data handling
    
    Install: pip install gspread-dataframe pandas
    """
    import pandas as pd
    from gspread_dataframe import set_with_dataframe
    
    try:
        client = setup_google_sheets()
        sheet = client.open("Real Estate Leads").sheet1
        
        # Convert to DataFrame
        df = pd.DataFrame([lead_data])
        
        # Get existing data
        existing = sheet.get_all_records()
        if existing:
            existing_df = pd.DataFrame(existing)
            df = pd.concat([existing_df, df], ignore_index=True)
        
        # Write back
        set_with_dataframe(sheet, df)
        print("✓ Saved to Google Sheets (advanced)!")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False