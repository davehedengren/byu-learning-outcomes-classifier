import streamlit as st
import pandas as pd
import plotly.express as px
import os

# Configuration
# Point back to the primary output file, which is now cleaned
DATA_FILE = "data/classified_learning_outcomes_cleaned.csv" # Use the cleaned file from data dir
DUMMY_DATA_FILE = "data/dummy_classified_data.csv" # For development, from data dir
BYU_AIMS = [
    "Spiritually Strengthening",
    "Intellectually Enlarging",
    "Character Building",
    "Lifelong Learning and Service"
]
# Define consistent colors for aims
AIM_COLORS = {
    "Spiritually Strengthening": px.colors.qualitative.Pastel[0], # Light Blue
    "Intellectually Enlarging": px.colors.qualitative.Pastel[1], # Light Orange
    "Character Building": px.colors.qualitative.Pastel[2], # Light Green
    "Lifelong Learning and Service": px.colors.qualitative.Pastel[3] # Light Red
}

# --- Helper Functions ---
@st.cache_data # Cache the data loading to improve performance
def load_data(filepath):
    """Loads the classified data CSV, harmonizes names, filters, and returns df and counts of removed rows."""
    if not os.path.exists(filepath):
        st.error(f"Data file not found: {filepath}. Please ensure the batch classification script has run successfully.")
        # Return None for df and 0 for counts if file not found
        return None, 0, 0 
    try:
        df = pd.read_csv(filepath)
        original_row_count = len(df)
        num_removed_placeholders = 0
        num_removed_zeros = 0

        # --- Harmonize College Names ---
        if 'college' in df.columns:
            # Define mapping for common college name variations
            college_mapping = {
                "College of Computational, Mathematical, & Physical Sciences": "College of Physical and Mathematical Sciences",
                "College of Computational, Mathematical & Physical Sciences": "College of Physical and Mathematical Sciences", # Variation without comma
                "Kennedy Center for International Studies": "David M. Kennedy Center for International Studies",
                "International and Area Studies": "David M. Kennedy Center for International Studies" # Group IAS under Kennedy Center
                # Add any other variations observed here
            }
            df['college'] = df['college'].replace(college_mapping)
            print("Harmonized college names.")
        else:
            # We don't stop execution, but the warning is helpful
            print("Warning: 'college' column not found, cannot harmonize names.") 

        # --- Filter out rows indicating no actual outcome or discontinued course ---
        # Define placeholder texts (case-insensitive check)
        no_outcome_text = "No learning outcomes found"
        discontinued_text = "This course is being discontinued so no learning outcomes will be listed."
        filter_texts = [no_outcome_text, discontinued_text]
        filter_pattern = '|'.join(filter_texts) # Create a regex pattern to match either string

        # Check in both details and title (in case one was empty)
        rows_to_remove = df[
            (df['learning_outcome_details'].astype(str).str.contains(filter_pattern, case=False, na=False, regex=True)) |
            (df['learning_outcome_title'].astype(str).str.contains(filter_pattern, case=False, na=False, regex=True))
        ]
        
        if not rows_to_remove.empty:
            num_removed_placeholders = len(rows_to_remove)
            df = df.drop(rows_to_remove.index)
            # st.info(f"Excluded {num_removed} rows containing placeholder text (e.g., '{no_outcome_text}') from analysis.") # Removed st.info
            print(f"Identified {num_removed_placeholders} rows containing placeholder text for removal.") # Keep console print
        
        # Convert aims columns to numeric FIRST, before zero filtering
        confidence_cols = []
        for aim in BYU_AIMS:
            col_name = f"confidence_{aim.replace(' ', '_')}"
            if col_name in df.columns:
                df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                confidence_cols.append(col_name)
            else:
                 # Log this, but don't use st.warning inside cached func
                 print(f"Warning: Confidence column '{col_name}' not found in data file.") 

        # --- Filter out rows where all confidence scores are zero ---
        if confidence_cols: # Only filter if we found confidence columns
            rows_before_zero_filter = len(df)
            # Fill NA in confidence columns with 0 *before* summing for the check
            df[confidence_cols] = df[confidence_cols].fillna(0)
            # Select rows where the sum of confidence scores is NOT zero
            df = df[df[confidence_cols].sum(axis=1) != 0]
            num_removed_zeros = rows_before_zero_filter - len(df)
            if num_removed_zeros > 0:
                # st.info(f"Excluded {num_removed_zeros} rows with zero confidence scores across all aims.") # Removed st.info
                print(f"Identified {num_removed_zeros} rows with zero confidence scores for removal.") # Keep console print

        # Final check for required columns after filtering
        if df.empty:
            st.error("No valid data remaining after filtering.") # Keep this error message here
            return None, num_removed_placeholders, num_removed_zeros
        required_cols = ['college', 'department', 'best_aim']
        if not all(col in df.columns for col in required_cols):
            st.error(f"Data file {filepath} is missing required columns after filtering.") # Keep this here
            # Return the potentially filtered df even if columns missing, but counts are accurate
            return df, num_removed_placeholders, num_removed_zeros 

        return df, num_removed_placeholders, num_removed_zeros
    except Exception as e:
        st.error(f"Error loading data from {filepath}: {e}")
        # Return None for df and 0 for counts on error
        return None, 0, 0 

# --- Main App Layout ---
st.set_page_config(layout="wide", page_title="Dashboard")
st.title("BYU Learning Outcomes Aims Distribution")

st.markdown("""
Brigham Young University operates under a broader charter than traditional universities. 
In addition to fostering intellectual growth, BYU's mission emphasizes four distinct aims: 
a BYU education should be:
1.  Spiritually strengthening,
2.  Intellectually enlarging,
3.  Character building, leading to
4.  Lifelong learning and service.
([Source: Aims of a BYU Education](https://catalog.byu.edu/about/aims-of-a-byu-education))

However, an analysis of course-level learning objectives across the entire BYU catalog reveals that over 90% focus primarily on intellectual development. 
This suggests a meaningful opportunity to better integrate the university's other aims into the classroom experience. 
As Elder Jeffrey R. Holland taught, "BYU will realize President Kimball's vision only to the degree it embraces its uniqueness, its singularity. . . . We must have the will to be different and to stand alone, if necessary, being a university second to none in its role primarily as an undergraduate teaching institution that is unequivocally true to the gospel of the Lord Jesus Christ." 
([Source: The Second Half of the Second Century of Brigham Young University](https://speeches.byu.edu/talks/jeffrey-r-holland/the-second-half-second-century-brigham-young-university/))
""")
st.divider() # Add a visual separator

# Load data - Prioritize final, then raw batch, then dummy
if os.path.exists(DATA_FILE):
    data_path = DATA_FILE
else:
    st.info(f"Real data files not found. Displaying dummy data ({DUMMY_DATA_FILE}) for demonstration.")
    data_path = DUMMY_DATA_FILE

# Unpack the returned values from load_data
df, num_removed_placeholders, num_removed_zeros = load_data(data_path) 

if df is not None:
    # --- Sidebar Filters ---
    st.sidebar.header("Filters")
    
    # College Filter
    colleges = sorted(df['college'].dropna().unique())
    selected_college = st.sidebar.selectbox("Select College (All)", ["All"] + colleges)
    
    # Filter data based on college selection
    if selected_college == "All":
        filtered_df = df
    else:
        filtered_df = df[df['college'] == selected_college]
    
    # Department Filter (depends on selected college)
    departments = sorted(filtered_df['department'].dropna().unique())
    selected_department = st.sidebar.selectbox("Select Department (All)", ["All"] + departments)
    
    # Filter data further based on department selection
    if selected_department != "All":
        filtered_df = filtered_df[filtered_df['department'] == selected_department]

    st.sidebar.markdown(f"_Displaying data for: **{selected_college}** / **{selected_department}**_ ({len(filtered_df)} outcomes)")

    # --- Main Content Area ---
    st.header(f"Distribution for: {selected_college} / {selected_department}")

    if filtered_df.empty:
        st.warning("No data available for the selected filters.")
    else:
        # --- Create Tabs ---
        tab1, tab2 = st.tabs(["Distribution Analysis", "High Confidence Examples"])

        with tab1:
            # --- Existing Content for Tab 1 ---
            # Plot 1: Overall Distribution for the selection
            st.subheader("Overall Aim Distribution")
            aim_counts = filtered_df['best_aim'].value_counts().reindex(BYU_AIMS, fill_value=0)
            fig_pie = px.pie(values=aim_counts.values, names=aim_counts.index, title="Primary Aim Classification",
                             color=aim_counts.index, # Use index for color mapping
                             color_discrete_map=AIM_COLORS,
                             hole=0.4) # Add hole parameter for donut chart
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Display counts table, sorted by Count descending
            aim_counts_df = aim_counts.reset_index().rename(columns={'index': 'Aim', 'best_aim': 'Count'})
            st.dataframe(aim_counts_df.sort_values(by='Count', ascending=False))
            
            # Plot 2: Distribution by College (if 'All' colleges selected)
            if selected_college == "All":
                st.subheader("Distribution by College")
                # Use the original unfiltered df for college comparison
                # Calculate Percentage distribution
                college_aim_dist = df.groupby('college')['best_aim'].value_counts(normalize=True).unstack(fill_value=0) * 100
                college_aim_dist = college_aim_dist.reindex(columns=BYU_AIMS, fill_value=0)
                
                # Calculate Total counts
                college_counts = df['college'].value_counts().rename('Total Outcomes')
                
                # Join counts and percentages
                college_summary = college_aim_dist.join(college_counts)
                # Ensure 'Total Outcomes' is the first column
                cols_order = ['Total Outcomes'] + [col for col in college_summary.columns if col != 'Total Outcomes']
                college_summary = college_summary[cols_order]

                # Add sorting option, default to Intellectually Enlarging
                sort_options = ["Alphabetical", "Total Outcomes"] + BYU_AIMS
                # Find the index of the default value, handling potential absence
                default_sort_option = "Intellectually Enlarging"
                try:
                    default_index = sort_options.index(default_sort_option)
                except ValueError:
                    default_index = 0 # Fallback to Alphabetical if not found
                
                sort_by_col = st.selectbox(
                    "Sort Colleges by:", 
                    sort_options, 
                    index=default_index, # Set default selection
                    key="college_sort_tab1" 
                )

                if sort_by_col == "Alphabetical":
                     # Default sort is alphabetical by index (college name)
                     college_summary_sorted = college_summary.sort_index()
                elif sort_by_col in college_summary.columns:
                    # Sort the DataFrame by the selected column's value, descending
                    college_summary_sorted = college_summary.sort_values(by=sort_by_col, ascending=False)
                else:
                     # Fallback to alphabetical if somehow column is invalid
                     college_summary_sorted = college_summary.sort_index()

                # Melt the potentially sorted DataFrame for Plotly Express bar chart (use original percentages for melt)
                # Need to sort the original percentage dist based on the summary sort order for the chart
                college_aim_dist_sorted_for_chart = college_aim_dist.loc[college_summary_sorted.index]
                college_aim_dist_melted = college_aim_dist_sorted_for_chart.reset_index().melt(id_vars='college', var_name='BYU Aim', value_name='Percentage (%)')

                fig_college = px.bar(college_aim_dist_melted, # Use melted percentage data
                                     x='college', y='Percentage (%)', color='BYU Aim',
                                     barmode='stack', 
                                     title="Percentage of Aims within Each College",
                                     color_discrete_map=AIM_COLORS,
                                     # Ensure the x-axis order respects the sorting
                                     category_orders={"college": college_summary_sorted.index.tolist()})
                fig_college.update_layout(yaxis_title="Percentage (%)", legend_title="BYU Aim", xaxis_title="College")
                st.plotly_chart(fig_college, use_container_width=True)
                
                # Display the sorted summary table (counts + percentages)
                # Define formatting for percentage columns only
                format_dict = {aim: '{:.1f}%' for aim in BYU_AIMS}
                st.dataframe(college_summary_sorted.style.format(format_dict))

            # Plot 3: Distribution by Department (if a specific college is selected)
            elif selected_college != "All" and selected_department == "All":
                 st.subheader(f"Distribution by Department within {selected_college}")
                 # Use filtered_df here as we only care about the selected college's departments
                 dept_aim_dist = filtered_df.groupby('department')['best_aim'].value_counts(normalize=True).unstack(fill_value=0) * 100
                 dept_aim_dist = dept_aim_dist.reindex(columns=BYU_AIMS, fill_value=0)
                 # Melt the DataFrame
                 dept_aim_dist_melted = dept_aim_dist.reset_index().melt(id_vars='department', var_name='BYU Aim', value_name='Percentage (%)')

                 fig_dept = px.bar(dept_aim_dist_melted, # Use melted data
                                 x='department', y='Percentage (%)', color='BYU Aim',
                                 barmode='stack', # Changed from 'group' to 'stack' for consistency
                                 title=f"Percentage of Aims within Departments of {selected_college}",
                                 color_discrete_map=AIM_COLORS,
                                 # Sort departments alphabetically for the chart
                                 category_orders={"department": sorted(dept_aim_dist.index.tolist())})
                 fig_dept.update_layout(yaxis_title="Percentage (%)", legend_title="BYU Aim", xaxis_title="Department")
                 st.plotly_chart(fig_dept, use_container_width=True)
                 # Add the table for department distribution
                 st.dataframe(dept_aim_dist.sort_index().style.format("{:.1f}%"))
                 
            # --- Add Raw Data Table ---
            st.subheader("Review Classified Data")
            st.markdown("The table below shows the detailed classification data based on the current filters.")
    
            # Add the confidence score for the best aim
            def get_best_aim_confidence(row):
                aim_col = f"confidence_{row['best_aim'].replace(' ', '_')}"
                if aim_col in row.index:
                    return row[aim_col]
                return None # Or pd.NA or 0, depending on desired handling

            # Apply only if the column doesn't already exist (avoid re-calculation)
            if 'best_aim_confidence' not in filtered_df.columns:
                filtered_df['best_aim_confidence'] = filtered_df.apply(get_best_aim_confidence, axis=1)
    
            # Select and rename columns for clarity
            display_cols = {
                'course_name': 'Course Code',
                'course_title': 'Course Title',
                'course_url': 'Course URL',
                'department': 'Department',
                'college': 'College',
                'learning_outcome_title': 'Outcome Title',
                'learning_outcome_details': 'Outcome Details',
                'best_aim': 'Best Aim',
                'best_aim_confidence': 'Best Aim Confidence'
            }
            # Filter the DataFrame to only include the columns we want to display
            # Ensure all display_cols exist in filtered_df before selecting
            cols_to_select = [col for col in display_cols.keys() if col in filtered_df.columns]
            # Create the display_df with selected and renamed columns *before* filtering by aim
            table_display_df_unfiltered = filtered_df[cols_to_select].rename(columns=display_cols)
            
            # --- Add Aim Filter for the Table ---
            # Get available aims from the *currently filtered* data
            available_aims = sorted(table_display_df_unfiltered['Best Aim'].dropna().unique())
            
            if available_aims:
                selected_aims_for_table = st.multiselect(
                    "Filter table by Best Aim:", 
                    options=available_aims,
                    default=available_aims, # Default to all available aims
                    key="aim_filter_table"
                )
                
                # Filter the DataFrame for the table based on multiselect
                if selected_aims_for_table != available_aims: # Check if selection changed from default
                     table_display_df = table_display_df_unfiltered[table_display_df_unfiltered['Best Aim'].isin(selected_aims_for_table)]
                else:
                    # If all are selected (or default), use the unfiltered display df
                    table_display_df = table_display_df_unfiltered
            else:
                st.write("No aims available to filter in the current selection.")
                table_display_df = table_display_df_unfiltered # Show empty table if no aims
            
            # --- Display the Filtered Table ---            
            # Use st.data_editor for sortable columns, configure URL column as link
            st.data_editor(
                table_display_df, # Use the potentially filtered DataFrame
                column_config={
                    "Course URL": st.column_config.LinkColumn(
                        "Course URL", # Column name in the DataFrame being displayed
                        help="Click to open the BYU course catalog page",
                        display_text="Open Catalog Page"
                    )
                },
                use_container_width=True, 
                hide_index=True
            )

        with tab2:
            # --- New Content for Tab 2: High Confidence Examples ---
            st.subheader(f"High Confidence Examples for: {selected_college} / {selected_department}")
            st.markdown("Showing top 5 examples for each BYU Aim based on the highest confidence score, according to the filters.")

            # Use the already filtered_df based on sidebar selections
            examples_df = filtered_df.copy()

            # Calculate best_aim_confidence if not already present
            if 'best_aim_confidence' not in examples_df.columns:
                examples_df['best_aim_confidence'] = examples_df.apply(get_best_aim_confidence, axis=1)

            # Ensure confidence column is numeric and drop rows where it's missing
            examples_df['best_aim_confidence'] = pd.to_numeric(examples_df['best_aim_confidence'], errors='coerce')
            examples_df.dropna(subset=['best_aim_confidence'], inplace=True) # Important for sorting
            examples_df['best_aim_confidence'] = examples_df['best_aim_confidence'].astype(int)

            for aim in BYU_AIMS:
                st.markdown(f"#### Top Examples for: {aim}")
                aim_col_name = f"confidence_{aim.replace(' ', '_')}"
                
                # Check if the specific confidence column exists
                if aim_col_name not in examples_df.columns:
                    st.warning(f"Confidence score column '{aim_col_name}' not found in data. Cannot show examples for {aim}.")
                    continue

                # Filter for the current aim AND ensure the specific confidence score is not null
                aim_examples = examples_df[
                    (examples_df['best_aim'] == aim) & 
                    (examples_df[aim_col_name].notna())
                ].copy() # Use copy to avoid SettingWithCopyWarning

                 # Convert the specific confidence column to numeric *before* sorting
                aim_examples[aim_col_name] = pd.to_numeric(aim_examples[aim_col_name], errors='coerce')
                aim_examples.dropna(subset=[aim_col_name], inplace=True) # Drop if conversion failed
                
                # Sort by the specific aim's confidence score
                top_examples = aim_examples.sort_values(by=aim_col_name, ascending=False).head(5)

                if top_examples.empty:
                    st.write("_No examples found for the current filters._")
                else:
                    # Select and display relevant columns
                    display_cols_examples = {
                        'course_name': 'Course Code',
                        'learning_outcome_title': 'Outcome Title',
                        'learning_outcome_details': 'Outcome Details',
                         aim_col_name: f'{aim} Confidence' # Show the specific confidence
                    }
                    cols_to_display_examples = [col for col in display_cols_examples.keys() if col in top_examples.columns]
                    st.dataframe(top_examples[cols_to_display_examples].rename(columns=display_cols_examples), hide_index=True)

        # --- Display Status Messages at the Bottom ---
        if num_removed_placeholders > 0:
            st.info(f"Excluded {num_removed_placeholders} rows containing placeholder text (e.g., 'No learning outcomes found') from analysis.")
        if num_removed_zeros > 0:
            st.info(f"Excluded {num_removed_zeros} rows with zero confidence scores across all aims.")
        # Display success message 
        st.success(f"Loaded {len(df)} classified learning outcomes from {os.path.basename(data_path)}.")

else:
    st.warning("Could not load data. Cannot display dashboard.")
    # Also display any messages about removed rows even if final df is None or empty, if counts > 0
    if num_removed_placeholders > 0:
        st.info(f"Excluded {num_removed_placeholders} rows containing placeholder text before determining no data remained.")
    if num_removed_zeros > 0:
        st.info(f"Excluded {num_removed_zeros} rows with zero confidence scores before determining no data remained.") 