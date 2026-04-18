import pandas as pd
import sqlite3

def sync_sheet_to_db():
    conn = sqlite3.connect('smart_backlog.db')
    
    sheet_id = "19RorxFhWc2lHocg4c9zrVssSwZq1u2nPcpTsAvzdJQw"
    gid = "1938605355"
    csv_export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    print("Fetching live data from Google Sheets...")
    
    try:
        # 1. Fetch fresh data from Google Sheets
        new_df = pd.read_csv(csv_export_url, skiprows=1)
        new_df.columns = new_df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # 2. Fetch existing local tracking data (if the table exists)
        try:
            existing_df = pd.read_sql(
                'SELECT game, personal_status, cover_image_url, my_hours FROM games_backlog', 
                conn
            )
            print("Found existing local data. Merging to preserve progress...")
            
            # Left merge ensures we keep all rows from the live sheet, 
            # but attach the local custom data where the game names match.
            final_df = new_df.merge(existing_df, on='game', how='left')
            
            # If a new game was added to the sheet, it won't have a status yet
            if 'personal_status' in final_df.columns:
                final_df['personal_status'] = final_df['personal_status'].fillna('📥 Backlog')
                
        except sqlite3.OperationalError:
            print("First run detected. Creating new table structure...")
            final_df = new_df
            # Initialize the custom columns so the app doesn't crash later
            final_df['personal_status'] = '📥 Backlog'
            final_df['cover_image_url'] = None
            final_df['my_hours'] = 0.0

        # 3. Push the merged data safely back to SQLite
        final_df.to_sql('games_backlog', conn, if_exists='replace', index=False)
        
        print("✅ Successfully synced Google Sheet and preserved local tracking!")
        
    except Exception as e:
        print(f"❌ Error during ETL process: {e}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    sync_sheet_to_db()