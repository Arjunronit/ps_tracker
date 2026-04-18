import pandas as pd
import sqlite3
import re
from rapidfuzz import process, fuzz

def clean_title(title):
    """Surgically remove platform tags so we can use a stricter matching algorithm."""
    t = str(title)
    # Remove things like "(PlayStation5)"
    t = re.sub(r'\(PlayStation\s*\d*\)', '', t, flags=re.IGNORECASE)
    # Remove "PS4 & PS5"
    t = re.sub(r'\bPS4\s*[&/]\s*PS5\b', '', t, flags=re.IGNORECASE)
    # Remove isolated "PS4" or "PS5"
    t = re.sub(r'\bPS[45]\b', '', t, flags=re.IGNORECASE)
    # Clean up any leftover double spaces
    return ' '.join(t.split())

def sync_hours_from_csv():
    db_path = "smart_backlog.db"
    csv_path = "psn_games.csv"
    
    print(f"Reading PSN data from {csv_path}...")
    try:
        psn_df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"❌ Could not find {csv_path}. Please make sure it exists.")
        return

    print("Connecting to local database...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Reset all tracked hours to 0.0
    try:
        cursor.execute("UPDATE games_backlog SET my_hours = 0.0")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE games_backlog ADD COLUMN my_hours REAL DEFAULT 0.0")
        
    # 2. Fetch all valid game titles from the backlog
    cursor.execute("SELECT game FROM games_backlog WHERE game IS NOT NULL")
    backlog_games = [row[0] for row in cursor.fetchall()]

    matched = 0
    total = len(psn_df)
    
    print(f"Matching {total} games from CSV to your backlog...\n")

    for index, row in psn_df.iterrows():
        raw_name = str(row['name']).strip()
        
        try:
            play_hours = float(row['play_duration_hours'])
        except (ValueError, TypeError):
            play_hours = 0.0
            
        if not raw_name or raw_name.lower() == 'nan' or play_hours <= 0:
            continue

        # Clean the PSN title BEFORE matching
        cleaned_name = clean_title(raw_name)

        # --- UPGRADED MATCHING PIPELINE ---
        # token_sort_ratio is much stricter. It won't merge sequels into originals.
        best_match = process.extractOne(cleaned_name, backlog_games, scorer=fuzz.token_sort_ratio)
        
        # If it's a solid match (85%+)
        if best_match and best_match[1] >= 85:
            matched_title = best_match[0]
            score = best_match[1]
            
            # Final safeguard: Don't merge if one has a '2' or 'II' and the other doesn't
            if ('2' in cleaned_name or 'II' in cleaned_name) and ('2' not in matched_title and 'II' not in matched_title):
                print(f"🛑 Blocked Sequel Mismatch: '{cleaned_name}' tried to match '{matched_title}'")
                continue
            
            cursor.execute("""
                UPDATE games_backlog 
                SET my_hours = my_hours + ? 
                WHERE game = ?
            """, (play_hours, matched_title))
            
            print(f"✅ Matched: '{cleaned_name}' -> '{matched_title}' (Score: {score:.1f})")
            matched += 1
        else:
            # Fallback for weird edge cases using basic SQL LIKE
            search_name = f"%{cleaned_name}%"
            cursor.execute("UPDATE games_backlog SET my_hours = my_hours + ? WHERE game LIKE ?", (play_hours, search_name))
            if cursor.rowcount > 0:
                print(f"⚠️ Fallback Matched: '{cleaned_name}'")
                matched += 1

    conn.commit()
    conn.close()
    print(f"\n✨ Sync complete! Successfully mapped {matched} games to your library.")

if __name__ == "__main__":
    sync_hours_from_csv()