import streamlit as st
import pandas as pd
import os
from pathlib import Path
import re # Import regex module

# Set page configuration
st.set_page_config(layout="wide", page_title="BYU Learning Outcomes - Analysis & Recommendations")

def read_file_content(filepath):
    """Read the content from a given file."""
    try:
        with open(filepath, 'r') as file:
            return file.read()
    except Exception as e:
        st.error(f"Error reading file content from {filepath}: {e}")
        return "" # Return empty string on error

# Page title
st.title("BYU Learning Outcomes - Analysis & Recommendations")

# --- Process and Display Blog Content with Inline Images ---
blog_content = read_file_content('blog_write_up.md')

# Regular expression to find markdown image tags: ![alt text](path/to/image.png)
# It captures the alt text and the image path.
image_pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')

# Split the blog content by the image tags. 
# `re.split` keeps the captured groups (alt text, path) in the resulting list.
parts = image_pattern.split(blog_content)

# The 'parts' list will contain text segments interleaved with alt text and image paths.
# Example: ['text before image 1', 'alt text 1', 'path/to/image1.png', 'text between images', 'alt text 2', 'path/to/image2.png', 'text after image 2']

# Check if visualizations directory exists
vis_dir = Path('visualizations')
visualizations_exist = vis_dir.exists()
if not visualizations_exist:
    st.warning("Visualization directory not found. Images referenced in the blog post may not display. Run generate_blog_visuals.py to create visualizations.")

# Display the first text segment (if any)
if parts and parts[0]:
    st.markdown(parts[0])

# Iterate through the rest of the parts, processing image tags
# We step by 3 because each image match results in three items in the list: preceding text, alt text, image path
for i in range(1, len(parts), 3):
    # Extract alt text and image path
    alt_text = parts[i]
    image_path_md = parts[i+1] # Path as written in markdown (e.g., visualizations/...)
    
    # Construct the full path relative to the script
    image_full_path = Path(image_path_md)

    # Display the image using st.image if the file exists
    if visualizations_exist and image_full_path.exists():
        # Use consistent width for all charts
        display_width = 900 
        st.image(str(image_full_path), caption=alt_text, width=display_width)
    else:
        # If image doesn't exist, show a warning or the alt text
        st.warning(f"Image not found: {image_path_md}")
        # Optionally display the markdown tag itself or just the alt text
        # st.markdown(f"_{alt_text}_") 

    # Display the text segment following the image (if any)
    if i + 2 < len(parts) and parts[i+2]:
        st.markdown(parts[i+2])

# --- Sidebar Content (Remains the same) ---
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
    # Read the original markdown content again for the download button
    report_content = read_file_content("blog_write_up.md")
    if report_content: # Ensure content was read successfully
        st.sidebar.download_button(
            label="Download Markdown Report",
            data=report_content,
            file_name="byu_learning_outcomes_analysis.md",
            mime="text/markdown"
        )
    else:
        st.sidebar.warning("Could not load report content for download.")
except Exception as e:
    st.sidebar.error(f"Could not prepare report for download: {e}") 