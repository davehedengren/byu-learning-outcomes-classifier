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
DEFAULT_OUTPUT_FILE = "classified_learning_outcomes_cleaned_with_suggested_aims.csv"
PROMPT_TEMPLATE_DIR = "prompt_templates"

# --- Parse Command-line Arguments ---
parser = argparse.ArgumentParser(description="Suggest additional BYU learning outcomes based on existing ones and non-modal Aims.")
parser.add_argument("--input", type=str, default="data/classified_learning_outcomes_cleaned.csv",
                    help="Input CSV file containing classified learning outcomes (default: data/classified_learning_outcomes_cleaned.csv)")
parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_FILE,
                    help=f"Output CSV file to save suggestions (default: {DEFAULT_OUTPUT_FILE})")
parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                    help=f"OpenAI model to use for suggestions (default: {DEFAULT_MODEL})")
# Add arguments for resuming/batching later if needed
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
    """Loads data and aggregates it by course."""
    print(f"Loading and preprocessing data from {input_path}...")
    try:
        df = pd.read_csv(input_path)
        print(f"Loaded {len(df)} rows.")

        # Check for essential columns
        required_cols = ['course_url', 'best_aim', 'learning_outcome_title', 'learning_outcome_details', 'course_name', 'course_title']
        if not all(col in df.columns for col in required_cols):
            missing = [col for col in required_cols if col not in df.columns]
            print(f"Error: Input CSV missing required columns: {missing}")
            return None

        # Group by course URL and apply aggregation
        # Make sure NaNs in best_aim don't break mode calculation
        df['best_aim'].fillna('Unknown', inplace=True)

        courses_summary_df = df.groupby('course_url').apply(aggregate_course_data).reset_index()

        print(f"Preprocessing complete. Aggregated into {len(courses_summary_df)} courses.")
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
    print(f"Output file: {args.output}")
    print(f"Using model: {args.model}")

    # Load API Key
    try:
        api_key = load_api_key()
        client = OpenAI(api_key=api_key)
        jinja_env = setup_jinja_env() # Setup Jinja env
        aim_definitions = load_aim_definitions() # Load definitions
        print("OpenAI client and helper functions initialized successfully.")
    except ValueError as e:
        print(f"Error: {e}")
        return

    # 1. Preprocess Data
    courses_summary_df = preprocess_data(args.input)
    if courses_summary_df is None or courses_summary_df.empty:
        print("Failed to preprocess data or data is empty. Exiting.")
        return

    # 2. Get Suggestions (Iterate through courses)
    all_results = [] # Store combined course info + suggestions
    total_courses = len(courses_summary_df)
    print(f"\nFound {total_courses} unique courses to process.")

    # Actual loop
    for i, course_info in courses_summary_df.iterrows():
        print(f"\nProcessing course {i+1}/{total_courses}...")
        # Pass jinja_env and aim_definitions to the function
        suggestions = get_suggestions_for_course(client, jinja_env, course_info, args.model, aim_definitions)

        # Combine course_info (as dict) with suggestions dictionary
        course_result = course_info.to_dict()
        course_result.update(suggestions) # Add suggestions to the course data
        all_results.append(course_result)

        # Consider adding progress saving logic here for long runs

    print(f"\nFinished processing {len(all_results)} courses.")

    # 3. Format and Save Output
    if all_results:
        final_df = pd.DataFrame(all_results)

        # Define final column structure and order
        # Start with original course info columns
        output_columns = list(courses_summary_df.columns)
        # Add columns for suggestions (3 for each non-modal aim)
        for aim in BYU_AIMS:
            aim_key_base = f"suggested_{aim.replace(' ', '_')}"
            # Check if this aim's suggestions exist in *any* result row
            # This handles cases where a course might only have 1 or 2 non-modal aims
            if any(aim_key_base in d for d in all_results):
                 # Unpack list into separate columns, handle potential missing suggestions
                 for j in range(3):
                    col_name = f"{aim_key_base}_{j+1}"
                    output_columns.append(col_name)
                    # Apply lambda to safely extract suggestion, default to empty string
                    final_df[col_name] = final_df[aim_key_base].apply(lambda x: x[j] if isinstance(x, list) and len(x) > j else "")
                 # Remove the original list column if desired
                 if aim_key_base in final_df.columns:
                     final_df = final_df.drop(columns=[aim_key_base])

        # Ensure only existing columns are selected and ordered
        final_output_columns = [col for col in output_columns if col in final_df.columns]
        final_df = final_df[final_output_columns]

        try:
            final_df.to_csv(args.output, index=False, encoding='utf-8')
            print(f"\nSuccessfully saved suggestions to {args.output}")
        except Exception as e:
            print(f"Error saving results to {args.output}: {e}")
    else:
        print("No suggestions were generated or processed.")

if __name__ == "__main__":
    main() 