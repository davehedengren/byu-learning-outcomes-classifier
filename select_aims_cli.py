import csv
import datetime
import os
import random

# --- File Paths ---
CSV_FILE_GPT41 = 'data/sample_20250503_060247_classified_learning_outcomes_cleaned_with_suggested_aims.csv'
CSV_FILE_GPT45 = 'data/sample_20250503_060455_classified_learning_outcomes_cleaned_with_suggested_aims.csv'
LOG_FILE = 'aim_selections.csv'
MODEL_STATS_FILE = 'model_preference_stats.csv'

# --- Constants ---
TARGET_AIMS = ["Spiritually Strengthening", "Character Building", "Lifelong Learning and Service"]

# --- Functions ---

def load_data_from_csvs():
    """
    Load course data and suggested outcomes from both CSV files.
    Combines 3 candidates from each file to get 6 per aim category.
    """
    print("Loading data from CSV files...")
    
    # Dictionary to store course data
    courses_data = {}
    
    # Helper function to parse CSV row data
    def parse_course_row(row, source_model):
        course_id = row['course_name']
        
        # Initialize course entry if it doesn't exist
        if course_id not in courses_data:
            courses_data[course_id] = {
                'CourseTitle': row['course_title'],
                'Department': row['department'],
                'College': row['college'],
                'OriginalOutcomes': row['all_existing_outcomes'].split('---'),
                'Candidates': {aim: [] for aim in TARGET_AIMS},
                'CandidateSources': {aim: [] for aim in TARGET_AIMS}
            }
        
        # Add candidates from this row for each aim
        for aim in TARGET_AIMS:
            formatted_aim = aim.replace(' ', '_')
            candidates = []
            for i in range(1, 4):  # Each CSV has 3 candidates per aim
                candidate_key = f'suggested_{formatted_aim}_{i}'
                if candidate_key in row and row[candidate_key]:
                    candidate = row[candidate_key]
                    courses_data[course_id]['Candidates'][aim].append(candidate)
                    courses_data[course_id]['CandidateSources'][aim].append(source_model)
    
    # Read first CSV (GPT-4.1)
    try:
        with open(CSV_FILE_GPT41, 'r', encoding='utf-8', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                parse_course_row(row, 'GPT-4.1')
    except FileNotFoundError:
        print(f"Warning: Could not find file {CSV_FILE_GPT41}")
    
    # Read second CSV (GPT-4.5)
    try:
        with open(CSV_FILE_GPT45, 'r', encoding='utf-8', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                parse_course_row(row, 'GPT-4.5')
    except FileNotFoundError:
        print(f"Warning: Could not find file {CSV_FILE_GPT45}")
    
    # Validate that we have 6 candidates for each aim
    valid_courses = {}
    for course_id, data in courses_data.items():
        is_valid = True
        for aim in TARGET_AIMS:
            if len(data['Candidates'][aim]) != 6:
                print(f"Warning: {course_id} has {len(data['Candidates'][aim])} candidates for {aim} (expected 6)")
                is_valid = False
        
        if is_valid:
            valid_courses[course_id] = data
    
    print(f"Loaded {len(valid_courses)} courses with valid data.")
    return valid_courses

def randomize_candidates(candidates, sources):
    """
    Randomize the order of candidates while maintaining their source mapping.
    Returns:
        - randomized candidates list
        - randomized sources list
        - mapping from new positions to original positions
    """
    # Create pairs of (candidate, source, original_index)
    candidate_pairs = [(c, s, i) for i, (c, s) in enumerate(zip(candidates, sources))]
    
    # Shuffle the pairs
    random.shuffle(candidate_pairs)
    
    # Unpack the shuffled pairs
    rand_candidates = [pair[0] for pair in candidate_pairs]
    rand_sources = [pair[1] for pair in candidate_pairs]
    position_map = [pair[2] for pair in candidate_pairs]  # Maps new position -> original position
    
    return rand_candidates, rand_sources, position_map

def get_user_selection(course_id, course_title, aim_category, original_outcomes, candidates, sources):
    """Presents options to the user and gets their selection."""
    # Randomize candidates for display
    rand_candidates, rand_sources, position_map = randomize_candidates(candidates, sources)
    
    # Display information
    print("\n" + "="*80)
    print(f"Course: {course_id} - {course_title}")
    print(f"Aim Category: {aim_category}")
    print("-"*80)
    print("Original Learning Outcome(s):")
    if original_outcomes:
        for i, outcome in enumerate(original_outcomes):
            print(f"- {outcome.strip()}")
    else:
        print("- None specified.")
    print("-"*80)
    print("Candidate Outcomes (randomized order):")
    for i, candidate in enumerate(rand_candidates):
        print(f"[{i+1}] {candidate}")
    print("[7] Write custom outcome")
    print("[8] Skip this aim for this course")
    print("="*80)

    while True:
        try:
            choice = int(input("Select an option (1-8): "))
            if 1 <= choice <= 8:
                if 1 <= choice <= 6:
                    # Return the original position and source for logging
                    original_position = position_map[choice-1]
                    selected_source = rand_sources[choice-1]
                    return choice, rand_candidates[choice-1], selected_source, original_position
                else:
                    return choice, None, None, None
            else:
                print("Invalid choice. Please enter a number between 1 and 8.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def get_custom_outcome():
    """Prompts user for custom outcome text."""
    while True:
        custom_text = input("Enter your custom learning outcome text: ").strip()
        if custom_text:
            return custom_text
        else:
            print("Custom outcome cannot be empty.")

def log_selection(course_id, course_title, aim_category, selection_text, selection_source, original_position=None):
    """Appends the selection to the CSV log file."""
    file_exists = os.path.isfile(LOG_FILE)
    timestamp = datetime.datetime.now().isoformat()
    
    # Include original position in the row if applicable
    position_info = "" if original_position is None else f" (position {original_position+1})"
    row = [timestamp, course_id, course_title, aim_category, selection_text, selection_source + position_info]

    with open(LOG_FILE, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists or os.path.getsize(LOG_FILE) == 0:
            writer.writerow(['Timestamp', 'CourseID', 'CourseTitle', 'AimCategory', 'SelectedOutcomeText', 'SelectionSource']) # Header
        writer.writerow(row)
    
    print(f"Logged: {aim_category} for {course_id} as '{selection_source}'")

def update_model_stats(selected_model=None):
    """Update statistics on which model's candidates are being preferred."""
    if selected_model is None or 'GPT' not in selected_model:
        return  # Only track GPT model selections
    
    stats = {'GPT-4.1': 0, 'GPT-4.5': 0}
    
    # Read existing stats if available
    if os.path.isfile(MODEL_STATS_FILE) and os.path.getsize(MODEL_STATS_FILE) > 0:
        try:
            with open(MODEL_STATS_FILE, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    stats = row  # Should only be one row
                    # Convert string counts to integers
                    stats = {k: int(v) for k, v in stats.items()}
        except Exception as e:
            print(f"Warning: Could not read model stats file. Error: {e}")
    
    # Update the count for the selected model
    if selected_model in stats:
        stats[selected_model] += 1
    
    # Write updated stats
    with open(MODEL_STATS_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=list(stats.keys()))
        writer.writeheader()
        writer.writerow(stats)

# --- Main Execution ---

def main():
    print("Starting Learning Outcome Selection Process...")
    
    # Initialize log file if it doesn't exist
    if not os.path.isfile(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
        with open(LOG_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Timestamp', 'CourseID', 'CourseTitle', 'AimCategory', 'SelectedOutcomeText', 'SelectionSource'])
        print(f"Created log file: {LOG_FILE}")
    
    # Initialize model stats file if it doesn't exist
    if not os.path.isfile(MODEL_STATS_FILE) or os.path.getsize(MODEL_STATS_FILE) == 0:
        with open(MODEL_STATS_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['GPT-4.1', 'GPT-4.5'])
            writer.writeheader()
            writer.writerow({'GPT-4.1': 0, 'GPT-4.5': 0})
        print(f"Created model stats file: {MODEL_STATS_FILE}")

    # Load course data from CSV files
    courses_data = load_data_from_csvs()
    
    processed_entries = set()
    # Read existing log to avoid re-prompting for already logged entries
    try:
        with open(LOG_FILE, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader) # Skip header
            for row in reader:
                if len(row) >= 4: # Basic check for valid row structure
                    processed_entries.add((row[1], row[3])) # Add (CourseID, AimCategory) tuple
    except FileNotFoundError:
        pass # File doesn't exist yet, which is fine
    except Exception as e:
        print(f"Warning: Could not read existing log file '{LOG_FILE}'. Error: {e}")

    # Process each course and aim category
    for course_id, data in courses_data.items():
        original_outcomes = data.get("OriginalOutcomes", [])
        course_title = data.get("CourseTitle", "Unknown Title")
        all_candidates = data.get("Candidates", {})
        all_sources = data.get("CandidateSources", {})

        for aim_category in TARGET_AIMS:
            # Check if this course/aim combo is already logged
            if (course_id, aim_category) in processed_entries:
                print(f"Skipping already logged entry: {course_id} - {aim_category}")
                continue

            candidates = all_candidates.get(aim_category, [])
            sources = all_sources.get(aim_category, [])
            
            if not candidates or len(candidates) != 6:
                print(f"Warning: Skipping {course_id} - {aim_category} due to missing or incorrect number of candidates.")
                continue

            choice, selected_text, selected_source, original_position = get_user_selection(
                course_id, course_title, aim_category, original_outcomes, candidates, sources
            )

            if 1 <= choice <= 6:
                log_selection(course_id, course_title, aim_category, selected_text, selected_source, original_position)
                update_model_stats(selected_source)
            elif choice == 7:
                custom_text = get_custom_outcome()
                log_selection(course_id, course_title, aim_category, custom_text, "Custom")
            elif choice == 8:
                log_selection(course_id, course_title, aim_category, "", "Skipped")

    print("\nOutcome selection process complete.")
    print(f"Selections logged to: {LOG_FILE}")
    print(f"Model preference statistics logged to: {MODEL_STATS_FILE}")

if __name__ == "__main__":
    main() 