import streamlit as st
import pandas as pd
import os
from pathlib import Path

# Set page configuration
st.set_page_config(layout="wide", page_title="BYU Learning Outcomes - Analysis & Recommendations")

def read_blog_content():
    """Read the blog content from blog_write_up.md"""
    try:
        with open('blog_write_up.md', 'r') as file:
            return file.read()
    except Exception as e:
        return f"Error reading blog content: {e}"

# Page title
st.title("BYU Learning Outcomes - Analysis & Recommendations")

# Check if images exist
vis_dir = Path('visualizations')
if vis_dir.exists():
    # Display blog images in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if (vis_dir / 'aim_distribution_donut.png').exists():
            st.image("visualizations/aim_distribution_donut.png", 
                    caption="Distribution of BYU Course Learning Objectives")
        else:
            st.warning("Donut chart visualization not found.")
    
    with col2:
        if (vis_dir / 'college_ranking_bar.png').exists():
            st.image("visualizations/college_ranking_bar.png", 
                    caption="BYU Colleges Ranked by Focus on Intellectual Enlargement")
        else:
            st.warning("College ranking visualization not found.")
    
    with col3:
        if (vis_dir / 'balanced_departments.png').exists():
            st.image("visualizations/balanced_departments.png", 
                    caption="BYU Departments with Most Balanced Coverage of All Aims")
        else:
            st.warning("Balanced departments visualization not found.")

    # Divider after images
    st.divider()
else:
    st.warning("Visualization directory not found. Run generate_blog_visuals.py to create visualizations.")

# Display blog content
blog_content = read_blog_content()
st.markdown(blog_content)

# Add attribution
st.sidebar.markdown("### About This Analysis")
st.sidebar.markdown("""
This analysis was created by the BYU Office of Analytics & Information.

The data was gathered from the BYU course catalog and classified using machine learning.
""")

# Add navigation hint
st.sidebar.markdown("### Navigation")
st.sidebar.markdown("""
Use the sidebar menu to navigate to the Dashboard for interactive data exploration.
""")

# Add download button for the full report
st.sidebar.markdown("### Download Report")
try:
    with open("blog_write_up.md", "r") as file:
        content = file.read()
        st.sidebar.download_button(
            label="Download Markdown Report",
            data=content,
            file_name="byu_learning_outcomes_analysis.md",
            mime="text/markdown"
        )
except Exception as e:
    st.sidebar.warning(f"Could not prepare report for download: {e}") 