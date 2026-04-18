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

# Create five visual tabs for the UI
tab1, tab2, tab3, tab4, tab5 = st.tabs(["💬 AI Gaming Assistant", "📋 Full Backlog View", "📊 Progress Tracker", "🗑️ Removed Games", "📈 My Stats"])

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
        # Initialize session state for processing status
        if "agent_processing" not in st.session_state:
            st.session_state.agent_processing = False
        if "agent_response" not in st.session_state:
            st.session_state.agent_response = None
        if "last_query" not in st.session_state:
            st.session_state.last_query = ""
        
        # Show current processing status
        if st.session_state.agent_processing:
            st.info("⏳ Agent is processing your request... Please wait.")
        
        # Input section - disabled during processing
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
                # Add a small visual spacer so the button aligns better with the input field
                st.markdown("<div style='margin-top: 18px'></div>", unsafe_allow_html=True)
                submit_disabled = st.session_state.agent_processing or not user_query.strip()
                if st.button(
                    "🤖 Ask" if not st.session_state.agent_processing else "⏳ Processing...",
                    disabled=submit_disabled,
                    use_container_width=True,
                    type="primary"
                ):
                    if user_query.strip():
                        st.session_state.agent_processing = True
                        st.session_state.last_query = user_query.strip()
                        st.session_state.agent_response = None
                        
                        try:
                            with st.spinner("🤖 Agent is analyzing your database..."):
                                answer = ask_gaming_agent(user_query.strip())
                            
                            st.session_state.agent_response = answer
                            st.session_state.agent_processing = False
                            
                            # Clear the input by updating session state
                            st.session_state.agent_input = ""
                            st.rerun()
                            
                        except Exception as e:
                            st.session_state.agent_processing = False
                            st.error(f"❌ Error communicating with agent: {e}")
        
        # Display the response
        if st.session_state.agent_response:
            st.success(f"**Question:** {st.session_state.last_query}")
            with st.container():
                st.markdown("**🤖 Agent Response:**")
                st.write(st.session_state.agent_response)
            
    else:
        st.error("🤖 AI Agent is not configured. Please set up your GOOGLE_API_KEY in a .env file.")

# --- TAB 2: The Database ---
with tab2:
    st.subheader("Your PlayStation Library")
    
    col1, col2 = st.columns([0.9, 0.1])
    with col2:
        if st.button("🔄 Sync Covers"):
            with st.spinner("Syncing covers from IGDB..."):
                import subprocess
                try:
                    subprocess.run(["python", "sync_covers.py"], check=True, cwd="c:\\ps_tracker")
                    st.success("✅ Covers synced!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Sync failed: {e}")
    
    try:
        with st.spinner("Loading all games..."):
            response = requests.get("http://127.0.0.1:8000/games/active")
        
        if response.status_code == 200:
            games_data = response.json()
            
            if not games_data:
                st.info("No active games found in the backlog.")
            else:
                df = pd.DataFrame(games_data)
                if 'my_hours' not in df.columns:
                    df['my_hours'] = 0.0
                else:
                    df['my_hours'] = pd.to_numeric(df['my_hours'], errors='coerce').fillna(0.0)

                if 'game' not in df.columns:
                    df['game'] = df.index.astype(str)

                platform_col = 'platform' if 'platform' in df.columns else 'system' if 'system' in df.columns else None
                platform_options = ['All']
                if platform_col:
                    platform_options += sorted(df[platform_col].dropna().astype(str).unique().tolist())

                total_games = len(df)
                total_hours = df['my_hours'].sum()
                avg_hours = df['my_hours'].mean() if total_games else 0.0
                most_played_platform = 'N/A'
                if platform_col and not df[platform_col].dropna().empty:
                    most_played_platform = df[platform_col].mode().iloc[0]
                leaving_soon_count = int((df['status'] == 'Leaving Soon').sum()) if 'status' in df.columns else 0

                st.markdown("### Quick Stats")
                stat1, stat2, stat3, stat4 = st.columns(4)
                stat1.metric("Total Hours Played", round(total_hours, 1))
                stat2.metric("Average Playtime", round(avg_hours, 1))
                stat3.metric("Most Played Platform", most_played_platform)
                stat4.metric("Games Completed", 0)

                extra1, extra2 = st.columns(2)
                extra1.metric("Games Available Now", total_games)
                extra2.metric("Games Leaving Soon", leaving_soon_count)

                st.markdown("### Search & Filters")
                filter_col1, filter_col2, filter_col3 = st.columns(3)
                search_title = filter_col1.text_input("Search by title")
                selected_platform = filter_col2.selectbox("Platform", platform_options)
                min_hours = filter_col3.slider(
                    "Min playtime (hours)",
                    0,
                    int(max(df['my_hours'].max(), 0)),
                    0,
                )

                filtered_df = df.copy()
                if search_title:
                    filtered_df = filtered_df[filtered_df['game'].astype(str).str.contains(search_title, case=False, na=False)]
                if selected_platform and selected_platform != 'All' and platform_col:
                    filtered_df = filtered_df[filtered_df[platform_col].astype(str) == selected_platform]
                filtered_df = filtered_df[filtered_df['my_hours'] >= min_hours]

                st.markdown(f"**Showing {len(filtered_df)} of {total_games} games**")

                if filtered_df.empty:
                    st.info("No games match your filters. Try widening your search or lowering the minimum playtime.")
                else:
                    cols = st.columns(4)
                    for index, row in filtered_df.iterrows():
                        game_title = row.get("game", "Unknown Game")
                        tier = row.get("tier", "Unknown")
                        metacritic = row.get("metacritic", "N/A")
                        cover_url = row.get("cover_image_url")
                        hltb = row.get("completion", "Unknown")
                        my_hours = row.get("my_hours", 0.0)

                        if not cover_url:
                            cover_url = get_game_cover(game_title)

                        with cols[index % 4]:
                            st.image(cover_url, width='stretch')
                            st.markdown(f"**{game_title}**")
                            st.caption(f"⭐ Metacritic: {metacritic} | 🎮 {tier}")
                            st.caption(f"⏱️ Time to Beat: {hltb} hrs")
                            if my_hours > 0:
                                st.caption(f"🔥 My Playtime: {my_hours} hrs")
                            st.divider()
        else:
            st.error("Failed to load games from API.")
            
    except Exception as e:
        st.error(f"⚠️ Error: {e}")
# --- TAB 3: The Progress Tracker ---
with tab3:
    st.subheader("Manage Your Backlog Status")
    st.markdown("Change the status below and click save to update your database.")
    
    try:
        # Fetch fresh data - all active/leaving soon games
        with st.spinner("Loading games for tracking..."):
            response = requests.get("http://127.0.0.1:8000/games/active")
        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            
            # Ensure the column exists in our dataframe view
            if 'personal_status' not in df.columns:
                df['personal_status'] = 'Backlog'
                
            # Filter down to just the columns we care about tracking
            display_cols = ['game', 'system', 'tier', 'personal_status']
            df_display = df[display_cols]
            
            # The Magic Streamlit Data Editor
            edited_df = st.data_editor(
                df_display,
                column_config={
                    "personal_status": st.column_config.SelectboxColumn(
                        "My Progress",
                        help="Update your game status",
                        width="medium",
                        options=[
                            "📥 Backlog",
                            "🔥 Playing",
                            "⏸️ On Hold",
                            "✅ Story Complete",
                            "🏆 Platinumed",
                            "♾️ Ongoing",
                            "🛑 Dropped",
                            "🚫 Not Interested"
                        ],
                    ),
                    "game": st.column_config.TextColumn("Game Title", disabled=True),
                    "system": st.column_config.TextColumn("System", disabled=True),
                    "tier": st.column_config.TextColumn("Tier", disabled=True)
                },
                hide_index=True,
                use_container_width=True
            )
            
            # The Save Mechanism
            if st.button("💾 Save Progress", type="primary"):
                changes_made = 0
                
                # Loop through the table to find what the user changed
                for index, row in edited_df.iterrows():
                    original_status = df_display.iloc[index]['personal_status']
                    new_status = row['personal_status']
                    
                    if original_status != new_status:
                        # Send the update to our new FastAPI endpoint
                        requests.put(
                            f"http://127.0.0.1:8000/games/{row['game']}/status", 
                            json={"status": new_status}
                        )
                        changes_made += 1
                
                if changes_made > 0:
                    st.success(f"Successfully updated {changes_made} games!")
                    st.rerun() # Refreshes the page to show new data
                else:
                    st.info("No changes detected.")
    except Exception as e:
        st.error(f"Error loading tracker: {e}")

# --- TAB 4: Removed Games Reference ---
with tab4:
    st.subheader("🗑️ Removed from PlayStation Plus")
    st.markdown("Games that are no longer available on the platform (from your Excel/Google Sheet).")
    
    try:
        with st.spinner("Loading removed games..."):
            response = requests.get("http://127.0.0.1:8000/games/removed")
        
        if response.status_code == 200:
            removed_games = response.json()
            
            if not removed_games:
                st.info("✨ No removed games yet!")
            else:
                # Create a 4-column grid
                cols = st.columns(4)
                
                for index, game in enumerate(removed_games):
                    game_title = game.get("game", "Unknown Game")
                    tier = game.get("tier", "Unknown")
                    metacritic = game.get("metacritic", "N/A")
                    cover_url = game.get("cover_image_url")
                    
                    # Use placeholder if no cover
                    if not cover_url:
                        safe_name = urllib.parse.quote_plus(game_title)
                        cover_url = f"https://placehold.co/264x374/222222/FFFFFF/png?text={safe_name}"
                    
                    with cols[index % 4]:
                        st.image(cover_url, width='stretch')
                        st.markdown(f"**{game_title}**")
                        st.caption(f"⭐ {metacritic} | {tier}")
                        st.divider()
        else:
            st.error("Failed to load removed games.")
            
    except Exception as e:
        st.error(f"⚠️ Error: {e}")

# --- TAB 5: My Playtime Stats ---
with tab5:
    st.subheader("📈 My Playtime Stats")
    st.markdown("See your full PSN playtime data from scraped games.")

    try:
        with st.spinner("Loading your PSN playtime stats..."):
            response = requests.get("http://127.0.0.1:8000/psn/games")

        if response.status_code == 200:
            df = pd.DataFrame(response.json())

            if df.empty:
                st.warning("No PSN playtime data found yet. Run the PSN sync script to populate your playtime.")
            else:
                df['play_duration_hours'] = pd.to_numeric(df['play_duration_hours'], errors='coerce').fillna(0.0)
                played = df[df['play_duration_hours'] > 0].copy()

                if played.empty:
                    st.info("No games with playtime found in PSN data.")
                else:
                    total_hours = played['play_duration_hours'].sum()
                    games_count = len(played)
                    avg_hours = played['play_duration_hours'].mean()

                    stats_col1, stats_col2, stats_col3 = st.columns(3)
                    stats_col1.metric("Games played", games_count)
                    stats_col2.metric("Total hours", round(total_hours, 1))
                    stats_col3.metric("Average hours", round(avg_hours, 1))

                    st.subheader("All played games")
                    all_played = played.sort_values('play_duration_hours', ascending=False)
                    st.dataframe(
                        all_played[['name', 'category', 'play_count', 'play_duration_hours']].rename(columns={'name': 'Game', 'play_duration_hours': 'Hours', 'play_count': 'Play Count'}),
                        use_container_width=True
                    )
        else:
            st.error("Failed to load your PSN playtime stats.")

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
