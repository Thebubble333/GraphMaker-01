import streamlit as st
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(__file__))

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
    st.subheader("Functions & Geometry")
    st.info("Plot functions, shapes, and number lines.")

    st.page_link("pages/1_Function_Grapher.py", label="Function Grapher", icon="📈", use_container_width=True)
    st.page_link("pages/10_Inequality_Grapher.py", label="Inequality Grapher", icon="🖍️", use_container_width=True)
    st.page_link("pages/5_Number_Line.py", label="Number Line Plotter", icon="➖", use_container_width=True)
    # --- NEW LINK ADDED HERE ---

    st.markdown("* $y = f(x)$ plots\n* Inequalities & Intervals\n* Geometry & Composites\n* Visual Domains")

with col2:
    st.subheader("Statistics")
    st.info("Visualise data sets for General Maths.")

    st.page_link("pages/2_Box_Plots.py", label="Box Plots", icon="📦", use_container_width=True)
    st.page_link("pages/3_Histograms.py", label="Histograms", icon="📊", use_container_width=True)
    st.page_link("pages/4_Scatter_Plots.py", label="Scatter Plots", icon="📉", use_container_width=True)
    st.page_link("pages/6_Visual_Quartiles.py", label="Visual Quartiles", icon="🔴", use_container_width=True)
    st.page_link("pages/7_Stem_and_Leaf.py", label="Stem & Leaf Plots", icon="🌿", use_container_width=True)

st.markdown("---")
st.caption("GraphMaker v2.6")