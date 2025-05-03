import os
import pandas as pd
import time
import json
import argparse
from openai import OpenAI
from dotenv import load_dotenv
from collections import Counter
from jinja2 import Environment, FileSystemLoader, select_autoescape
import traceback
from datetime import datetime # Added for timestamp

# --- Constants ---
BYU_AIMS = [
    "Spiritually Strengthening",
    "Intellectually Enlarging",
    "Character Building",
    "Lifelong Learning and Service"
]
# Simplified Aim definitions for the prompt (Consider loading from aims_of_a_BYU_education.md)
AIM_DEFINITIONS = {
    "Spiritually Strengthening": "Focuses on building faith in Jesus Christ, integrating gospel perspectives, strengthening religious commitment.",
    "Intellectually Enlarging": "Focuses on critical thinking, reasoning, communication, quantitative skills, disciplinary competence, integrating theory and practice.",
    "Character Building": "Focuses on integrity, honesty, ethics, self-discipline, compassion, service, courage, moral virtues.",
    "Lifelong Learning and Service": "Focuses on instilling a love of learning, preparing for self-education, developing a desire to serve others and society."
}
DEFAULT_MODEL = "gpt-4.1-mini" # Or choose another capable model
# Changed default output path to data/ directory
DEFAULT_OUTPUT_FILE = "data/classified_learning_outcomes_cleaned_with_suggested_aims.csv"
PROMPT_TEMPLATE_DIR = "prompt_templates"

# --- Define Confidence Columns ---
CONFIDENCE_COLS = [f"confidence_{aim.replace(' ', '_')}" for aim in BYU_AIMS]

# --- Parse Command-line Arguments ---
parser = argparse.ArgumentParser(description="Suggest additional BYU learning outcomes based on existing ones and non-modal Aims.")
parser.add_argument("--input", type=str, default="data/classified_learning_outcomes_cleaned.csv",
                    help="Input CSV file containing classified learning outcomes (default: data/classified_learning_outcomes_cleaned.csv)")
parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_FILE,
                    help=f"Output CSV file path (default: {DEFAULT_OUTPUT_FILE}). If --limit is used, this is the base name for the timestamped sample file.")
parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                    help=f"OpenAI model to use for suggestions (default: {DEFAULT_MODEL})")
parser.add_argument("--limit", type=int, default=-1,
                    help="Process a random sample of N courses (for testing, default: -1, process all). Saves output to a timestamped file in the same directory as --output.")
parser.add_argument("--random_state", type=int, default=42,
                    help="Random state for sampling (for reproducibility, default: 42)")
args = parser.parse_args()

# --- Load API Key ---
def load_api_key():
    load_dotenv() # Load environment variables from .env file
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file or environment variables.")
    return api_key

# --- Setup Jinja Environment ---
def setup_jinja_env(template_dir=PROMPT_TEMPLATE_DIR):
    """Sets up the Jinja2 environment to load templates."""
    try:
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape()
        )
        print(f"Jinja environment loaded for template directory: {template_dir}")
        return env
    except Exception as e:
        print(f"Error setting up Jinja environment: {e}")
        raise # Re-raise exception to stop execution if templates can't load

# --- Load Aim Definitions (Placeholder - Refine as needed) ---
# Option 1: Hardcode based on classifier prompt (as done here)
# Option 2: Parse aims_of_a_BYU_education.md
def load_aim_definitions():
    """Loads detailed definitions for each BYU Aim."""
    # Using definitions extracted from classify_outcomes.py system prompt
    # TODO: Consider parsing the markdown file for richer/more structured definitions
    definitions = {
        "Spiritually Strengthening": "Focuses on building testimonies of the restored gospel of Jesus Christ. Learning outcomes that:\n    *   Encourage learning by both study and faith\n    *   Integrate gospel perspectives with academic subjects\n    *   Help students develop personal testimonies\n    *   Enable students to frame questions in faithful ways\n    *   Connect academic disciplines with spiritual insights\n    *   Strengthen religious understanding and commitment",
        "Intellectually Enlarging": "Focuses on expanding intellectual capabilities and academic excellence. Learning outcomes that:\n    *   Develop critical thinking, reasoning, and analytical skills\n    *   Build effective written and oral communication abilities\n    *   Foster quantitative reasoning and research methodology\n    *   Promote understanding of broad areas of human knowledge\n    *   Develop depth and competence in a specific area or discipline\n    *   Integrate theory with practice and abstract concepts with real-world applications\n    *   Build academic skills like writing, analysis, laboratory techniques, research methods",
        "Character Building": "Focuses on developing moral virtues and Christlike attributes. Learning outcomes that:\n    *   Foster integrity, honesty, and ethical behavior\n    *   Develop self-discipline, self-control, and personal responsibility\n    *   Cultivate compassion, service, and respect for others\n    *   Build courage to defend truth and righteous principles\n    *   Promote modesty, reverence, and other moral virtues\n    *   Encourage personal wholeness and integration of knowledge with conduct",
        "Lifelong Learning and Service": "Focuses on preparing students for ongoing learning and contribution. Learning outcomes that:\n    *   Instill a love of learning that continues beyond formal education\n    *   Prepare students to continue self-education throughout life\n    *   Develop a desire to use knowledge and skills to serve others\n    *   Foster commitment to family, community, church, and society\n    *   Promote an ethic of service rather than self-interest\n    *   Prepare students to apply their education to solve real-world problems"
    }
    print("Loaded BYU Aim definitions.")
    return definitions

# --- Data Preprocessing ---
def aggregate_course_data(group):
    """Aggregates data for a single course group."""
    # Determine modal 'best_aim'
    try:
        # Use mode().tolist() to handle potential multiple modes, take the first one
        mode_result = group['best_aim'].mode()
        modal_aim = mode_result[0] if not mode_result.empty else 'Unknown'
    except Exception:
        modal_aim = 'ErrorCalculatingMode' # Handle potential errors in mode calc

    # Combine title and details for full text
    group['full_outcome_text'] = group['learning_outcome_title'].fillna('').astype(str) + " " + group['learning_outcome_details'].fillna('').astype(str)
    group['full_outcome_text'] = group['full_outcome_text'].str.strip()
    # Filter out empty strings after stripping, then join
    all_outcomes_text = "\n---\n".join(group['full_outcome_text'][group['full_outcome_text'] != ''])

    # Get first value for course identifiers (should be same for all rows in group)
    first_row = group.iloc[0]
    return pd.Series({
        'course_name': first_row.get('course_name', 'N/A'),
        'course_title': first_row.get('course_title', 'N/A'),
        'department': first_row.get('department', 'N/A'),
        'college': first_row.get('college', 'N/A'),
        'modal_aim': modal_aim,
        'all_existing_outcomes': all_outcomes_text
    })

def preprocess_data(input_path):
    """Loads data, filters out unusable rows, and aggregates it by course."""
    print(f"Loading and preprocessing data from {input_path}...")
    try:
        df = pd.read_csv(input_path)
        print(f"Loaded {len(df)} rows.")

        # Check for essential columns (including confidence for filtering)
        required_cols = ['course_url', 'best_aim', 'learning_outcome_title', 'learning_outcome_details', 'course_name', 'course_title'] + CONFIDENCE_COLS
        if not all(col in df.columns for col in required_cols):
            missing = [col for col in required_cols if col not in df.columns]
            print(f"Error: Input CSV missing required columns: {missing}")
            return None

        # --- Pre-filtering --- #
        initial_rows = len(df)

        # 1. Filter out placeholder text rows (similar to dashboard.py)
        no_outcome_text = "No learning outcomes found"
        discontinued_text = "This course is being discontinued"
        filter_pattern = f'{no_outcome_text}|{discontinued_text}'
        # Check in both details and title (case-insensitive)
        placeholder_rows_mask = (
            df['learning_outcome_details'].astype(str).str.contains(filter_pattern, case=False, na=False, regex=True) |
            df['learning_outcome_title'].astype(str).str.contains(filter_pattern, case=False, na=False, regex=True)
        )
        df_filtered = df[~placeholder_rows_mask].copy() # Use .copy() to avoid SettingWithCopyWarning
        num_removed_placeholders = initial_rows - len(df_filtered)
        if num_removed_placeholders > 0:
            print(f"Filtered out {num_removed_placeholders} rows containing placeholder text.")

        # 2. Filter out rows with all zero confidence scores
        # Convert confidence columns to numeric, coercing errors to NaN
        for col in CONFIDENCE_COLS:
            df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')
        # Fill NaN with 0 for the sum check
        df_filtered[CONFIDENCE_COLS] = df_filtered[CONFIDENCE_COLS].fillna(0)
        # Keep rows where the sum of confidence scores is NOT zero
        rows_before_zero_filter = len(df_filtered)
        df_filtered = df_filtered[df_filtered[CONFIDENCE_COLS].sum(axis=1) != 0]
        num_removed_zeros = rows_before_zero_filter - len(df_filtered)
        if num_removed_zeros > 0:
             print(f"Filtered out {num_removed_zeros} rows with zero confidence scores across all aims.")

        if df_filtered.empty:
            print("No valid outcome rows remaining after filtering. Cannot proceed.")
            return None

        print(f"Proceeding with {len(df_filtered)} rows after filtering.")
        # --- End Pre-filtering --- #

        # Group by course URL and apply aggregation *on the filtered data*
        df_filtered['best_aim'].fillna('Unknown', inplace=True)
        courses_summary_df = df_filtered.groupby('course_url').apply(aggregate_course_data).reset_index()

        print(f"Preprocessing complete. Aggregated into {len(courses_summary_df)} courses with valid outcomes.")
        return courses_summary_df

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
        return None
    except Exception as e:
        print(f"Error during data preprocessing: {e}")
        traceback.print_exc()
        return None

# --- Suggestion Function ---

def get_suggestions_for_course(client: OpenAI, jinja_env: Environment, course_info: pd.Series, model_name: str, aim_definitions: dict):
    """Gets 3 suggested outcomes for each non-modal aim for a single course."""
    suggestions = {}
    modal_aim = course_info.get('modal_aim', 'Unknown')
    non_modal_aims = [aim for aim in BYU_AIMS if aim != modal_aim and aim in aim_definitions] # Ensure aim has definition

    print(f"  Course: {course_info.get('course_name', 'N/A')}, Modal Aim: {modal_aim}. Seeking suggestions for: {non_modal_aims}")

    try:
        # Load templates
        system_template = jinja_env.get_template("system_prompt_suggest.j2")
        user_template = jinja_env.get_template("user_prompt_suggest.j2")
    except Exception as e:
        print(f"  Error loading prompt templates: {e}. Skipping suggestions for this course.")
        return {}

    for target_aim in non_modal_aims:
        print(f"    Targeting Aim: {target_aim}...")
        try:
            # Render prompts
            system_prompt = system_template.render(
                target_aim=target_aim,
                aim_definitions=aim_definitions # Pass the whole dict
            )
            user_prompt = user_template.render(
                course_info=course_info,
                target_aim=target_aim
            )

            # Make API call
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.6, # Slightly higher temp for creative suggestions
                max_tokens=300 # Estimate reasonable token limit
            )

            # Parse JSON response
            response_content = response.choices[0].message.content
            try:
                data = json.loads(response_content)
                suggested_outcomes = data.get('suggested_outcomes', [])
                if isinstance(suggested_outcomes, list) and len(suggested_outcomes) == 3:
                    # Store suggestions keyed by aim, e.g., suggested_Spiritually_Strengthening
                    suggestions[f"suggested_{target_aim.replace(' ', '_')}"] = suggested_outcomes
                    print(f"      -> Received 3 suggestions for {target_aim}.")
                else:
                    print(f"      Error: Received invalid suggestions format for {target_aim}. Found: {suggested_outcomes}")
                    suggestions[f"suggested_{target_aim.replace(' ', '_')}"] = ["Error: Invalid format received", "", ""]

            except json.JSONDecodeError:
                print(f"      Error: Failed to decode JSON response for {target_aim}: {response_content}")
                suggestions[f"suggested_{target_aim.replace(' ', '_')}"] = ["Error: JSONDecodeError", "", ""]
            except Exception as e:
                 print(f"      Error processing suggestions for {target_aim}: {e}")
                 suggestions[f"suggested_{target_aim.replace(' ', '_')}"] = [f"Error: {e}", "", ""]

        except Exception as e:
            print(f"    Error calling OpenAI API for {target_aim}: {e}")
            suggestions[f"suggested_{target_aim.replace(' ', '_')}"] = [f"Error: API Call Failed - {e}", "", ""]
            # Consider adding more robust retry logic here if needed

        time.sleep(1.5) # Increased sleep time for safety with multiple calls per course

    return suggestions

# --- Main Execution ---
def main():
    print("Starting learning outcome suggestion process...")
    print(f"Input file: {args.input}")
    print(f"Using model: {args.model}")

    # --- Determine Output Filename --- #
    output_path = args.output
    is_sampling = args.limit > 0

    if is_sampling:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.dirname(output_path)
        base_filename = os.path.basename(output_path)
        sample_filename = f"sample_{timestamp}_{base_filename}"
        output_path = os.path.join(output_dir, sample_filename)
        print(f"SAMPLE MODE: Processing random sample of {args.limit} course(s) with random_state={args.random_state}." )
        print(f"Output will be saved to: {output_path}")
    else:
        print(f"Output file: {output_path}")
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")

    try:
        api_key = load_api_key()
        client = OpenAI(api_key=api_key)
        jinja_env = setup_jinja_env()
        aim_definitions = load_aim_definitions()
        print("OpenAI client and helper functions initialized successfully.")
    except Exception as e:
        print(f"Initialization Error: {e}")
        return

    # 1. Preprocess Data
    courses_summary_df = preprocess_data(args.input)
    if courses_summary_df is None or courses_summary_df.empty:
        print("Failed to preprocess data or data is empty. Exiting.")
        return

    # 2. Get Suggestions (Apply sampling if limit is set)
    all_results = []
    total_courses_available = len(courses_summary_df)
    if args.limit > 0 and args.limit < total_courses_available:
        print(f"\nRandomly sampling {args.limit} out of {total_courses_available} available courses..." )
        process_df = courses_summary_df.sample(n=args.limit, random_state=args.random_state)
        total_to_process = len(process_df)
    elif args.limit > 0:
        print(f"\nLimit ({args.limit}) >= total available courses ({total_courses_available}). Processing all available courses.")
        process_df = courses_summary_df
        total_to_process = total_courses_available
    else:
        process_df = courses_summary_df
        total_to_process = total_courses_available
        print(f"\nFound {total_to_process} unique courses to process.")

    # Iterate through the selected (potentially sampled) DataFrame
    for i, (index, course_info) in enumerate(process_df.iterrows()):
        print(f"\nProcessing course {i+1}/{total_to_process} (Index: {index})...")
        suggestions = get_suggestions_for_course(client, jinja_env, course_info, args.model, aim_definitions)
        course_result = course_info.to_dict()
        course_result.update(suggestions)
        all_results.append(course_result)

    print(f"\nFinished processing {len(all_results)} courses.")

    # 3. Format and Save Output
    if all_results:
        # Format for CSV saving
        final_df = pd.DataFrame(all_results)
        output_columns = list(courses_summary_df.columns) # Use original summary cols as base
        for aim in BYU_AIMS:
            aim_key_base = f"suggested_{aim.replace(' ', '_')}"
            if any(aim_key_base in d for d in all_results):
                 for j in range(3):
                    col_name = f"{aim_key_base}_{j+1}"
                    output_columns.append(col_name)
                    # Use .get() on dict within lambda for safer access
                    final_df[col_name] = final_df[aim_key_base].apply(
                        lambda x: x[j] if isinstance(x, list) and len(x) > j else (
                            x.get(j, "") if isinstance(x, dict) else "" # Handle if suggestions are dicts or missing keys
                        )
                    )
                 # Drop original list/dict column if it exists
                 if aim_key_base in final_df.columns:
                     final_df = final_df.drop(columns=[aim_key_base])
        final_output_columns = [col for col in output_columns if col in final_df.columns]
        # Ensure no duplicate columns before selecting
        final_output_columns = list(dict.fromkeys(final_output_columns))
        final_df = final_df[final_output_columns]

        # Always save to the determined output_path
        try:
            final_df.to_csv(output_path, index=False, encoding='utf-8')
            print(f"\nSuccessfully saved suggestions to {output_path}")
        except Exception as e:
            print(f"Error saving results to {output_path}: {e}")
    else:
        print("No suggestions were generated or processed.")

if __name__ == "__main__":
    main() 