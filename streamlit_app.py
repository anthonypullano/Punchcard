"""Streamlit entry point for the generated PUNCHCARD game."""

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from build_punchcard import build_html


st.set_page_config(
    page_title="PUNCHCARD",
    page_icon="🎟️",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def load_game_html() -> str:
    """Load or generate the standalone game HTML for the Streamlit iframe."""
    html_path = Path(__file__).resolve().with_name("index.html")

    if not html_path.is_file():
        build_html(html_path, skip_image_fetch=True)

    return html_path.read_text(encoding="utf-8")


st.markdown(
    """
    <style>
        [data-testid="stHeader"] { display: none; }
        [data-testid="stMain"] > div { padding-top: 0; }
        iframe { border: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    game_html = load_game_html()
except (OSError, UnicodeDecodeError) as exc:
    st.error("PUNCHCARD could not be loaded.")
    st.exception(exc)
else:
    components.html(game_html, height=1400, scrolling=True)
