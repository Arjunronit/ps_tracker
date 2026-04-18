"""
Sync game covers from IGDB and store URLs in the database.
Only fetches covers for non-removed games.
"""
import sqlite3
import requests
import urllib.parse
from igpb_helper import CLIENT_ID, get_igdb_token

# Note: CLIENT_ID may be None if not configured - functions handle this gracefully

def get_db_connection():
    conn = sqlite3.connect('smart_backlog.db')
    conn.row_factory = sqlite3.Row
    return conn

def ensure_cover_column():
    """Add cover_image_url column if it doesn't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE games_backlog ADD COLUMN cover_image_url TEXT")
        conn.commit()
        print("✅ Added cover_image_url column")
    except sqlite3.OperationalError:
        print("ℹ️ cover_image_url column already exists")
    finally:
        conn.close()

def fetch_cover_from_igdb(game_name: str) -> str:
    """Fetch cover URL from IGDB API"""
    token = get_igdb_token()
    if not token:
        safe_name = urllib.parse.quote(game_name)
        return f"https://placehold.co/264x374/222222/FFFFFF/png?text={safe_name}"
    
    url = "https://api.igdb.com/v4/games"
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {token}',
    }
    
    clean_name = game_name.replace("'", "").replace(":", "")
    body = f'search "{clean_name}"; fields name, cover.image_id; limit 1;'
    
    try:
        response = requests.post(url, headers=headers, data=body)
        if response.status_code == 200 and response.json():
            data = response.json()
            image_id = data[0]['cover']['image_id']
            return f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"
    except Exception as e:
        print(f"❌ Error fetching {game_name}: {e}")
    
    # Fallback
    safe_name = urllib.parse.quote(game_name)
    return f"https://placehold.co/264x374/222222/FFFFFF/png?text={safe_name}"

def sync_covers():
    """Sync covers for all active games missing cover_image_url"""
    ensure_cover_column()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get games that are Active or Leaving Soon (not Removed)
    cursor.execute("""
        SELECT game FROM games_backlog 
        WHERE (cover_image_url IS NULL OR cover_image_url = '')
        AND (status IS NULL OR status != 'Removed')
    """)
    
    games = cursor.fetchall()
    total = len(games)
    
    print(f"\n🎮 Syncing covers for {total} games...")
    
    for idx, row in enumerate(games, 1):
        game_name = row['game']
        print(f"[{idx}/{total}] Fetching cover for {game_name}...", end=" ")
        
        cover_url = fetch_cover_from_igdb(game_name)
        
        cursor.execute(
            "UPDATE games_backlog SET cover_image_url = ? WHERE game = ?",
            (cover_url, game_name)
        )
        conn.commit()
        print("✅")
    
    conn.close()
    print(f"\n✨ Sync complete! {total} games updated.\n")

if __name__ == "__main__":
    sync_covers()
