from fastapi import FastAPI, HTTPException
import sqlite3
import pandas as pd
from pydantic import BaseModel

app = FastAPI(title="Smart Backlog API")

# Helper function to connect to the DB
def get_db_connection():
    conn = sqlite3.connect('smart_backlog.db')
    conn.row_factory = sqlite3.Row  # Returns rows as dictionaries
    return conn

@app.get("/")
def health_check():
    return {"status": "API is running natively!"}

@app.get("/games")
def get_all_games(limit: int | None = None):
    """Fetch games from the backlog"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Using pure sqlite3 instead of pandas to avoid NaN JSON errors
        if limit is None:
            cursor.execute("SELECT * FROM games_backlog")
        else:
            cursor.execute("SELECT * FROM games_backlog LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        # Convert the SQLite rows directly to a list of dictionaries
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/games/search/{game_name}")
def search_game(game_name: str):
    """Search for a specific game by name"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM games_backlog WHERE game LIKE ?"
        cursor.execute(query, (f'%{game_name}%',))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {"message": "Game not found"}
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/games/active")
def get_active_games(limit: int | None = None):
    """Fetch only active games (Active or Leaving Soon, excluding Removed)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if limit is None:
            cursor.execute("SELECT * FROM games_backlog WHERE status IS NULL OR status != 'Removed'")
        else:
            cursor.execute("SELECT * FROM games_backlog WHERE status IS NULL OR status != 'Removed' LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/games/removed")
def get_removed_games():
    """Fetch games marked as Removed (from Excel status column)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM games_backlog WHERE status = 'Removed'")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/psn/games")
def get_psn_games():
    """Fetch all PSN games with playtime data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM psn_games")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
class StatusUpdate(BaseModel):
    status: str

@app.put("/games/{game_name}/status")
def update_game_status(game_name: str, update: StatusUpdate):
    """Updates the personal status of a game"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Safely add the column if it doesn't exist yet (prevents crashing on first run)
        try:
            cursor.execute("ALTER TABLE games_backlog ADD COLUMN personal_status TEXT DEFAULT 'Backlog'")
        except sqlite3.OperationalError:
            pass # Column already exists!
            
        # Update the specific game
        cursor.execute("UPDATE games_backlog SET personal_status = ? WHERE game = ?", (update.status, game_name))
        conn.commit()
        conn.close()
        
        return {"message": f"Successfully updated {game_name} to {update.status}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))