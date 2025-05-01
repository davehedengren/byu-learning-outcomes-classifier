import json
import tiktoken
import os

# Configuration
BATCH_FILE = "my_batch.jsonl"  # The large batch file generated previously
MODEL_NAME = "gpt-4.1-mini-2025-04-14" # Make sure this matches the model used in the batch script

def estimate_tokens_in_batch_file(filepath, model_name):
    """Reads a JSONL batch file and estimates the total tokens for all requests."""
    total_tokens = 0
    request_count = 0

    if not os.path.exists(filepath):
        print(f"Error: Batch file not found at {filepath}")
        return

    try:
        # Get the appropriate encoding for the specified model
        encoding = tiktoken.encoding_for_model(model_name)
        print(f"Using tokenizer for model: {model_name}")
    except KeyError:
        print(f"Warning: Model {model_name} not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception as e:
        print(f"Error initializing tokenizer: {e}")
        return

    print(f"Processing batch file: {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                try:
                    request = json.loads(line)
                    request_count += 1
                    
                    # Extract messages from the request body
                    messages = request.get("body", {}).get("messages", [])
                    
                    # Concatenate content from all messages for token counting
                    full_content = ""
                    for msg in messages:
                        content = msg.get("content", "")
                        if content:
                            # Add role prefix maybe? OpenAI cookbook suggests separators.
                            # Let's approximate by just joining content for now.
                            full_content += content + "\n" 
                            
                    # Encode and count tokens
                    tokens = encoding.encode(full_content)
                    total_tokens += len(tokens)

                    # Print progress periodically
                    if (line_num + 1) % 1000 == 0:
                        print(f"  Processed {line_num + 1} requests...")

                except json.JSONDecodeError:
                    print(f"Warning: Skipping malformed JSON line {line_num + 1}: {line.strip()[:100]}...")
                except Exception as e:
                    print(f"Error processing line {line_num + 1}: {e}")
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return
        
    print(f"\nFinished processing.")
    print(f"Total requests found: {request_count}")
    print(f"Estimated total tokens (input): {total_tokens:,}")

if __name__ == "__main__":
    estimate_tokens_in_batch_file(BATCH_FILE, MODEL_NAME) 