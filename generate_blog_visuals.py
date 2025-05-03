import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re
from pathlib import Path

# Set style for plots
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("colorblind")

# Create output directory if it doesn't exist
output_dir = Path('visualizations')
output_dir.mkdir(exist_ok=True)

def load_data():
    """Load and preprocess the classified learning outcomes data"""
    print("Loading data...")
    df = pd.read_csv('data/classified_learning_outcomes_cleaned.csv')
    
    # Harmonize college names (match dashboard.py)
    if 'college' in df.columns:
        # Define mapping for common college name variations
        college_mapping = {
            "College of Computational, Mathematical, & Physical Sciences": "College of Physical and Mathematical Sciences",
            "College of Computational, Mathematical & Physical Sciences": "College of Physical and Mathematical Sciences", 
            "Kennedy Center for International Studies": "David M. Kennedy Center for International Studies",
            "International and Area Studies": "David M. Kennedy Center for International Studies"
        }
        df['college'] = df['college'].replace(college_mapping)
        print("Harmonized college names.")
    
    # Filter out rows where learning_outcome_details is "No learning outcomes found"
    print("Before filtering 'No learning outcomes found':", len(df))
    df = df[df['learning_outcome_details'] != "No learning outcomes found"]
    print("After filtering 'No learning outcomes found':", len(df))
    
    # Filter out rows where all confidence scores are 0
    zero_confidence_mask = (
        (df['confidence_Spiritually_Strengthening'] == 0) &
        (df['confidence_Intellectually_Enlarging'] == 0) &
        (df['confidence_Character_Building'] == 0) &
        (df['confidence_Lifelong_Learning_and_Service'] == 0)
    )
    print("Rows with all zero confidence scores:", zero_confidence_mask.sum())
    df = df[~zero_confidence_mask]
    print("After filtering all-zero confidence rows:", len(df))
    
    # Drop rows with NaN values in the confidence columns
    df = df.dropna(subset=[
        'confidence_Intellectually_Enlarging',
        'confidence_Spiritually_Strengthening',
        'confidence_Character_Building',
        'confidence_Lifelong_Learning_and_Service'
    ])
    print("After dropping NaN confidence values:", len(df))
    
    # Add best_aim column if it doesn't exist
    if 'best_aim' not in df.columns:
        # Calculate the primary aim for each learning outcome
        aims = ['Intellectually_Enlarging', 'Spiritually_Strengthening', 
                'Character_Building', 'Lifelong_Learning_and_Service']
        
        # Get the aim with the highest confidence for each row
        df['best_aim'] = df[[f'confidence_{aim}' for aim in aims]].idxmax(axis=1)
        # Remove 'confidence_' prefix from best_aim values
        df['best_aim'] = df['best_aim'].str.replace('confidence_', '')
        # Replace underscores with spaces
        df['best_aim'] = df['best_aim'].str.replace('_', ' ')
    
    # Group by course to get unique courses (for certain analyses)
    course_data = df.groupby(['course_name', 'department', 'college']).agg({
        'confidence_Intellectually_Enlarging': 'mean',
        'confidence_Spiritually_Strengthening': 'mean',
        'confidence_Character_Building': 'mean',
        'confidence_Lifelong_Learning_and_Service': 'mean',
    }).reset_index()
    
    # Department and college data
    dept_data = df.groupby('department').agg({
        'confidence_Intellectually_Enlarging': 'mean',
        'confidence_Spiritually_Strengthening': 'mean',
        'confidence_Character_Building': 'mean',
        'confidence_Lifelong_Learning_and_Service': 'mean',
    }).reset_index()
    
    college_data = df.groupby('college').agg({
        'confidence_Intellectually_Enlarging': 'mean',
        'confidence_Spiritually_Strengthening': 'mean',
        'confidence_Character_Building': 'mean',
        'confidence_Lifelong_Learning_and_Service': 'mean',
    }).reset_index()
    
    return df, course_data, dept_data, college_data

def generate_aim_distribution_donut(df):
    """Generate a donut chart showing distribution of primary aims across all learning outcomes"""
    print("Generating aim distribution donut chart...")
    
    # Define the standard aim order to be consistent with other charts
    aims = [
        'Intellectually Enlarging', 
        'Character Building',
        'Lifelong Learning and Service',
        'Spiritually Strengthening'
    ]
    
    # Count occurrences of each aim in the best_aim column
    aim_counts = df['best_aim'].value_counts().reindex(aims, fill_value=0)
    aim_percentages = [count / sum(aim_counts) * 100 for count in aim_counts]
    
    # Create a more compact figure
    fig, ax = plt.subplots(figsize=(7, 5.2))  # Further reduce height
    
    # Create a circle at the center
    circle = plt.Circle((0, 0), 0.7, fc='white')
    
    # Define colors to be consistent with other charts
    colors = sns.color_palette("colorblind", n_colors=len(aims))
    
    # Create the donut chart without labels (we'll use a legend instead)
    wedges, _ = ax.pie(
        aim_counts, 
        labels=None,  # Remove direct labels
        wedgeprops={'width': 0.5},
        colors=colors,
        startangle=90,
    )
    
    # Add percentage labels directly on the wedges
    for i, p in enumerate(wedges):
        ang = (p.theta2 - p.theta1)/2. + p.theta1
        y = np.sin(np.deg2rad(ang))
        x = np.cos(np.deg2rad(ang))
        
        # Calculate position for text
        # For the large segment (IE), place it in the center of the segment
        if aims[i] == 'Intellectually Enlarging':
            ax.text(x*0.4, y*0.4, f"{aim_percentages[i]:.1f}%", 
                   ha='center', va='center', fontsize=11, fontweight='bold')
        # For smaller segments, add percentage near the outer edge if >1%
        elif aim_percentages[i] > 1.0:
            # Place the text on the wedge but near the edge
            ax.text(x*0.85, y*0.85, f"{aim_percentages[i]:.1f}%", 
                   ha='center', va='center', fontsize=9, color='black')
    
    # Add the center circle
    fig.gca().add_artist(circle)
    
    # Equal aspect ratio ensures that pie is drawn as a circle
    ax.set_aspect('equal')
    
    # Position the title closer to the chart
    plt.title('Distribution of BYU Course Learning Objectives', fontsize=12, pad=0)
    
    # Add a legend immediately below the chart with minimal spacing
    ax.legend(
        wedges, 
        aims,
        title="BYU Aims",
        loc="upper center",
        bbox_to_anchor=(0.5, -0.05),  # Move legend very close to chart
        ncol=2,
        fontsize=9,
        title_fontsize=10,
        frameon=False,  # Remove legend frame for cleaner look
        borderpad=0     # Minimal padding
    )
    
    # Remove any extra padding
    plt.tight_layout(pad=0.5)
    plt.subplots_adjust(bottom=0.0, top=0.85)  # Bring title and chart closer
    
    # Save the chart with minimal margins
    plt.savefig(output_dir / 'aim_distribution_donut.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # Return stats for blog update
    return {
        'total_outcomes': len(df),
        'ie_percent': aim_percentages[0],
        'cb_percent': aim_percentages[1],
        'lls_percent': aim_percentages[2],
        'ss_percent': aim_percentages[3],
        'ie_count': aim_counts.iloc[0],
        'cb_count': aim_counts.iloc[1],
        'lls_count': aim_counts.iloc[2],
        'ss_count': aim_counts.iloc[3]
    }

def generate_college_ranking_bar(college_data, df):
    """Generate a bar chart of colleges ranked by percentage of intellectually enlarging outcomes"""
    print("Generating college ranking bar chart...")
    
    # Count how many learning outcomes have each aim as the primary aim by college
    # First get counts by college and aim
    college_aim_counts = df.groupby(['college', 'best_aim']).size().reset_index(name='count')
    
    # Convert to pivot table
    pivot_df = college_aim_counts.pivot_table(
        index='college', 
        columns='best_aim', 
        values='count',
        fill_value=0
    )
    
    # Calculate row percentages (percentage of each aim within a college)
    pivot_df = pivot_df.div(pivot_df.sum(axis=1), axis=0) * 100
    
    # Sort by the Intellectually Enlarging column
    sorted_colleges = pivot_df.sort_values(by='Intellectually Enlarging', ascending=False)
    
    # Calculate number of colleges with >90% IE focus
    ie_dominant_colleges = sorted_colleges[sorted_colleges['Intellectually Enlarging'] > 90]
    
    # Take top 15 for readability
    sorted_colleges = sorted_colleges.head(15)
    
    # Create smaller figure size
    plt.figure(figsize=(10, 8))
    
    # Define the order of aims
    aim_order = [
        'Intellectually Enlarging',
        'Character Building',
        'Lifelong Learning and Service',
        'Spiritually Strengthening'
    ]
    
    # Ensure all aims exist in the dataframe, add with 0 if not present
    for aim in aim_order:
        if aim not in sorted_colleges.columns:
            sorted_colleges[aim] = 0
    
    # Define colors - use consistent colors across charts
    colors = sns.color_palette("colorblind", n_colors=len(aim_order))
    
    # Flip the order for plotting (so highest percentage is at the top)
    plot_colleges = sorted_colleges.iloc[::-1]
    
    # Create the stacked bars
    bottom = np.zeros(len(plot_colleges))
    
    for i, aim in enumerate(aim_order):
        if aim in plot_colleges.columns:  # Check if this aim exists in the data
            plt.barh(
                plot_colleges.index, 
                plot_colleges[aim], 
                left=bottom, 
                color=colors[i],
                label=aim
            )
            bottom += plot_colleges[aim]
    
    # Add IE scores as text with smaller font
    for i, college in enumerate(plot_colleges.index):
        ie_percent = plot_colleges.loc[college, 'Intellectually Enlarging']
        plt.text(
            102,  # Move closer to the bars
            i,
            f"Score: {ie_percent:.1f}",
            va='center',
            fontsize=7  # Even smaller font for scores
        )
    
    # Set chart properties with smaller fonts
    plt.title('BYU Colleges Ranked by Focus on Intellectual Enlargement', fontsize=12)
    plt.xlabel('Percentage Distribution Across Aims', fontsize=10)
    plt.xlim(0, 120)  # Reduce the x-axis limit
    plt.grid(True, linestyle='--', alpha=0.7, which='both', axis='x')
    
    # Adjust y-axis tick label font size - make even smaller
    plt.yticks(fontsize=8)
    plt.xticks(fontsize=8)
    
    # Position legend better to avoid overlap
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=2, fontsize=8)
    
    # Add more space at the bottom for the legend
    plt.subplots_adjust(bottom=0.15)
    
    # Save the chart
    plt.tight_layout()
    plt.savefig(output_dir / 'college_ranking_bar.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # Return information about colleges with >99% IE focus and >90% IE focus
    ie_heavy_colleges = sorted_colleges[sorted_colleges['Intellectually Enlarging'] > 99].index.tolist()
    return {
        'ie_heavy_colleges': ie_heavy_colleges,
        'ie_heavy_count': len(ie_heavy_colleges),
        'ie_dominant_count': len(ie_dominant_colleges)
    }

def calculate_wholistic_score(row):
    """Calculate a score that rewards balanced coverage across all four aims"""
    # Get the confidence scores for each aim
    scores = [
        row['confidence_Intellectually_Enlarging'],
        row['confidence_Spiritually_Strengthening'],
        row['confidence_Character_Building'],
        row['confidence_Lifelong_Learning_and_Service']
    ]
    
    # Normalize to sum to 1
    total = sum(scores)
    if total == 0:
        return 0
    
    normalized = [s/total for s in scores]
    
    # Calculate entropy - higher values mean more balanced distribution
    # Add a small epsilon to avoid log(0)
    epsilon = 1e-10
    entropy = -sum(p * np.log(p + epsilon) for p in normalized if p > 0)
    
    # Scale to 0-100
    max_entropy = -np.log(0.25)  # Maximum entropy when all aims are equal at 0.25
    wholistic_score = (entropy / max_entropy) * 100
    
    return wholistic_score

def generate_balanced_departments_chart(dept_data, df):
    """Generate a chart showing departments with the most balanced coverage of all aims"""
    print("Generating balanced departments chart...")
    
    # Count how many learning outcomes have each aim as the primary aim by department
    dept_aim_counts = df.groupby(['department', 'best_aim']).size().reset_index(name='count')
    
    # Convert to pivot table for department IE calculation
    dept_pivot_df = dept_aim_counts.pivot_table(
        index='department', 
        columns='best_aim', 
        values='count',
        fill_value=0
    )
    
    # Calculate row percentages (percentage of each aim within a department)
    dept_pivot_df = dept_pivot_df.div(dept_pivot_df.sum(axis=1), axis=0) * 100
    
    # Count departments with >90% IE focus
    ie_dominant_depts = dept_pivot_df[dept_pivot_df.get('Intellectually Enlarging', 0) > 90]
    
    # Calculate wholistic score for each department
    dept_data['wholistic_score'] = dept_data.apply(calculate_wholistic_score, axis=1)
    
    # Sort departments by wholistic score
    sorted_depts = dept_data.sort_values(by='wholistic_score', ascending=False)
    
    # Take top 15 for readability
    top_depts = sorted_depts.head(15)
    
    # Flip the order for plotting (so highest score is at the top)
    plot_depts = top_depts.iloc[::-1]
    
    # Create a smaller stacked bar chart
    plt.figure(figsize=(10, 8))
    
    # Define standard aim order to match the college ranking chart
    aims_mapping = {
        'confidence_Intellectually_Enlarging': 'Intellectually Enlarging',
        'confidence_Character_Building': 'Character Building',
        'confidence_Lifelong_Learning_and_Service': 'Lifelong Learning and Service',
        'confidence_Spiritually_Strengthening': 'Spiritually Strengthening'
    }
    
    # Set up the aims in the specified order
    aims = [
        'confidence_Intellectually_Enlarging',
        'confidence_Character_Building', 
        'confidence_Lifelong_Learning_and_Service',
        'confidence_Spiritually_Strengthening'
    ]
    
    # Define colors to be consistent with college chart
    colors = sns.color_palette("colorblind", n_colors=len(aims))
    
    # Create the stacked bars
    bottom = np.zeros(len(plot_depts))
    
    for i, aim in enumerate(aims):
        # Normalize the values for better visualization
        values = plot_depts[aim] / plot_depts[[a for a in aims if a in plot_depts.columns]].sum(axis=1) * 100
        plt.barh(
            plot_depts['department'], 
            values, 
            left=bottom, 
            color=colors[i],
            label=aims_mapping[aim]
        )
        bottom += values
    
    # Add wholistic scores as text with smaller font
    for i, (_, row) in enumerate(plot_depts.iterrows()):
        plt.text(
            102,  # Move closer to the bars
            i,
            f"Score: {row['wholistic_score']:.1f}",
            va='center',
            fontsize=7  # Even smaller font for scores
        )
    
    # Set chart properties with smaller fonts
    plt.title('BYU Departments with Most Balanced Coverage of All Aims', fontsize=12)
    plt.xlabel('Percentage Distribution Across Aims', fontsize=10)
    plt.xlim(0, 120)  # Reduce the x-axis limit
    
    # Adjust y-axis tick label font size - make even smaller
    plt.yticks(fontsize=8)
    plt.xticks(fontsize=8)
    
    # Position legend better to avoid overlap
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=2, fontsize=8)
    
    # Add more space at the bottom for the legend
    plt.subplots_adjust(bottom=0.15)
    
    # Save the chart
    plt.tight_layout()
    plt.savefig(output_dir / 'balanced_departments.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    return {
        'top_balanced_dept': top_depts.iloc[0]['department'],
        'top_balanced_score': top_depts.iloc[0]['wholistic_score'],
        'top_balanced_depts': top_depts['department'].head(5).tolist(),
        'ie_dominant_dept_count': len(ie_dominant_depts)
    }

def update_blog_post(stats):
    """Update the blog post with image paths and key statistics"""
    print("Updating blog post...")
    
    with open('blog_write_up.md', 'r') as file:
        content = file.read()
    
    # Replace placeholder for donut chart
    content = re.sub(
        r'\[DONUT_CHART_PLACEHOLDER\]',
        f'![Distribution of BYU Courses by Primary Aim](visualizations/aim_distribution_donut.png)',
        content
    )
    
    # Replace placeholder for college ranking chart
    content = re.sub(
        r'\[COLLEGE_RANKING_PLACEHOLDER\]',
        f'![BYU Colleges Ranked by Focus on Intellectual Enlargement](visualizations/college_ranking_bar.png)',
        content
    )
    
    # Replace placeholder for balanced departments chart
    content = re.sub(
        r'\[BALANCED_DEPARTMENTS_PLACEHOLDER\]',
        f'![BYU Departments with Most Balanced Coverage of All Aims](visualizations/balanced_departments.png)',
        content
    )
    
    # Replace statistic placeholders
    content = re.sub(r'\[IE_PERCENT\]', f"{stats['ie_percent']:.1f}%", content)
    content = re.sub(r'\[CB_PERCENT\]', f"{stats['cb_percent']:.1f}%", content)
    content = re.sub(r'\[LLS_PERCENT\]', f"{stats['lls_percent']:.1f}%", content)
    content = re.sub(r'\[SS_PERCENT\]', f"{stats['ss_percent']:.1f}%", content)
    
    content = re.sub(r'\[TOP_BALANCED_DEPT\]', f"{stats['top_balanced_dept']}", content)
    content = re.sub(r'\[TOP_BALANCED_SCORE\]', f"{stats['top_balanced_score']:.1f}", content)
    
    # Replace list of intellectually enlarging heavy colleges
    ie_heavy_colleges_text = ", ".join(stats['ie_heavy_colleges'])
    content = re.sub(r'\[IE_HEAVY_COLLEGES\]', ie_heavy_colleges_text, content)
    
    # Replace list of balanced departments
    balanced_depts_text = ", ".join(stats['top_balanced_depts'])
    content = re.sub(r'\[TOP_BALANCED_DEPTS\]', balanced_depts_text, content)
    
    # Replace X and Y placeholders (using correct pattern match)
    content = re.sub(r'\* X colleges', f"* {stats['ie_dominant_count']} colleges", content)
    content = re.sub(r'\* Y departments', f"* {stats['ie_dominant_dept_count']} departments", content)
    
    # Write updated content back to the file
    with open('blog_write_up.md', 'w') as file:
        file.write(content)

def main():
    """Main function to generate all visualizations and update the blog post"""
    print("Starting blog visualization generation...")
    
    # Load data
    df, course_data, dept_data, college_data = load_data()
    
    # Generate visualizations and collect statistics
    aim_stats = generate_aim_distribution_donut(df)  # Use df instead of course_data
    college_stats = generate_college_ranking_bar(college_data, df)
    balance_stats = generate_balanced_departments_chart(dept_data, df)
    
    # Combine all stats for blog update
    all_stats = {**aim_stats, **college_stats, **balance_stats}
    
    # Update the blog post
    update_blog_post(all_stats)
    
    print(f"Visualizations generated in '{output_dir}' directory")
    print("Blog post updated with visualizations and statistics")
    
    # Print some key findings
    print("\nKey findings:")
    print(f"- {aim_stats['ie_percent']:.1f}% of BYU learning outcomes primarily focus on Intellectual Enlargement")
    print(f"- {college_stats['ie_heavy_count']} colleges have >99% focus on Intellectual Enlargement")
    print(f"- {college_stats['ie_dominant_count']} colleges have >90% focus on Intellectual Enlargement")
    print(f"- {balance_stats['ie_dominant_dept_count']} departments have >90% focus on Intellectual Enlargement")
    print(f"- The department with the most balanced coverage is {balance_stats['top_balanced_dept']}")

if __name__ == "__main__":
    main() 