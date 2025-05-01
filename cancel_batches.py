import os
from openai import OpenAI
from dotenv import load_dotenv
import time

def load_api_key():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file or environment variables.")
    return api_key

def cancel_active_batches():
    try:
        api_key = load_api_key()
        client = OpenAI(api_key=api_key)
        print("OpenAI client initialized.")
    except ValueError as e:
        print(f"Error: {e}")
        return

    print("Fetching list of batch jobs...")
    try:
        batches_to_cancel = []
        # List batches, potentially needing pagination if many exist
        list_batches = client.batches.list(limit=100) 
        for batch in list_batches.data:
            # Check status: 'validating', 'in_progress', 'queued' indicate potentially active states
            # We might only need 'in_progress' and 'validating', but include 'queued' just in case.
            if batch.status in ['validating', 'in_progress', 'queued']:
                 batches_to_cancel.append(batch)

        if not batches_to_cancel:
            print("No active batch jobs found to cancel.")
            return

        print(f"Found {len(batches_to_cancel)} active batch jobs:")
        for batch in batches_to_cancel:
            print(f"  - ID: {batch.id}, Status: {batch.status}, Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(batch.created_at))}")

        confirm = input("Do you want to cancel all these jobs? (yes/no): ").lower()
        if confirm == 'yes':
            print("Cancelling jobs...")
            cancelled_count = 0
            failed_count = 0
            for batch in batches_to_cancel:
                try:
                    client.batches.cancel(batch.id)
                    print(f"  - Cancel request sent for batch ID: {batch.id}")
                    cancelled_count += 1
                    # Add a small delay to avoid hitting potential cancellation rate limits
                    time.sleep(0.5) 
                except Exception as e:
                    print(f"  - Failed to cancel batch ID {batch.id}: {e}")
                    failed_count += 1
            print(f"Cancellation process complete. Requested cancellation for {cancelled_count} jobs. Failed attempts: {failed_count}.")
        else:
            print("Cancellation aborted by user.")

    except Exception as e:
        print(f"An error occurred while listing or cancelling batches: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    cancel_active_batches() 