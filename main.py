from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import pandas as pd
from typing import Optional

# We can import your existing cover helper directly into the API!
from igpb_helper import get_game_cover 

app = FastAPI(title="Smart Backlog API - Phase 2")

# --- 1. CORS CONFIGURATION ---
# This allows your future React frontend to talk to this backend safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, you'd change "*" to your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HELPER FUNCTIONS ---
def get_db_connection():
    conn = sqlite3.connect('smart_backlog.db')
    conn.row_factory = sqlite3.Row
    return conn

class StatusUpdate(BaseModel):
    status: str

# --- 2. THE NEW /API/ ROUTES ---

@app.get("/")
def health_check():
    return {"status": "Production API is running natively!"}

@app.get("/api/games")
def get_games(status: Optional[str] = Query("active", description="'active', 'removed', or 'all'")):
    """Fetch games with built-in IGDB cover fetching."""
    try:
        conn = get_db_connection()
        
        # Load tables using Pandas for easy manipulation
        backlog_df = pd.read_sql("SELECT * FROM games_backlog", conn)
        conn.close()

        # Apply the Essential Tier exception logic you built earlier
        is_essential = backlog_df['tier'].astype(str).str.contains('Essential', case=False, na=False)
        is_removed = backlog_df['status'] == 'Removed'
        is_active = backlog_df['status'] != 'Removed'
        is_null_status = backlog_df['status'].isna()

        if status == "active":
            df = backlog_df[is_active | is_null_status | (is_removed & is_essential)].copy()
        elif status == "removed":
            df = backlog_df[is_removed & ~is_essential].copy()
        else:
            df = backlog_df.copy()

        # Ensure custom columns exist and clean data for JSON
        if 'my_hours' not in df.columns:
            df['my_hours'] = 0.0
        if 'personal_status' not in df.columns:
            df['personal_status'] = '📥 Backlog'

        df = df.fillna("") # Clean NaNs for JSON serialization
        
        games_list = []
        for _, row in df.iterrows():
            game_dict = row.to_dict()
            # If the database doesn't have a cover URL, the API fetches the placeholder/IGDB one automatically!
            if not game_dict.get('cover_image_url'):
                game_dict['cover_image_url'] = get_game_cover(game_dict.get('game', 'Unknown'))
            games_list.append(game_dict)
            
        return games_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
def get_dashboard_stats():
    """Calculates all KPIs so the frontend doesn't have to do the math."""
    try:
        conn = get_db_connection()
        backlog_df = pd.read_sql("SELECT status, tier FROM games_backlog", conn)
        conn.close()
        
        # Determine active games
        is_essential = backlog_df['tier'].astype(str).str.contains('Essential', case=False, na=False)
        is_removed = backlog_df['status'] == 'Removed'
        is_active = backlog_df['status'] != 'Removed'
        is_null_status = backlog_df['status'].isna()
        
        active_count = len(backlog_df[is_active | is_null_status | (is_removed & is_essential)])
        leaving_soon_count = len(backlog_df[backlog_df['status'] == 'Leaving Soon'])

        # Get Playtime Stats from PSN CSV
        total_hours = 0.0
        avg_hours = 0.0
        try:
            psn_df = pd.read_csv("psn_games.csv")
            psn_df['play_duration_hours'] = pd.to_numeric(psn_df['play_duration_hours'], errors='coerce').fillna(0.0)
            played_games = psn_df[psn_df['play_duration_hours'] > 0]
            
            total_hours = played_games['play_duration_hours'].sum()
            if not played_games.empty:
                avg_hours = played_games['play_duration_hours'].mean()
        except FileNotFoundError:
            pass # Failsafe if CSV is missing

        return {
            "total_games_available": active_count,
            "games_leaving_soon": leaving_soon_count,
            "total_hours_played": round(total_hours, 1),
            "average_playtime": round(avg_hours, 1)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/games/{game_name}/status")
def update_game_status(game_name: str, update: StatusUpdate):
    """Updates the personal status of a game"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("ALTER TABLE games_backlog ADD COLUMN personal_status TEXT DEFAULT '📥 Backlog'")
        except sqlite3.OperationalError:
            pass 
            
        cursor.execute("UPDATE games_backlog SET personal_status = ? WHERE game = ?", (update.status, game_name))
        conn.commit()
        conn.close()
        
        return {"message": f"Successfully updated {game_name} to {update.status}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# Add this class right underneath your StatusUpdate class:
class ChatRequest(BaseModel):
    query: str

# ... (keep your other routes here) ...

# Add this entirely new endpoint at the bottom of the file:
@app.post("/api/chat")
def chat_with_agent(req: ChatRequest):
    """Passes the user query to the Langchain AI agent"""
    try:
        from ai_agent import ask_gaming_agent
        answer = ask_gaming_agent(req.query)
        return {"response": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))