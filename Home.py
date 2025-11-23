import streamlit as st
from utils.nav import render_sidebar

st.set_page_config(
    page_title="GraphMaker Hub",
    page_icon="📐",
    layout="wide"
)

# Render Custom Sidebar
render_sidebar()

st.title("📐 GraphMaker Suite")
st.markdown(r"""
### Select a tool to begin

This tool is designed to create **high-quality, publication-ready mathematical graphs** for exams, worksheets, and textbooks. 

---
""")

# --- LAYOUT ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Functions")
    st.info("Plot mathematical functions with exact grids.")

    st.page_link("pages/1_Function_Grapher.py", label="Function Grapher", icon="📈", use_container_width=True)
    # Fix: Used double backslash for pi (\\pi) to avoid invalid escape sequence warning
    st.markdown("* $y = f(x)$ plots\n* Intersections & Turning Points\n* Exact Surds & $\\pi$")

with col2:
    st.subheader("Statistics")
    st.info("Visualise data sets for General Maths.")

    st.page_link("pages/2_Box_Plots.py", label="Box Plots", icon="📦", use_container_width=True)
    st.page_link("pages/3_Histograms.py", label="Histograms", icon="📊", use_container_width=True)
    st.page_link("pages/4_Scatter_Plots.py", label="Scatter Plots", icon="📉", use_container_width=True)
    # Removed Residual Plots and Time Series as requested

st.markdown("---")
st.caption("GraphMaker v2.1")