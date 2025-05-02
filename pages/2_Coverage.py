import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- Configuration ---
# Point to the same data file used by the main dashboard
DATA_FILE = "data/classified_learning_outcomes_cleaned.csv" # Use the cleaned file
DUMMY_DATA_FILE = "data/dummy_classified_data.csv" # Fallback
BYU_AIMS = [ # Keep aims definition consistent if needed, though not directly used here
    "Spiritually Strengthening",
    "Intellectually Enlarging",
    "Character Building",
    "Lifelong Learning and Service"
]

# --- Helper Functions ---
# Copied and adapted from dashboard.py for self-containment
@st.cache_data # Cache the data loading
def load_data(filepath):
    """Loads the classified data CSV, potentially harmonizes names, and returns df.
       NOTE: This version is simplified and doesn't return removal counts,
             as the focus here is on the content of the final file."""
    if not os.path.exists(filepath):
        st.error(f"Data file not found: {filepath}. Please ensure the classification and cleaning scripts have run successfully.")
        return None
    try:
        df = pd.read_csv(filepath)
        original_row_count = len(df)
        print(f"Read {original_row_count} rows from {filepath}")

        # --- Harmonize College Names (optional but good practice) ---
        if 'college' in df.columns:
            college_mapping = {
                "College of Computational, Mathematical, & Physical Sciences": "College of Physical and Mathematical Sciences",
                "College of Computational, Mathematical & Physical Sciences": "College of Physical and Mathematical Sciences",
                "Kennedy Center for International Studies": "David M. Kennedy Center for International Studies",
                "International and Area Studies": "David M. Kennedy Center for International Studies"
            }
            df['college'] = df['college'].replace(college_mapping)
        else:
             print("Warning: 'college' column not found.")

        # --- Basic Filtering (Ensure essential columns exist) ---
        # Unlike the main dashboard, we DON'T filter out placeholders or zero scores here
        # as we want to analyze the full content of the final classified file.
        # However, we need core columns for analysis.
        required_cols = ['course_url', 'learning_outcome_title', 'learning_outcome_details']
        if not all(col in df.columns for col in required_cols):
            st.error(f"Data file {filepath} is missing required columns for coverage analysis (e.g., course_url, outcome title/details).")
            # Keep potentially incomplete df for partial analysis if possible
            # return None

        # Ensure outcome columns are strings for length calculation
        df['learning_outcome_title'] = df['learning_outcome_title'].astype(str)
        df['learning_outcome_details'] = df['learning_outcome_details'].astype(str)


        # --- Add Combined Outcome Text and Length ---
        # Handle potential NaN implicitly converted to 'nan' string by astype(str)
        df['full_outcome_text'] = df['learning_outcome_title'].replace('nan', '', regex=False) + " " + df['learning_outcome_details'].replace('nan', '', regex=False)
        df['full_outcome_text'] = df['full_outcome_text'].str.strip() # Remove leading/trailing spaces
        df['outcome_length'] = df['full_outcome_text'].str.len()

        return df
    except Exception as e:
        st.error(f"Error loading or processing data from {filepath}: {e}")
        return None

# --- Page Setup ---
st.set_page_config(layout="wide", page_title="Data Coverage")
st.title("Data Coverage Analysis")
st.markdown(f"""
This page analyzes the content of the final dataset (`{os.path.basename(DATA_FILE)}`)
to understand the scope of the scraped and classified learning outcomes.
""")

# --- Load Data ---
# Prioritize final, then dummy
if os.path.exists(DATA_FILE):
    data_path = DATA_FILE
else:
    st.info(f"Real data file not found ({DATA_FILE}). Displaying dummy data ({DUMMY_DATA_FILE}) for demonstration.")
    data_path = DUMMY_DATA_FILE

df = load_data(data_path)

# --- Calculations and Display ---
if df is not None and not df.empty:
    total_outcomes = len(df)
    # Use course_url as the unique identifier for courses
    if 'course_url' in df.columns:
        total_courses = df['course_url'].nunique()
        st.header("Overall Statistics")
        col1, col2 = st.columns(2)
        col1.metric("Total Learning Outcomes Found", f"{total_outcomes:,}")
        col2.metric("Unique Courses Represented (with outcomes)", f"{total_courses:,}")

        st.markdown("""**Note:** 'Unique Courses Represented' counts courses that have at least one learning outcome row present in the final dataset. It does not necessarily represent the total number of courses listed in the BYU catalog initially scraped, as courses without any listed outcomes might not be present in this final file.""")

        st.header("Distribution of Outcomes per Course")
        # Calculate outcomes per course
        outcomes_per_course = df.groupby('course_url').size().reset_index(name='outcome_count')

        # Create histogram
        fig_hist = px.histogram(
            outcomes_per_course,
            x='outcome_count',
            nbins=max(30, outcomes_per_course['outcome_count'].nunique()), # Adjust bins dynamically
            title="Histogram of Learning Outcomes per Course",
            labels={'outcome_count': 'Number of Learning Outcomes per Course URL', 'count': 'Number of Courses'}
        )
        fig_hist.update_layout(bargap=0.1)
        st.plotly_chart(fig_hist, use_container_width=True)
        st.dataframe(outcomes_per_course.describe())


        # --- Length Analysis ---
        st.header("Analysis of Outcome Length")
        st.markdown("""
        Some learning outcomes listed on the source website appear to be concatenated or contain extensive descriptive text rather than distinct, enumerated outcomes. Analyzing the length of the combined outcome title and details can help identify these cases. Outcomes with unusually long text might represent multiple conceptual points merged into one entry in the source data.
        """)

        if 'outcome_length' in df.columns:
            # Calculate 98th percentile threshold
            length_threshold = df['outcome_length'].quantile(0.98)

            st.metric("98th Percentile Outcome Length", f"{length_threshold:,.0f} characters")

            # Filter for long outcomes
            long_outcomes_df = df[df['outcome_length'] >= length_threshold].sort_values(by='outcome_length', ascending=False)

            st.subheader(f"Learning Outcomes Longer Than {length_threshold:,.0f} Characters (Top 2%)")
            st.markdown(f"Found {len(long_outcomes_df)} outcomes potentially representing combined points.")

            # Select columns to display
            display_cols_long = {
                'course_name': 'Course Code',
                'course_url': 'Course URL',
                'outcome_length': 'Text Length',
                'full_outcome_text': 'Full Outcome Text (Title + Details)',
            }
            cols_to_select_long = [col for col in display_cols_long.keys() if col in long_outcomes_df.columns]

            if not long_outcomes_df.empty:
                st.dataframe(
                    long_outcomes_df[cols_to_select_long].rename(columns=display_cols_long),
                    column_config={
                        "Course URL": st.column_config.LinkColumn("Course URL", display_text="Open Catalog"),
                        "Full Outcome Text": st.column_config.TextColumn("Full Outcome Text", width="large")
                    },
                    height=400, # Set a fixed height for the table
                    use_container_width=True
                )
            else:
                st.write("No outcomes met the 98th percentile length threshold.")
        else:
            st.warning("Could not perform length analysis because 'outcome_length' column was not generated.")

    else:
        st.error("Required column 'course_url' not found in the data. Cannot perform coverage analysis.")

elif df is not None and df.empty:
    st.warning("The loaded data file is empty. Cannot perform analysis.")
else:
    # Error messages handled by load_data or initial check
    st.error("Failed to load data. Cannot display coverage analysis.")

# --- Update TODO ---
# (Manual step for now - mark items done in TODO.md)
# Consider adding a step to automatically update TODO later if needed. 