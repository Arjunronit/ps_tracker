import os
import requests
import urllib.parse
import streamlit as st

CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

# Note: No error raised here - functions will handle missing credentials gracefully

@st.cache_data(ttl=3500)
def get_igdb_token():
    if not CLIENT_ID or not CLIENT_SECRET:
        return None
    
    auth_url = f"https://id.twitch.tv/oauth2/token?client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}&grant_type=client_credentials"
    response = requests.post(auth_url)
    if response.status_code == 200:
        return response.json()['access_token']
    return None

@st.cache_data(ttl=86400)
def get_game_cover(game_name: str):
    # Use placehold.co for fallback cover images.
    safe_name = urllib.parse.quote(game_name)
    fallback_url = f"https://placehold.co/264x374/222222/FFFFFF/png?text={safe_name}"

    token = get_igdb_token()
    if not token:
        return fallback_url

    url = "https://api.igdb.com/v4/games"
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {token}',
    }
    
    clean_name = game_name.replace("'", "").replace(":", "")
    body = f'search "{clean_name}"; fields name, cover.image_id; limit 1;'
    
    try:
        response = requests.post(url, headers=headers, data=body)
        if response.status_code == 200:
            data = response.json()
            image_id = data[0]['cover']['image_id']
            return f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"
    except Exception:
        pass
        
    return fallback_url
