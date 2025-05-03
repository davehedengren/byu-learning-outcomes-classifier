import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- Configuration ---
# Point to the same data file used by the main dashboard
DATA_FILE = "data/classified_learning_outcomes_cleaned.csv" # Use the cleaned file
URL_LIST_FILE = "data/course_urls.txt" # File containing one URL per line
DUMMY_DATA_FILE = "data/dummy_classified_data.csv" # Fallback
BYU_AIMS = [ # Keep aims definition consistent if needed, though not directly used here
    "Spiritually Strengthening",
    "Intellectually Enlarging",
    "Character Building",
    "Lifelong Learning and Service"
]

# --- Helper Functions ---
@st.cache_data
def count_urls_in_file(filepath):
    """Counts the number of lines (URLs) in a text file."""
    try:
        with open(filepath, 'r') as f:
            return sum(1 for line in f if line.strip()) # Count non-empty lines
    except FileNotFoundError:
        st.warning(f"URL list file not found: {filepath}. Cannot display total targeted courses.")
        return None
    except Exception as e:
        st.error(f"Error reading URL list file {filepath}: {e}")
        return None

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
st.set_page_config(layout="wide", page_title="Data Coverage Report")
st.title("Learning Outcome Data Coverage Report")
st.markdown(f"""
This report summarizes the scope of learning outcomes extracted from the BYU Course Catalog and available in the final dataset (`{os.path.basename(DATA_FILE)}`).
""")

# --- Load Data & Initial Counts ---
initial_url_count = count_urls_in_file(URL_LIST_FILE)

# Prioritize final, then dummy
if os.path.exists(DATA_FILE):
    data_path = DATA_FILE
else:
    # Don't show dummy data if the real file isn't there for a coverage report
    st.error(f"Required data file not found: {DATA_FILE}. Cannot generate coverage report.")
    st.stop()
    # Fallback removed: st.info(...) data_path = DUMMY_DATA_FILE

df = load_data(data_path)

# --- Calculations and Display ---
if df is not None and not df.empty:
    total_outcomes = len(df)
    # Use course_url as the unique identifier for courses
    if 'course_url' in df.columns:
        total_courses_with_outcomes = df['course_url'].nunique()

        st.header("Coverage Summary")
        col1, col2, col3 = st.columns(3)

        if initial_url_count is not None:
            col1.metric("Catalog Course Pages Targeted", f"{initial_url_count:,}")
            help_text_targeted = f"Based on the number of URLs found in `{URL_LIST_FILE}`."
        else:
            col1.metric("Catalog Course Pages Targeted", "N/A")
            help_text_targeted = f"Could not read `{URL_LIST_FILE}`."
        col1.caption(help_text_targeted)

        col2.metric("Courses with ≥1 Outcome Found", f"{total_courses_with_outcomes:,}")
        if initial_url_count is not None:
            coverage_percent = (total_courses_with_outcomes / initial_url_count) * 100 if initial_url_count > 0 else 0
            help_text_found = f"Represents {coverage_percent:.1f}% of targeted courses. Courses without listed outcomes on the catalog page may not be included here."
        else:
            help_text_found = "Percentage of targeted courses cannot be calculated."
        col2.caption(help_text_found)

        col3.metric("Total Learning Outcomes Recorded", f"{total_outcomes:,}")
        avg_outcomes = total_outcomes / total_courses_with_outcomes if total_courses_with_outcomes > 0 else 0
        col3.caption(f"An average of {avg_outcomes:.1f} outcomes per course (for courses with outcomes). Individual counts vary significantly.")

        st.divider()

        st.header("Distribution of Outcomes per Course")
        # Calculate outcomes per course
        outcomes_per_course = df.groupby('course_url').size().reset_index(name='outcome_count')

        # Create histogram
        fig_hist = px.histogram(
            outcomes_per_course,
            x='outcome_count',
            nbins=max(30, outcomes_per_course['outcome_count'].nunique()), # Adjust bins dynamically
            title="Histogram of Learning Outcomes per Course",
            labels={'outcome_count': 'Number of Learning Outcomes Recorded per Course', 'count': 'Number of Courses'}
        )
        fig_hist.update_layout(bargap=0.1)
        st.plotly_chart(fig_hist, use_container_width=True)
        st.dataframe(outcomes_per_course.describe(), use_container_width=True)

        # --- Add Detailed Course Outcome Count Table ---
        st.subheader("Course Outcome Counts (Detailed)")
        # Check for necessary columns
        course_detail_cols = ['course_url', 'course_name', 'course_title']
        if all(col in df.columns for col in course_detail_cols):
            # Group by course details and count outcomes
            course_counts_detailed = df.groupby(course_detail_cols).size().reset_index(name='outcome_count')

            # Sort by outcome count descending
            course_counts_sorted = course_counts_detailed.sort_values(by='outcome_count', ascending=False)

            # Select and rename columns for display
            display_cols_counts = {
                'course_name': 'Course Code',
                'course_title': 'Course Title',
                'course_url': 'Course URL',
                'outcome_count': 'Number of Outcomes'
            }
            # Ensure all expected columns are present before renaming/selecting
            cols_to_display = [col for col in display_cols_counts.keys() if col in course_counts_sorted.columns]

            st.dataframe(
                course_counts_sorted[cols_to_display].rename(columns=display_cols_counts),
                column_config={
                    "Course URL": st.column_config.LinkColumn("Course URL", display_text="Open Catalog")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("Could not display detailed course counts because 'course_name' or 'course_title' columns are missing.")

        st.divider()

        # --- Length Analysis ---
        st.header("Analysis of Outcome Text Length")
        st.markdown("""
        Some learning outcomes listed on the source website appear to be concatenated or contain extensive descriptive text rather than distinct, enumerated outcomes. Analyzing the length of the combined outcome title and details can help identify these cases. Outcomes with unusually long text might represent multiple conceptual points merged into one entry in the source data.
        """)

        if 'outcome_length' in df.columns:
            # Calculate 99.5th percentile threshold
            length_threshold = df['outcome_length'].quantile(0.995)

            st.metric("99.5th Percentile Outcome Length", f"{length_threshold:,.0f} characters")

            # Filter for long outcomes
            long_outcomes_df = df[df['outcome_length'] >= length_threshold].sort_values(by='outcome_length', ascending=False)

            st.subheader(f"Learning Outcomes Longer Than {length_threshold:,.0f} Characters (Top 0.5%)")
            st.markdown(f"Found **{len(long_outcomes_df)}** outcomes potentially representing combined points based on text length exceeding the 99.5th percentile.")

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
                st.write("No outcomes met the 99.5th percentile length threshold.")
        else:
            st.warning("Could not perform length analysis because 'outcome_length' column was not generated.")

    else:
        st.error("Required column 'course_url' not found in the data. Cannot perform coverage analysis.")

elif df is not None and df.empty:
    st.warning("The loaded data file is empty. Cannot perform analysis.")
else:
    # Error messages handled by load_data or initial check
    st.error("Failed to load data. Cannot display coverage report.")

# --- Update TODO ---
# (Manual step for now - mark items done in TODO.md)
# Consider adding a step to automatically update TODO later if needed. 