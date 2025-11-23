import streamlit as st

def render_sidebar():
    """
    Renders a clean sidebar with just a Home button.
    """
    with st.sidebar:
        # Home Button
        st.page_link("Home.py", label="Home", icon="🏠", use_container_width=True)
        st.markdown("---")