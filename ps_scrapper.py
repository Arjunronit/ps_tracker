import csv
import sqlite3
from datetime import datetime
from psnawp_api import PSNAWP

# Paste your active npsso cookie here
NPSSO_CODE = "1nc0lF1tjR8tll9kPK3WScHlfL3i3h85NhjoxyoPquNsUHisNBl0ggB76iHTLlok"
DB_PATH = "smart_backlog.db"
CSV_PATH = "psn_games.csv"


def ensure_db_schema(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS psn_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title_id TEXT,
            name TEXT NOT NULL,
            category TEXT,
            play_count INTEGER,
            first_played TEXT,
            last_played TEXT,
            play_duration_hours REAL,
            image_url TEXT,
            synced_at TEXT,
            UNIQUE(title_id, name)
        )'''
    )
    try:
        cursor.execute("ALTER TABLE games_backlog ADD COLUMN my_hours REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass
    conn.commit()


def duration_to_hours(duration) -> float:
    if duration is None:
        return 0.0
    return round(duration.total_seconds() / 3600, 1)


def maybe_iso(dt) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def normalize_name(name: str) -> str:
    return name.replace("®", "").replace("™", "").strip()


def extract_all_psn_games() -> None:
    print("Authenticating with PlayStation Network...")
    try:
        psnawp = PSNAWP(NPSSO_CODE)
        me = psnawp.me()
        print(f"Logged in as: {me.online_id}")
    except Exception as e:
        print(f"PSN auth failed. Your cookie might be expired: {e}")
        return

    print("Connecting to local database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    ensure_db_schema(conn)

    print("Fetching all PSN title stats...")
    stats = me.title_stats(limit=None, page_size=200)

    total = 0
    matched = 0
    inserted = 0
    cursor.execute("DELETE FROM psn_games")
    conn.commit()

    for game in stats:
        total += 1
        name = normalize_name(game.name or "")
        if not name:
            continue

        play_hours = duration_to_hours(game.play_duration)
        category = str(game.category) if game.category is not None else None
        first_played = maybe_iso(game.first_played_date_time)
        last_played = maybe_iso(game.last_played_date_time)
        title_id = game.title_id
        image_url = game.image_url

        cursor.execute(
            """INSERT OR REPLACE INTO psn_games (
                title_id,
                name,
                category,
                play_count,
                first_played,
                last_played,
                play_duration_hours,
                image_url,
                synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                title_id,
                name,
                category,
                game.play_count,
                first_played,
                last_played,
                play_hours,
                image_url,
                datetime.utcnow().isoformat(),
            ),
        )
        inserted += 1

        search_name = f"%{name}%"
        cursor.execute("UPDATE games_backlog SET my_hours = ? WHERE game LIKE ?", (play_hours, search_name))
        if cursor.rowcount > 0:
            print(f"  -> Synced {name}: {play_hours} hrs")
            matched += 1

    conn.commit()

    print(f"\nFinished extracting {total} PSN titles.")
    print(f"Matched {matched} titles to backlog rows.")
    print(f"Saved {inserted} rows into psn_games table.")

    print(f"Exporting extracted PSN titles to {CSV_PATH}...")
    cursor.execute(
        "SELECT title_id, name, category, play_count, play_duration_hours, image_url, first_played, last_played FROM psn_games"
    )
    rows = cursor.fetchall()
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "title_id",
            "name",
            "category",
            "play_count",
            "play_duration_hours",
            "image_url",
            "first_played",
            "last_played",
        ])
        writer.writerows(rows)

    conn.close()
    print("Done. You can now compare psn_games.csv against your Excel backlog.")


if __name__ == "__main__":
    extract_all_psn_games()
