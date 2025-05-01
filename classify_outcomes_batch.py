import os
import pandas as pd
import time
import json
import uuid
from openai import OpenAI
from dotenv import load_dotenv
import argparse
from concurrent.futures import ThreadPoolExecutor
import threading
import pprint

# --- Parse command-line arguments ---
parser = argparse.ArgumentParser(description="Classify BYU learning outcomes based on BYU Aims using OpenAI's Batch API")
parser.add_argument("--input", type=str, default="learning_outcomes.csv",
                    help="Input CSV file containing learning outcomes (default: learning_outcomes.csv)")
parser.add_argument("--output", type=str, default="classified_learning_outcomes_batch.csv",
                    help="Output CSV file to save classifications (default: classified_learning_outcomes_batch.csv)")
parser.add_argument("--batch-size", type=int, default=1000,
                    help="Number of rows to process in each batch (default: 1000)")
parser.add_argument("--temp-dir", type=str, default="temp_batches",
                    help="Directory for temporary batch files (default: temp_batches)")
parser.add_argument("--max-workers", type=int, default=1,
                    help="Maximum number of concurrent batch jobs to monitor (default: 1)")
parser.add_argument("--check-interval", type=int, default=30,
                    help="Seconds between status checks for batch jobs (default: 30)")
parser.add_argument("--debug", action="store_true", 
                    help="Enable debug mode with more detailed error reporting")
args = parser.parse_args()

# --- Configuration ---
INPUT_CSV = args.input
OUTPUT_CSV = args.output
BATCH_SIZE = args.batch_size
TEMP_DIR = args.temp_dir
MAX_WORKERS = args.max_workers
CHECK_INTERVAL = args.check_interval
DEBUG = args.debug
# Define BYU Aims
BYU_AIMS = [
    "Spiritually Strengthening",
    "Intellectually Enlarging",
    "Character Building",
    "Lifelong Learning and Service"
]
MODEL_NAME = "gpt-4.1-mini-2025-04-14"  # Or another suitable model supporting JSON mode

# Thread-safe dictionary for storing results
results_lock = threading.Lock()
all_results = {}

# --- Load API Key ---
def load_api_key():
    load_dotenv()  # Load environment variables from .env file
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file or environment variables.")
    return api_key

# --- Debug helpers ---
def dump_object(obj, name="object"):
    """Dump an object's attributes for debugging"""
    if not DEBUG:
        return
    
    print(f"\n----- DEBUG: {name} -----")
    try:
        # Try to convert to dict for nicer printing
        if hasattr(obj, 'model_dump'):
            # For Pydantic models
            obj_dict = obj.model_dump()
        elif hasattr(obj, '__dict__'):
            # For regular objects
            obj_dict = obj.__dict__
        else:
            # Just use the object itself
            obj_dict = obj
            
        # Pretty print the dict
        pprint.pprint(obj_dict)
    except Exception as e:
        print(f"Error dumping {name}: {e}")
        print(obj)
    print("-----------------------\n")

# --- Prepare system prompt ---
def get_system_prompt():
    return """You are an expert classifier tasked with aligning university learning outcomes with the Aims of a BYU Education.

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
"""

# --- Prepare batch request ---
def prepare_batch_request(input_df, batch_idx, start_idx, end_idx, batch_file):
    """Create a JSONL file for batch request from a dataframe slice."""
    print(f"Preparing batch request file for batch {batch_idx+1} (rows {start_idx}-{end_idx})...")
    
    try:
        # Create list for batch requests
        batch_requests = []
        system_prompt = get_system_prompt()
        
        # Process each row in the slice
        for i, row in input_df.iloc[start_idx:end_idx].iterrows():
            # Extract title and details
            title = row.get('learning_outcome_title', '')
            details = row.get('learning_outcome_details', '')
            
            # Skip if both title and details are empty
            if (pd.isna(title) or not title.strip()) and (pd.isna(details) or not details.strip()):
                print(f"Skipping row {i}: Both title and details are empty.")
                continue
                
            # Combine title and details
            if pd.isna(title) or not title.strip():
                outcome_text = str(details).strip()
            elif pd.isna(details) or not details.strip():
                outcome_text = str(title).strip()
            else:
                outcome_text = f"Title: {str(title).strip()}\nDetails: {str(details).strip()}"
            
            # Create a unique ID for this request
            custom_id = f"outcome-{i}"
            
            # Create batch request entry
            batch_request = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": MODEL_NAME,
                    "response_format": {"type": "json_object"},
                    "temperature": 0.0,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Analyze the following learning outcome and provide confidence scores for how well it aligns with each BYU Aim:\n\n{outcome_text}"}
                    ]
                }
            }
            
            # Add to list
            batch_requests.append(batch_request)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(batch_file), exist_ok=True)
        
        # Write batch requests to JSONL file
        with open(batch_file, 'w') as f:
            for request in batch_requests:
                f.write(json.dumps(request) + '\n')
        
        # Save a sample request for debugging
        if DEBUG:
            sample_file = f"{batch_file}.sample.json"
            with open(sample_file, 'w') as f:
                if batch_requests:
                    json.dump(batch_requests[0], f, indent=2)
                    print(f"Sample request saved to {sample_file}")
        
        print(f"Successfully created batch file with {len(batch_requests)} requests at {batch_file}")
        
        # Print batch file size for debugging
        if os.path.exists(batch_file):
            size_mb = os.path.getsize(batch_file) / (1024 * 1024)
            print(f"Batch file size: {size_mb:.2f} MB")
            
        return True, len(batch_requests)
    
    except Exception as e:
        print(f"Error preparing batch request: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

# --- Create batch job ---
def create_batch_job(client, batch_file, batch_idx):
    """Upload the JSONL file and create a batch job."""
    try:
        print(f"Uploading batch file {batch_idx+1}...")
        # Upload file
        batch_file_obj = client.files.create(
            file=open(batch_file, "rb"),
            purpose="batch"
        )
        
        print(f"File uploaded with ID: {batch_file_obj.id}")
        
        # Create batch job
        print(f"Creating batch job {batch_idx+1}...")
        batch_job = client.batches.create(
            input_file_id=batch_file_obj.id,
            endpoint="/v1/chat/completions",
            completion_window="24h"  # Will be completed within 24h
        )
        
        print(f"Batch job {batch_idx+1} created with ID: {batch_job.id}")
        
        # Debug: Dump batch job object
        if DEBUG:
            dump_object(batch_job, f"Batch job {batch_idx+1}")
            
        return batch_job
    
    except Exception as e:
        print(f"Error creating batch job: {e}")
        import traceback
        traceback.print_exc()
        return None

# --- Process a single batch ---
def process_batch(client, input_df, batch_idx, start_idx, end_idx, total_rows, total_batches, input_csv, output_csv):
    """Prepare, submit, monitor and process a single batch."""
    # Generate unique identifiers for this batch
    batch_id = str(uuid.uuid4())[:8]
    batch_file = os.path.join(TEMP_DIR, f"batch_{batch_idx}_{batch_id}.jsonl")
    results_file = os.path.join(TEMP_DIR, f"results_{batch_idx}_{batch_id}.jsonl")
    errors_file = os.path.join(TEMP_DIR, f"errors_{batch_idx}_{batch_id}.json")
    
    print(f"\n--- Processing Batch {batch_idx+1}/{total_batches} (rows {start_idx}-{end_idx}) ---")
    
    # Prepare batch request
    success, request_count = prepare_batch_request(input_df, batch_idx, start_idx, end_idx, batch_file)
    if not success or request_count == 0:
        print(f"Skipping batch {batch_idx+1} due to preparation error or no valid requests.")
        return
    
    # Create batch job
    batch_job = create_batch_job(client, batch_file, batch_idx)
    if not batch_job:
        print(f"Failed to create batch job {batch_idx+1}.")
        return
    
    # Monitor batch status
    retry_count = 0
    max_retries = 3
    
    while retry_count <= max_retries:
        try:
            # Initial wait to give the job time to start
            time.sleep(CHECK_INTERVAL)
            
            while True:
                # Get current status
                batch_object = client.batches.retrieve(batch_job.id)
                status = batch_object.status
                
                # Print current status
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{timestamp}] Batch {batch_idx+1}/{total_batches} status: {status}")
                
                # Debug: Dump batch object on status changes
                if DEBUG:
                    dump_object(batch_object, f"Batch {batch_idx+1} status update")
                
                # Check if job is complete or failed
                if status == "completed":
                    # Process batch results
                    batch_results = process_batch_results(client, batch_object, batch_idx, results_file)
                    
                    # Add to global results
                    with results_lock:
                        all_results.update(batch_results)
                        current_count = len(all_results)
                        print(f"Progress: {current_count}/{total_rows} outcomes classified ({current_count/total_rows:.1%})")
                        
                        # Save intermediate results
                        save_intermediate_results(input_df, input_csv, output_csv)
                    
                    return
                elif status == "failed":
                    # Save error details
                    if DEBUG:
                        try:
                            with open(errors_file, 'w') as f:
                                json.dump(batch_object.model_dump() if hasattr(batch_object, 'model_dump') else vars(batch_object), f, indent=2, default=str)
                            print(f"Error details saved to {errors_file}")
                            
                            # Check for error details in the object
                            error_details = getattr(batch_object, 'error', None)
                            if error_details:
                                print(f"ERROR DETAILS: {error_details}")
                        except Exception as e:
                            print(f"Failed to save error details: {e}")
                    
                    if retry_count < max_retries:
                        retry_count += 1
                        print(f"Batch {batch_idx+1} failed. Retrying ({retry_count}/{max_retries})...")
                        
                        # Try with a smaller slice for the retry
                        if retry_count > 1:
                            # Cut the batch size in half for subsequent retries
                            mid_point = start_idx + (end_idx - start_idx) // 2
                            print(f"Reducing batch size for retry: {start_idx}-{mid_point} (half of original)")
                            end_idx = mid_point
                            
                            # Generate a new batch file for the smaller slice
                            batch_id = str(uuid.uuid4())[:8]
                            batch_file = os.path.join(TEMP_DIR, f"batch_{batch_idx}_retry{retry_count}_{batch_id}.jsonl")
                            success, request_count = prepare_batch_request(input_df, batch_idx, start_idx, end_idx, batch_file)
                            if not success or request_count == 0:
                                print(f"Failed to prepare smaller batch for retry {retry_count}.")
                                return
                        
                        # Create a new batch job
                        batch_job = create_batch_job(client, batch_file, batch_idx)
                        if not batch_job:
                            print(f"Failed to recreate batch job {batch_idx+1} on retry {retry_count}.")
                            return
                        break  # Break the inner loop to restart monitoring
                    else:
                        print(f"Batch {batch_idx+1} failed after {max_retries} retries. Giving up.")
                        return
                elif status in ["validating", "in_progress", "finalizing"]:
                    # Still running, wait and check again
                    time.sleep(CHECK_INTERVAL)
                else:
                    print(f"Batch {batch_idx+1} has unexpected status: {status}. Giving up.")
                    return
        except Exception as e:
            print(f"Error monitoring batch {batch_idx+1}: {e}")
            if retry_count < max_retries:
                retry_count += 1
                print(f"Retrying monitoring batch {batch_idx+1} ({retry_count}/{max_retries})...")
                time.sleep(CHECK_INTERVAL)
            else:
                print(f"Failed to monitor batch {batch_idx+1} after {max_retries} retries. Giving up.")
                return

# --- Process batch results ---
def process_batch_results(client, batch_object, batch_idx, results_file):
    """Process the batch results and return a dictionary of results."""
    if not batch_object or batch_object.status != "completed":
        print(f"Batch {batch_idx+1} did not complete successfully.")
        return {}
        
    try:
        print(f"Processing batch {batch_idx+1} results...")
        
        # Get the output file ID from the batch object
        output_file_id = batch_object.output_file_id
        if not output_file_id:
            print(f"No output file ID found in batch {batch_idx+1} object.")
            return {}
            
        # Download result file
        result = client.files.content(output_file_id)
        json_data = result.content.decode('utf-8')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        # Save raw results for reference
        with open(results_file, 'w') as f:
            f.write(json_data)
        print(f"Raw results for batch {batch_idx+1} saved to {results_file}")
        
        # Process results
        results_dict = {}
        for line in json_data.splitlines():
            try:
                json_record = json.loads(line)
                custom_id = json_record.get("custom_id", "")
                
                # Extract row index from custom_id
                if custom_id.startswith("outcome-"):
                    row_idx = int(custom_id.split("-")[1])
                    
                    # Extract confidence scores from response
                    response_body = json_record.get("response", {}).get("body", {})
                    choices = response_body.get("choices", [])
                    
                    if choices and len(choices) > 0:
                        message_content = choices[0].get("message", {}).get("content", "{}")
                        try:
                            confidence_scores = json.loads(message_content)
                            
                            # Determine and clean the best aim
                            best_aim = "" # Default if no scores
                            if confidence_scores:
                                best_aim = max(confidence_scores, key=confidence_scores.get).strip()
                                
                            # Store cleaned results by row index
                            results_dict[row_idx] = {
                                'scores': confidence_scores,
                                'best_aim': best_aim
                            }
                        except json.JSONDecodeError:
                            print(f"Error parsing JSON from message content for {custom_id}: {message_content}")
            except Exception as e:
                print(f"Error processing result line: {e}")
                
        print(f"Successfully processed {len(results_dict)} results from batch {batch_idx+1}.")
        return results_dict
    
    except Exception as e:
        print(f"Error processing batch results: {e}")
        import traceback
        traceback.print_exc()
        return {}

# --- Save intermediate results ---
def save_intermediate_results(input_df, input_csv, output_csv):
    """Save intermediate results to a CSV file."""
    try:
        # Apply results to the input dataframe
        output_df = apply_results_to_df(input_df, all_results)
        
        # Save intermediate results
        intermediate_file = f"{output_csv}.partial"
        output_df.to_csv(intermediate_file, index=False)
        
        completed = len(all_results)
        total = len(input_df)
        print(f"Saved intermediate results ({completed}/{total} rows, {completed/total:.1%}) to {intermediate_file}")
        
        return output_df
    except Exception as e:
        print(f"Error saving intermediate results: {e}")
        return None

# --- Apply results to dataframe ---
def apply_results_to_df(input_df, results_dict):
    """Apply classification results to the input dataframe."""
    # Create a copy of the dataframe
    output_df = input_df.copy()
    
    # Add confidence score columns if they don't exist
    for aim in BYU_AIMS:
        column_name = f"confidence_{aim.replace(' ', '_')}"
        if column_name not in output_df.columns:
            output_df[column_name] = None
    
    # Add best aim column if it doesn't exist
    if "best_aim" not in output_df.columns:
        output_df["best_aim"] = None
    
    # Fill in results
    for i, row in input_df.iterrows():
        if i in results_dict:
            result_data = results_dict[i]
            confidence_scores = result_data.get('scores', {})
            best_aim = result_data.get('best_aim', None) # Already cleaned
            
            # Add confidence scores
            for aim in BYU_AIMS:
                column_name = f"confidence_{aim.replace(' ', '_')}"
                if aim in confidence_scores:
                    output_df.at[i, column_name] = confidence_scores[aim]
            
            # Add cleaned best aim
            if best_aim:
                output_df.at[i, "best_aim"] = best_aim
    
    return output_df

# --- Main Execution ---
def main():
    print(f"Starting learning outcome classification process using OpenAI's Batch API...")
    print(f"Input file: {INPUT_CSV}")
    print(f"Output file: {OUTPUT_CSV}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Temporary directory: {TEMP_DIR}")
    print(f"Maximum concurrent workers: {MAX_WORKERS}")
    print(f"Status check interval: {CHECK_INTERVAL} seconds")
    if DEBUG:
        print(f"Debug mode: ENABLED")
    
    # Load OpenAI API Key
    try:
        api_key = load_api_key()
        client = OpenAI(api_key=api_key)
        print("OpenAI API key loaded successfully.")
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Create temp directory if it doesn't exist
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Read the input data
    try:
        input_df = pd.read_csv(INPUT_CSV)
        total_rows = len(input_df)
        print(f"Successfully read {total_rows} rows from {INPUT_CSV}")
        
        # --- Clean input string columns ---
        print("Cleaning whitespace from input columns...")
        input_string_cols = ['course_name', 'course_title', 'department', 'college', 'learning_outcome_title', 'learning_outcome_details']
        cleaned_input_count = 0
        for col in input_string_cols:
            if col in input_df.columns:
                input_df[col] = input_df[col].fillna('').astype(str).str.strip()
                cleaned_input_count += 1
        print(f"Cleaned {cleaned_input_count} input string columns.")
        # --- End cleaning ---

        # Calculate number of batches
        num_batches = (total_rows + BATCH_SIZE - 1) // BATCH_SIZE  # Ceiling division
        print(f"Will process data in {num_batches} parallel batches of up to {BATCH_SIZE} rows each.")
        
        # Try a test batch with just a few rows if in debug mode
        if DEBUG:
            print("\n--- Running a small test batch first ---")
            test_size = min(10, total_rows)
            test_batch_id = str(uuid.uuid4())[:8]
            test_batch_file = os.path.join(TEMP_DIR, f"test_batch_{test_batch_id}.jsonl")
            test_results_file = os.path.join(TEMP_DIR, f"test_results_{test_batch_id}.jsonl")
            
            # Prepare test batch
            success, count = prepare_batch_request(input_df, 0, 0, test_size, test_batch_file)
            if success and count > 0:
                # Create test batch job
                test_batch_job = create_batch_job(client, test_batch_file, 0)
                if test_batch_job:
                    print(f"Test batch submitted with {count} items. ID: {test_batch_job.id}")
                    print(f"Will continue with full processing regardless of test batch result.")
                    print("Check test_batch_... files in {TEMP_DIR} for test results.")
            
            print("--- End of test batch setup ---\n")
        
        # Process batches in parallel with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all batches
            futures = []
            for batch_idx in range(num_batches):
                # Calculate start and end indices for this batch
                start_idx = batch_idx * BATCH_SIZE
                end_idx = min(start_idx + BATCH_SIZE, total_rows)
                
                # Submit batch processing
                future = executor.submit(
                    process_batch, 
                    client, 
                    input_df,
                    batch_idx,
                    start_idx,
                    end_idx,
                    total_rows,
                    num_batches,
                    INPUT_CSV,
                    OUTPUT_CSV
                )
                futures.append(future)
                # Small delay between submissions to avoid rate limiting
                time.sleep(1)
            
            print(f"All {num_batches} batches submitted. Waiting for completion...")
            
            # Wait for all futures to complete
            for future in futures:
                future.result()
        
        # Final processing
        print(f"\nAll batches completed. Generating final output...")
        final_df = apply_results_to_df(input_df, all_results)
        final_df.to_csv(OUTPUT_CSV, index=False)
        
        classified_count = len(all_results)
        print(f"\nClassification complete! Results saved to {OUTPUT_CSV}")
        print(f"Successfully classified {classified_count}/{total_rows} learning outcomes ({classified_count/total_rows:.1%}).")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 