import streamlit as st
import requests
import pandas as pd
import urllib.parse
from igpb_helper import get_game_cover
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Set up the webpage layout
st.set_page_config(page_title="Smart Backlog", page_icon="🎮", layout="wide")

st.title("🎮 Smart PS+ Backlog Manager")
st.markdown("Manage your PlayStation library and ask the AI what to play next.")

# 3 core tabs for a cleaner experience
tab1, tab2, tab3 = st.tabs(["💬 AI Gaming Assistant", "📋 My Library & Stats", "🗑️ Removed Games"])

# --- DATA FETCHING & ESSENTIAL TIER LOGIC ---
@st.cache_data(ttl=60)
def load_game_data():
    """Fetches all games and applies the 'Essential' tier logic"""
    try:
        # Fetch ALL games from the database
        response = requests.get("http://127.0.0.1:8000/games")
        if response.status_code == 200:
            all_games = pd.DataFrame(response.json())
            
            # Logic: It is Active IF it's not Removed OR if it IS Removed but tier is Essential
            is_essential = all_games['tier'].astype(str).str.contains('Essential', case=False, na=False)
            is_removed = all_games['status'] == 'Removed'
            is_active = all_games['status'] != 'Removed'
            is_null_status = all_games['status'].isna()
            
            # Filter DataFrames
            active_df = all_games[is_active | is_null_status | (is_removed & is_essential)].copy()
            removed_df = all_games[is_removed & ~is_essential].copy()
            
            return active_df, removed_df
        return pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to fetch from API: {e}")
        return pd.DataFrame(), pd.DataFrame()

active_df, removed_df = load_game_data()

# Load PSN data directly from the CSV
try:
    psn_df = pd.read_csv("psn_games.csv")
    psn_df['play_duration_hours'] = pd.to_numeric(psn_df['play_duration_hours'], errors='coerce').fillna(0.0)
except FileNotFoundError:
    psn_df = pd.DataFrame()


# --- TAB 1: The AI Agent ---
with tab1:
    st.subheader("Ask your Backlog Agent")
    st.markdown("Ask anything about your game library, playtime, or get recommendations.")
    
    try:
        from ai_agent import ask_gaming_agent
        agent_available = True
    except EnvironmentError as e:
        agent_available = False
        st.warning(f"🤖 AI Agent unavailable: {e}")
        st.info("To enable the AI agent, create a `.env` file with your `GOOGLE_API_KEY`.")
    
    if agent_available:
        if "agent_processing" not in st.session_state:
            st.session_state.agent_processing = False
        if "agent_response" not in st.session_state:
            st.session_state.agent_response = None
        if "last_query" not in st.session_state:
            st.session_state.last_query = ""
        
        if st.session_state.agent_processing:
            st.info("⏳ Agent is processing your request... Please wait.")
        
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                user_query = st.text_input(
                    "Ask your gaming question:",
                    placeholder="What are 3 short RPGs I can play this weekend?",
                    disabled=st.session_state.agent_processing,
                    key="agent_input"
                )
            with col2:
                st.markdown("<div style='margin-top: 28px'></div>", unsafe_allow_html=True)
                submit_disabled = st.session_state.agent_processing or not user_query.strip()
                if st.button("🤖 Ask", disabled=submit_disabled, width="stretch", type="primary"):
                    if user_query.strip():
                        st.session_state.agent_processing = True
                        st.session_state.last_query = user_query.strip()
                        st.session_state.agent_response = None
                        
                        try:
                            with st.spinner("🤖 Agent is analyzing your database..."):
                                answer = ask_gaming_agent(user_query.strip())
                            
                            st.session_state.agent_response = answer
                            st.session_state.agent_processing = False
                            st.session_state.agent_input = ""
                            st.rerun()
                            
                        except Exception as e:
                            st.session_state.agent_processing = False
                            st.error(f"❌ Error communicating with agent: {e}")
        
        if st.session_state.agent_response:
            st.success(f"**Question:** {st.session_state.last_query}")
            with st.container():
                st.markdown("**🤖 Agent Response:**")
                st.write(st.session_state.agent_response)
    else:
        st.error("🤖 AI Agent is not configured. Please set up your GOOGLE_API_KEY in a .env file.")

# --- TAB 2: The Database & Stats ---
with tab2:
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.subheader("Your PlayStation Library")
    with col2:
        if st.button("🔄 Sync Covers", width="stretch"):
            with st.spinner("Syncing covers from IGDB..."):
                import subprocess
                try:
                    subprocess.run(["python", "sync_covers.py"], check=True, cwd="c:\\ps_tracker")
                    st.success("✅ Covers synced!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Sync failed: {e}")
    
    if not active_df.empty:
        df = active_df.copy()
        
        # --- STATS SECTION ---
        if 'my_hours' not in df.columns:
            df['my_hours'] = 0.0
        else:
            df['my_hours'] = pd.to_numeric(df['my_hours'], errors='coerce').fillna(0.0)

        total_games = len(df)
        leaving_soon_count = int((df['status'] == 'Leaving Soon').sum()) if 'status' in df.columns else 0

        # KPI calculation using PSN data
        if not psn_df.empty:
            total_hours = psn_df['play_duration_hours'].sum()
            played_games = psn_df[psn_df['play_duration_hours'] > 0]
            avg_hours = played_games['play_duration_hours'].mean() if not played_games.empty else 0.0
        else:
            total_hours = df['my_hours'].sum()
            avg_hours = df['my_hours'].mean() if total_games else 0.0

        st.markdown("### Quick Stats")
        stat1, stat2, stat3, stat4 = st.columns(4)
        stat1.metric("Total Hours Played", round(total_hours, 1))
        stat2.metric("Average Playtime", round(avg_hours, 1))
        stat3.metric("Games Available Now", total_games)
        stat4.metric("Games Leaving Soon", leaving_soon_count, delta_color="inverse")
        
        # Expandable detailed PSN Stats
        if not psn_df.empty:
            with st.expander("📊 View Detailed PSN Playtime Stats"):
                played = psn_df[psn_df['play_duration_hours'] > 0].copy()
                all_played = played.sort_values('play_duration_hours', ascending=False)
                st.dataframe(
                    all_played[['name', 'category', 'play_count', 'play_duration_hours']].rename(
                        columns={'name': 'Game', 'play_duration_hours': 'Hours', 'play_count': 'Play Count'}
                    ),
                    width="stretch",
                    hide_index=True
                )

        st.divider()

        # --- FILTERS ---
        st.markdown("### Search & Filters")
        platform_col = 'platform' if 'platform' in df.columns else 'system' if 'system' in df.columns else None
        platform_options = ['All'] + (sorted(df[platform_col].dropna().astype(str).unique().tolist()) if platform_col else [])

        filter_col1, filter_col2, filter_col3 = st.columns(3)
        search_title = filter_col1.text_input("Search by title")
        selected_platform = filter_col2.selectbox("Platform", platform_options)
        min_hours = filter_col3.slider("Min playtime (hours)", 0, int(max(df['my_hours'].max(), 0)), 0)

        filtered_df = df.copy()
        if search_title:
            filtered_df = filtered_df[filtered_df.get('game', '').astype(str).str.contains(search_title, case=False, na=False)]
        if selected_platform and selected_platform != 'All' and platform_col:
            filtered_df = filtered_df[filtered_df[platform_col].astype(str) == selected_platform]
        filtered_df = filtered_df[filtered_df['my_hours'] >= min_hours]

        st.markdown(f"**Showing {len(filtered_df)} of {total_games} games**")

        # --- GRID VIEW WITH BATCH FORM ---
        status_options = ["📥 Backlog", "🔥 Playing", "⏸️ On Hold", "✅ Story Complete", "🏆 Platinumed", "♾️ Ongoing", "🛑 Dropped", "🚫 Not Interested"]
        
        if filtered_df.empty:
            st.info("No games match your filters.")
        else:
            with st.form("library_form"):
                submitted = st.form_submit_button("💾 Save All Progress", type="primary")
                
                cols = st.columns(4)
                # Reset index so we can iterate safely for column distribution
                filtered_df = filtered_df.reset_index()
                
                for i, row in filtered_df.iterrows():
                    # 'index' is the original DataFrame index, making the key guaranteed unique
                    original_index = row['index'] 
                    game_title = row.get("game", "Unknown Game")
                    tier = row.get("tier", "Unknown")
                    metacritic = row.get("metacritic", "N/A")
                    hltb = row.get("completion", "Unknown") # Grab time to beat
                    cover_url = row.get("cover_image_url")
                    # Check if it's a Pandas NaN (float), empty string, or actual "nan" text
                    if pd.isna(cover_url) or not str(cover_url).strip() or str(cover_url).lower() == "nan":
                        cover_url = get_game_cover(game_title)
                    my_hours = row.get("my_hours", 0.0)
                    current_status = row.get("personal_status", "📥 Backlog")
                    
                    if current_status not in status_options:
                        current_status = "📥 Backlog"

                    with cols[i % 4]:
                        st.image(cover_url, width='stretch')
                        st.markdown(f"**{game_title}**")
                        # Added Time to beat back into the display
                        st.caption(f"⭐ MC: {metacritic} | 🎮 {tier} | ⏱️ {hltb} hrs")
                        if my_hours > 0:
                            st.caption(f"🔥 Playtime: {my_hours} hrs")
                        
                        st.selectbox(
                            "Progress", 
                            options=status_options, 
                            index=status_options.index(current_status),
                            # FIXED KEY: Using the original DataFrame index to prevent duplicates
                            key=f"status_{original_index}_{game_title}",
                            label_visibility="collapsed"
                        )
                        st.divider()
                
                        if submitted:
                            changes_made = 0
                            for i, row in filtered_df.iterrows():
                                game_title = row.get("game", "Unknown Game")
                                original_index = row['index']
                                original_status = row.get("personal_status", "📥 Backlog")
                                if original_status not in status_options:
                                    original_status = "📥 Backlog"
                                
                                # Match the unique key used in the selectbox
                                new_status = st.session_state.get(f"status_{original_index}_{game_title}")
                                
                                if new_status and new_status != original_status:
                                    # 🚨 CRITICAL FIX: URL Encode the game title! 🚨
                                    # This converts spaces, '&', '?', etc. into safe web characters
                                    safe_title = urllib.parse.quote(game_title, safe="")
                                    
                                    try:
                                        res = requests.put(
                                            f"http://127.0.0.1:8000/games/{safe_title}/status", 
                                            json={"status": new_status}
                                        )
                                        if res.status_code == 200:
                                            changes_made += 1
                                        else:
                                            st.error(f"⚠️ Backend Error for '{game_title}': {res.text}")
                                    except Exception as e:
                                        st.error(f"⚠️ Failed to connect to API for '{game_title}': {e}")
                            
                            if changes_made > 0:
                                st.success(f"✅ Successfully updated {changes_made} games! Refreshing dashboard...")
                                st.cache_data.clear() # Clear cache so new data loads on rerun
                                st.rerun() # Let Streamlit automatically refresh the UI! Do not press F5.
                            else:
                                st.info("No changes detected.")
    else:
        st.info("No active games found in the database.")

# --- TAB 3: Removed Games Reference ---
with tab3:
    st.subheader("🗑️ Removed from PlayStation Plus")
    st.markdown("These games are no longer available on the service (excluding claimed Essential games).")
    
    if not removed_df.empty:
        display_cols = ['game', 'system', 'tier', 'metacritic', 'release']
        existing_cols = [col for col in display_cols if col in removed_df.columns]
        
        if existing_cols:
            st.dataframe(
                removed_df[existing_cols].rename(columns={
                    'game': 'Game Title',
                    'system': 'Platform',
                    'tier': 'PS+ Tier',
                    'metacritic': 'Metacritic Score',
                    'release': 'Release Date'
                }),
                width="stretch",
                hide_index=True
            )
        else:
            st.write(removed_df)
    else:
        st.info("✨ No removed games yet!")