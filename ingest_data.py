import pandas as pd
import sqlite3

def sync_sheet_to_db():
    # 1. Connect to SQLite (this will automatically create 'smart_backlog.db' in your folder)
    conn = sqlite3.connect('smart_backlog.db')
    
    # 2. Your exact Google Sheet ID and GID from the URL you provided
    sheet_id = "19RorxFhWc2lHocg4c9zrVssSwZq1u2nPcpTsAvzdJQw"
    gid = "1938605355"
    
    # Construct the live CSV export URL
    csv_export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    print("Fetching live data from Google Sheets...")
    
    try:
        # 3. Read the live sheet
        df = pd.read_csv(csv_export_url, skiprows=1)
        
        # 4. Clean up column names (makes them lowercase and replaces spaces with underscores for SQL best practices)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # 5. Push the data into the SQLite database
        # Using if_exists='replace' means every time this script runs, it perfectly mirrors your live sheet
        df.to_sql('games_backlog', conn, if_exists='replace', index=False)
        
        print("✅ Successfully ingested data into SQLite!")
        
        # Quick validation check to see the first 5 rows
        print("\n--- Database Preview ---")
        preview = pd.read_sql('SELECT * FROM games_backlog LIMIT 5', conn)
        print(preview)
        
    except Exception as e:
        print(f"❌ Error fetching or saving data: {e}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    sync_sheet_to_db()