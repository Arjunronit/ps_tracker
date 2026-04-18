import urllib.parse

PLACEHOLDER_BASE = "https://placehold.co/264x374/222222/FFFFFF/png?text="


def get_game_cover(game_title: str) -> str:
    """Return a placeholder image URL for the given game title.

    This avoids a missing-module crash and still shows a visual card in Streamlit.
    Replace this implementation with real IGDB or other cover art API logic later.
    """
    if not game_title:
        game_title = "Unknown+Game"
    safe_title = urllib.parse.quote_plus(game_title)
    return f"{PLACEHOLDER_BASE}{safe_title}"
