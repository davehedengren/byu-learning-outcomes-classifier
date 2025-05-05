import streamlit as st
import pandas as pd
import os
import random

# Configuration
SUGGESTIONS_FILE = "data/sample_20250503_143216_gpt4.5_suggested_outcomes.csv"
BYU_AIMS = [
    "Spiritually Strengthening",
    "Intellectually Enlarging",
    "Character Building",
    "Lifelong Learning and Service"
]

# Non-intellectual aims we want to show suggestions for
TARGET_AIMS = [aim for aim in BYU_AIMS if aim != "Intellectually Enlarging"]

# --- Helper Functions ---
@st.cache_data # Cache the data loading to improve performance
def load_suggestions_data(filepath):
    """Load the suggestions data from CSV."""
    if not os.path.exists(filepath):
        st.error(f"Suggestions file not found: {filepath}")
        return None
        
    try:
        df = pd.read_csv(filepath)
        print(f"Loaded {len(df)} courses with suggestions.")
        return df
    except Exception as e:
        st.error(f"Error loading suggestions data: {e}")
        return None

# --- Main App Layout ---
st.set_page_config(layout="wide", page_title="BYU Learning Outcomes - Suggestions")
st.title("Alternative Learning Outcome Suggestions")

# Initialize session state for storing selected suggestions if not already initialized
if 'selected_suggestions' not in st.session_state:
    st.session_state.selected_suggestions = []

# Initialize state for the selected course
if 'selected_course_value' not in st.session_state:
    st.session_state.selected_course_value = "All"

st.markdown("""
This tool provides alternative learning outcome suggestions for courses that align with BYU's four aims of education.
For each course, we provide three alternative learning outcomes focused on:

- **Spiritually Strengthening**
- **Character Building**
- **Lifelong Learning and Service**

These suggestions are generated using advanced AI models (GPT-4.5) trained on BYU's educational mission and aims.
""")

st.markdown("---")

# Load the suggestions data
suggestions_df = load_suggestions_data(SUGGESTIONS_FILE)

if suggestions_df is not None:
    # --- Sidebar Filters ---
    st.sidebar.header("Filters")
    
    # College Filter
    colleges = sorted(suggestions_df['college'].dropna().unique())
    selected_college = st.sidebar.selectbox("Select College", ["All"] + colleges)
    
    # Filter data based on college selection
    if selected_college == "All":
        filtered_df = suggestions_df
    else:
        filtered_df = suggestions_df[suggestions_df['college'] == selected_college]
    
    # Department Filter (depends on selected college)
    departments = sorted(filtered_df['department'].dropna().unique())
    selected_department = st.sidebar.selectbox("Select Department", ["All"] + departments)
    
    # Filter data further based on department selection
    if selected_department != "All":
        filtered_df = filtered_df[filtered_df['department'] == selected_department]
    
    # Course Filter (depends on selected department)
    courses = []
    if not filtered_df.empty:
        course_data = filtered_df[['course_name', 'course_title']].drop_duplicates()
        # Create a formatted list for the selectbox: "COURSE_NAME - COURSE_TITLE"
        course_options = [f"{row['course_name']} - {row['course_title']}" for _, row in course_data.iterrows()]
        courses = sorted(course_options)
    
    # Calculate the correct default index
    options = ["All"] + courses
    default_index = 0 # Default to "All"
    selected_value = st.session_state.get('selected_course_value', "All") # Safely get value, default to "All"
    if selected_value != "All" and selected_value in options:
        try:
            default_index = options.index(selected_value)
        except ValueError:
            # Should not happen if 'in options' check passed, but good practice
            default_index = 0 
            
    # Update the selected course in the sidebar (and synchronize with any table clicks)
    selected_course = st.sidebar.selectbox(
        "Select Course", 
        options, # Use the defined options list
        index=default_index # Use the calculated default index
    )
    
    # Update session state if changed from sidebar
    if selected_course != st.session_state.selected_course_value:
        st.session_state.selected_course_value = selected_course
    
    # Further filter based on course selection
    if selected_course != "All":
        course_name = selected_course.split(" - ")[0].strip()
        filtered_df = filtered_df[filtered_df['course_name'] == course_name]
    
    st.sidebar.markdown(f"_Found {len(filtered_df.drop_duplicates(['course_name']))} courses with suggestions_")
    
    # --- Main Content Area ---
    if filtered_df.empty:
        st.warning("No suggestions available for the selected filters.")
    else:
        # If a specific course is selected, show its details and suggestions
        if selected_course != "All":
            course_row = filtered_df.iloc[0]  # Get first row since all rows are for the same course
            
            # Show course information in a clean card format
            st.header(f"{course_row['course_name']} - {course_row['course_title']}")
            
            # Create columns for the course info
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Department:** {course_row['department']}")
            with col2:
                st.markdown(f"**College:** {course_row['college']}")
            
            # Show current learning outcomes
            st.subheader("Current Learning Outcomes")
            outcomes_list = course_row['all_existing_outcomes'].split("---")
            for outcome in outcomes_list:
                st.markdown(f"- {outcome.strip()}")
            
            # Divider
            st.markdown("---")
            
            # Show alternative suggestions for each aim
            st.subheader("Alternative Learning Outcome Suggestions")
            
            # Create tabs for each non-intellectual aim
            tabs = st.tabs(TARGET_AIMS)
            
            for i, aim in enumerate(TARGET_AIMS):
                with tabs[i]:
                    # Create a clean card format for each suggestion
                    st.markdown(f"### {aim} Suggestions")
                    
                    # Get the 3 suggestions for this aim
                    aim_key = aim.replace(" ", "_")
                    suggestions = []
                    for j in range(1, 4):
                        col_name = f"suggested_{aim_key}_{j}"
                        if col_name in course_row and pd.notna(course_row[col_name]):
                            suggestions.append(course_row[col_name])
                    
                    # Display each suggestion in a nice card with buttons to collect
                    for idx, suggestion in enumerate(suggestions):
                        # Create a unique key for this suggestion
                        suggestion_key = f"{course_row['course_name']}_{aim}_{idx}"
                        
                        # Create a two-column layout for each suggestion: card and button
                        col1, col2 = st.columns([5, 1])
                        
                        with col1:
                            # Display suggestion card
                            st.markdown(
                                f"""
                                <div style="
                                    background-color: #f9f9f9;
                                    border-radius: 10px;
                                    padding: 15px;
                                    margin-bottom: 15px;
                                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                                ">
                                    <p style="
                                        margin: 0;
                                        font-size: 16px;
                                        font-weight: 400;
                                        color: #333;
                                    ">{suggestion}</p>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                        
                        with col2:
                            # Add a button to collect this suggestion
                            # Check if this suggestion is already collected
                            is_collected = any(item['text'] == suggestion for item in st.session_state.selected_suggestions)
                            button_label = "✓ Added" if is_collected else "Add"
                            button_type = "primary" if is_collected else "secondary"
                            
                            if st.button(button_label, key=suggestion_key, type=button_type, disabled=is_collected):
                                # Add to selected suggestions
                                st.session_state.selected_suggestions.append({
                                    'course': course_row['course_name'],
                                    'aim': aim,
                                    'text': suggestion
                                })
                                # Use rerun to update the UI immediately
                                st.rerun()
        else:
            # If no specific course is selected, show a summary table
            st.header("Available Courses with Suggestions")
            
            # Create a summary dataframe with course info
            summary_df = filtered_df[['course_name', 'course_title', 'department', 'college']].drop_duplicates()
            
            # Add a button column to each row
            summary_df['view'] = summary_df.apply(
                lambda row: f"{row['course_name']} - {row['course_title']}", 
                axis=1
            )
            
            # Construct the clickable table with buttons
            for i, row in summary_df.iterrows():
                col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 1])
                with col1:
                    st.text(row['course_name'])
                with col2:
                    st.text(row['course_title'])
                with col3:
                    st.text(row['department'])
                with col4:
                    st.text(row['college'])
                with col5:
                    if st.button("View", key=f"view_{row['course_name']}"):
                        # Update session state with the selected course
                        st.session_state.selected_course_value = row['view']
                        # Use rerun to update the UI immediately
                        st.rerun()

            st.info("👆 Click 'View' on a course to see its alternative learning outcome suggestions.")
    
    # --- Selected Suggestions Section ---
    if st.session_state.selected_suggestions:
        st.markdown("---")
        st.header("Your Selected Suggestions")
        
        # Create an expander to keep the UI clean
        with st.expander("View and Copy Selected Suggestions", expanded=True):
            # Display all selected suggestions
            for i, item in enumerate(st.session_state.selected_suggestions):
                # Create columns for display and remove button
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    st.markdown(
                        f"""
                        <div style="
                            background-color: #eef8ff;
                            border-radius: 10px;
                            padding: 15px;
                            margin-bottom: 15px;
                            border-left: 5px solid #4a90e2;
                        ">
                            <p style="margin: 0; font-size: 12px; color: #666;">
                                <strong>{item['course']}</strong> - {item['aim']}
                            </p>
                            <p style="
                                margin-top: 5px;
                                font-size: 15px;
                                font-weight: 400;
                                color: #333;
                            ">{item['text']}</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                with col2:
                    # Add a button to remove this suggestion
                    if st.button("Remove", key=f"remove_{i}"):
                        # Remove from selected suggestions
                        st.session_state.selected_suggestions.pop(i)
                        # Use rerun to update the UI immediately
                        st.rerun()
            
            # Concatenate all suggestions for easy copying
            all_text = "\n\n".join([f"{item['course']} - {item['aim']}:\n{item['text']}" for item in st.session_state.selected_suggestions])
            
            # Add a button to copy all text
            st.text_area("Copy all selected suggestions at once:", all_text, height=200)
            
            # Add a button to clear all
            if st.button("Clear All Selections"):
                st.session_state.selected_suggestions = []
                st.rerun()
else:
    st.error(f"Could not load suggestions data. Please ensure the file {SUGGESTIONS_FILE} exists.") 