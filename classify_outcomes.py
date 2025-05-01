import os
import pandas as pd
import time
from openai import OpenAI
from dotenv import load_dotenv
import json
from jinja2 import Template
import argparse

# --- Parse command-line arguments ---
parser = argparse.ArgumentParser(description="Classify BYU learning outcomes based on BYU Aims")
parser.add_argument("--input", type=str, default="learning_outcomes.csv",
                    help="Input CSV file containing learning outcomes (default: learning_outcomes.csv)")
parser.add_argument("--output", type=str, default="classified_learning_outcomes.csv",
                    help="Output CSV file to save classifications (default: classified_learning_outcomes.csv)")
parser.add_argument("--save-frequency", type=int, default=1,
                    help="Save progress after this many classifications (default: 1)")
args = parser.parse_args()

# --- Configuration ---
INPUT_CSV = args.input
OUTPUT_CSV = args.output
SAVE_FREQUENCY = args.save_frequency
# Define BYU Aims
BYU_AIMS = [
    "Spiritually Strengthening",
    "Intellectually Enlarging",
    "Character Building",
    "Lifelong Learning and Service"
]
# MODEL_NAME = "gpt-4.1-2025-04-14" # Or another suitable model supporting JSON mode
MODEL_NAME = "gpt-4.1-mini-2025-04-14"

# --- Load API Key ---
def load_api_key():
    load_dotenv() # Load environment variables from .env file
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file or environment variables.")
    return api_key

# --- Classification Function ---
def classify_aim(client: OpenAI, outcome_title: str, outcome_details: str) -> dict | None:
    """Classifies a learning outcome against BYU Aims using OpenAI structured output.
    Returns confidence scores for each aim."""
    if pd.isna(outcome_details) or not outcome_details.strip():
        if pd.isna(outcome_title) or not outcome_title.strip():
            print("Skipping row: Both title and details are empty.")
            return None # Cannot classify empty outcome
        # Use title as details if details are empty but title is not
        outcome_text = str(outcome_title).strip()
        print(f"Warning: Outcome details missing, using title: '{outcome_text[:100]}...'")
    elif pd.isna(outcome_title) or not outcome_title.strip():
        # Use details if title is empty
        outcome_text = str(outcome_details).strip()
        print(f"Warning: Outcome title missing, using details: '{outcome_text[:100]}...'")
    else:
        # Combine title and details
        outcome_text = f"Title: {str(outcome_title).strip()}\nDetails: {str(outcome_details).strip()}"

    # Define templates using Jinja2
    system_template = Template("""You are an expert classifier tasked with aligning university learning outcomes with the Aims of a BYU Education.

The BYU Aims are:

1. SPIRITUALLY STRENGTHENING
   This aim focuses on building testimonies of the restored gospel of Jesus Christ. Learning outcomes that:
   - Encourage learning by both study and faith
   - Integrate gospel perspectives with academic subjects
   - Help students develop personal testimonies
   - Enable students to frame questions in faithful ways
   - Connect academic disciplines with spiritual insights
   - Strengthen religious understanding and commitment

2. INTELLECTUALLY ENLARGING
   This aim focuses on expanding intellectual capabilities and academic excellence. Learning outcomes that:
   - Develop critical thinking, reasoning, and analytical skills
   - Build effective written and oral communication abilities
   - Foster quantitative reasoning and research methodology
   - Promote understanding of broad areas of human knowledge
   - Develop depth and competence in a specific area or discipline
   - Integrate theory with practice and abstract concepts with real-world applications
   - Build academic skills like writing, analysis, laboratory techniques, research methods

3. CHARACTER BUILDING
   This aim focuses on developing moral virtues and Christlike attributes. Learning outcomes that:
   - Foster integrity, honesty, and ethical behavior
   - Develop self-discipline, self-control, and personal responsibility
   - Cultivate compassion, service, and respect for others
   - Build courage to defend truth and righteous principles
   - Promote modesty, reverence, and other moral virtues
   - Encourage personal wholeness and integration of knowledge with conduct

4. LIFELONG LEARNING AND SERVICE
   This aim focuses on preparing students for ongoing learning and contribution. Learning outcomes that:
   - Instill a love of learning that continues beyond formal education
   - Prepare students to continue self-education throughout life
   - Develop a desire to use knowledge and skills to serve others
   - Foster commitment to family, community, church, and society
   - Promote an ethic of service rather than self-interest
   - Prepare students to apply their education to solve real-world problems

Given the learning outcome provided by the user, determine how well it aligns with EACH of these four aims.
Respond ONLY with a valid JSON object containing confidence scores (0-100) for each aim, where 100 means complete confidence 
that the outcome aligns with that aim, and 0 means no alignment at all.

Example JSON format: 
{
  "Spiritually Strengthening": 25,
  "Intellectually Enlarging": 90,
  "Character Building": 40,
  "Lifelong Learning and Service": 60
}
""")
    
    user_template = Template("""Analyze the following learning outcome and provide confidence scores for how well it aligns with each BYU Aim:

    {{ outcome_text }}
    """)
    
    # Render templates with context variables
    system_prompt = system_template.render()
    user_prompt = user_template.render(outcome_text=outcome_text)
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2 # Lower temperature for more deterministic classification
        )
        
        response_content = response.choices[0].message.content
        # Parse the JSON response
        try:
            data = json.loads(response_content)
            # Verify all aims are present in the response
            confidence_scores = {}
            for aim in BYU_AIMS:
                if aim in data:
                    confidence_scores[aim] = data[aim]
                else:
                    print(f"Warning: Model response missing confidence for '{aim}'")
                    confidence_scores[aim] = 0
            
            # Find the highest confidence aim for logging
            best_aim = max(confidence_scores, key=confidence_scores.get)
            print(f"  -> Highest confidence: {best_aim} ({confidence_scores[best_aim]}%)")
            
            return confidence_scores
        except json.JSONDecodeError:
            print(f"Error: Failed to decode JSON response: {response_content}")
            return None
        except Exception as e:
            print(f"Error parsing JSON data '{response_content}': {e}")
            return None
            
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

def save_progress(df, output_path, message=None):
    """Save the current progress to CSV"""
    try:
        df.to_csv(output_path, index=False, encoding='utf-8')
        if message:
            print(message)
    except Exception as e:
        print(f"Error saving progress to {output_path}: {e}")

def create_key(row):
    """Create a unique key for a row based on course name and learning outcome ID"""
    return f"{row.get('course_name', '')}-{row.get('learning_outcome_id', '')}"

# --- Main Execution ---
def main():
    print(f"Starting learning outcome classification process...")
    print(f"Input file: {INPUT_CSV}")
    print(f"Output file: {OUTPUT_CSV}")
    print(f"Save frequency: Every {SAVE_FREQUENCY} classifications")
    
    # Load OpenAI API Key
    try:
        api_key = load_api_key()
        client = OpenAI(api_key=api_key)
        print("OpenAI API key loaded successfully.")
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Read the scraped data
    try:
        if not os.path.exists(INPUT_CSV):
             print(f"Error: Input file not found at {INPUT_CSV}")
             return
             
        input_df = pd.read_csv(INPUT_CSV)
        original_count = len(input_df)
        print(f"Successfully read {original_count} rows from {INPUT_CSV}")
        
        # Add unique keys to input data
        input_df['key'] = input_df.apply(create_key, axis=1)
        
        # Check for existing output file to resume processing
        already_processed_keys = set()
        if os.path.exists(OUTPUT_CSV):
            print(f"Found existing output file {OUTPUT_CSV}. Checking for already processed records...")
            try:
                output_df = pd.read_csv(OUTPUT_CSV)
                # Only consider rows that have confidence scores (not empty placeholders)
                for i, row in output_df.iterrows():
                    if not pd.isna(row.get('best_aim')):
                        already_processed_keys.add(create_key(row))
                
                print(f"Found {len(already_processed_keys)} already processed records.")
            except Exception as e:
                print(f"Error reading existing output file: {e}. Starting fresh.")
                # If there's an error reading the output, we'll just start fresh
                if os.path.exists(OUTPUT_CSV):
                    os.remove(OUTPUT_CSV)
                    
        # Filter to unprocessed records
        input_df['already_processed'] = input_df['key'].isin(already_processed_keys)
        unprocessed_df = input_df[~input_df['already_processed']]
        
        # Check if there's anything left to process
        if len(unprocessed_df) == 0:
            print("All records have already been processed! Nothing to do.")
            return
        
        print(f"Continuing with {len(unprocessed_df)} records to process.")
        
        # Clean up working columns
        unprocessed_df = unprocessed_df.drop(columns=['key', 'already_processed'])
        
        # Display first few rows for confirmation
        print("\nFirst 5 rows of the data to process:")
        print(unprocessed_df.head().to_string())
        
        # --- Apply Classification --- 
        print("\nStarting classification...")
        
        # Process records
        total_rows = len(unprocessed_df)
        records_saved = 0
        
        # Create an empty dataframe to hold all classified results
        results = []
        
        for i, row in unprocessed_df.iterrows():
            print(f"Processing row {i} ({records_saved + 1}/{total_rows})...")
            # Extract title and details, handle potential NaN values
            title = row.get('learning_outcome_title', '') 
            details = row.get('learning_outcome_details', '')

            # Call the classification function
            confidence_scores = classify_aim(client, title, details)
            
            if confidence_scores is not None:
                # Create a copy of the row with confidence scores added
                new_row = row.copy()
                for aim in BYU_AIMS:
                    new_row[f'confidence_{aim.replace(" ", "_")}'] = confidence_scores[aim]
                new_row['best_aim'] = max(confidence_scores, key=confidence_scores.get)
                
                # Add to our results list
                results.append(new_row)
                
                records_saved += 1
                
                # Save all processed records at specified frequency
                if records_saved % SAVE_FREQUENCY == 0:
                    # Convert results to dataframe
                    results_df = pd.DataFrame(results)
                    
                    # If the output file exists, read it and merge
                    if os.path.exists(OUTPUT_CSV):
                        existing_df = pd.read_csv(OUTPUT_CSV)
                        # To avoid duplicates, we'll extract the existing keys again
                        existing_keys = set()
                        for _, row in existing_df.iterrows():
                            if not pd.isna(row.get('best_aim')):
                                existing_keys.add(create_key(row))
                        
                        # Add key column to results for filtering
                        results_df['key'] = results_df.apply(create_key, axis=1)
                        # Only keep new results not already in the file
                        new_results = results_df[~results_df['key'].isin(existing_keys)]
                        new_results = new_results.drop(columns=['key'])
                        
                        # Combine with existing and save
                        combined_df = pd.concat([existing_df, new_results], ignore_index=True)
                        save_progress(combined_df, OUTPUT_CSV, 
                                      f"Saved progress: {records_saved}/{total_rows} records processed.")
                    else:
                        # Just save the new results
                        save_progress(results_df, OUTPUT_CSV, 
                                      f"Saved progress: {records_saved}/{total_rows} records processed.")
            
            # Pause between API calls
            time.sleep(1)
        
        # Final save
        if len(results) > 0:
            # Convert all results to dataframe
            results_df = pd.DataFrame(results)
            
            # If the output file exists, read it and merge (avoiding duplicates)
            if os.path.exists(OUTPUT_CSV):
                existing_df = pd.read_csv(OUTPUT_CSV)
                # Extract existing keys to avoid duplicates
                existing_keys = set()
                for _, row in existing_df.iterrows():
                    if not pd.isna(row.get('best_aim')):
                        existing_keys.add(create_key(row))
                
                # Add key column to results for filtering
                results_df['key'] = results_df.apply(create_key, axis=1)
                # Only keep new results not already in the file
                new_results = results_df[~results_df['key'].isin(existing_keys)]
                new_results = new_results.drop(columns=['key'])
                
                # Combine with existing and save
                combined_df = pd.concat([existing_df, new_results], ignore_index=True)
                save_progress(combined_df, OUTPUT_CSV, 
                              f"\nClassification complete. All {records_saved} records processed.")
            else:
                # Just save the new results
                save_progress(results_df, OUTPUT_CSV, 
                              f"\nClassification complete. All {records_saved} records processed.")

            # Display final results
            print("\nFinal results (first 5 rows):")
            final_results = pd.read_csv(OUTPUT_CSV)
            print(final_results.head().to_string())
        else:
            print("No records were successfully processed.")
            
    except FileNotFoundError:
        print(f"Error: Input file not found at {INPUT_CSV}")
    except pd.errors.EmptyDataError:
        print(f"Error: Input file {INPUT_CSV} is empty.")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        
if __name__ == "__main__":
    main() 