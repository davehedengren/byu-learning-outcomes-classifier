import pandas as pd
import re
import html
import argparse
import csv
import os
import io

def clean_text(text):
    """Clean text by removing line breaks and HTML entities."""
    if pd.isna(text):
        return text
    
    # Convert to string in case it's not
    text = str(text)
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Replace line breaks with spaces
    text = re.sub(r'\n+', ' ', text)
    
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove any trailing/leading whitespace
    text = text.strip()
    
    return text

def clean_csv(input_file, output_file):
    """Clean a CSV file by processing all text fields."""
    try:
        print(f"Reading file: {input_file}")
        
        # Try different encodings and reading methods
        encodings_to_try = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        file_content = None
        
        # First check if file exists and has content
        if not os.path.exists(input_file):
            print(f"Error: File {input_file} does not exist")
            return
            
        file_size = os.path.getsize(input_file)
        if file_size == 0:
            print(f"Error: File {input_file} is empty (0 bytes)")
            return
            
        print(f"File size: {file_size} bytes")
        
        # Try different encodings to read the file
        for encoding in encodings_to_try:
            try:
                with open(input_file, 'r', encoding=encoding) as f:
                    file_content = f.read()
                print(f"Successfully read file using {encoding} encoding")
                break
            except UnicodeDecodeError:
                print(f"Failed to read with {encoding} encoding")
            except Exception as e:
                print(f"Error reading file with {encoding} encoding: {e}")
        
        if not file_content:
            print("Could not read file with any encoding, trying binary mode")
            try:
                with open(input_file, 'rb') as f:
                    file_content = f.read().decode('utf-8', errors='replace')
                print("Successfully read file in binary mode with UTF-8 decoding")
            except Exception as e:
                print(f"Error reading file in binary mode: {e}")
                return
        
        if not file_content or not file_content.strip():
            print("File content appears to be empty after reading")
            return
            
        # Check if it's a valid CSV by looking for commas
        comma_count = file_content.count(',')
        if comma_count < 5:  # Unlikely to be a proper CSV with our expected columns
            print(f"Warning: File doesn't appear to be a standard CSV (only {comma_count} commas found)")
        
        # Create a StringIO object to use with pandas
        csv_data = io.StringIO(file_content)
        
        # Try different parameters to read the CSV
        print("Attempting to read with regular parameters...")
        try:
            df = pd.read_csv(csv_data)
            csv_data.seek(0)  # Reset position for potential reuse
        except Exception as e:
            print(f"First attempt failed: {e}")
            print("Trying with error_bad_lines=False...")
            try:
                csv_data.seek(0)
                df = pd.read_csv(csv_data, on_bad_lines='skip')
            except Exception as e:
                print(f"Second attempt failed: {e}")
                print("Trying with quote character settings...")
                try:
                    csv_data.seek(0)
                    df = pd.read_csv(csv_data, quoting=csv.QUOTE_MINIMAL)
                except Exception as e:
                    print(f"Third attempt failed: {e}")
                    print("Trying with more lenient parsing...")
                    try:
                        csv_data.seek(0)
                        # Most permissive reading - may not handle quotes properly but will read something
                        df = pd.read_csv(csv_data, quoting=csv.QUOTE_NONE, sep=',', 
                                     escapechar='\\', engine='python')
                    except Exception as e:
                        print(f"All attempts failed. Last error: {e}")
                        print("Trying alternative approach with manual CSV parsing...")
                        
                        # Manual parsing as last resort
                        try:
                            rows = []
                            csv_data.seek(0)
                            lines = csv_data.readlines()
                            
                            if not lines:
                                print("No lines found in file")
                                return
                                
                            # Get the first line for headers
                            header_line = lines[0]
                            try:
                                headers = next(csv.reader([header_line]))
                            except Exception as he:
                                print(f"Error parsing header line: {he}")
                                print(f"Header line: {header_line[:100]}...")
                                headers = header_line.strip().split(',')
                                print(f"Using simple split headers: {headers}")
                            
                            if not headers:
                                print("Failed to extract headers from file")
                                return
                                
                            print(f"Found headers: {headers}")
                            
                            # Read remaining lines
                            for i, line in enumerate(lines[1:], start=2):
                                if i % 1000 == 0:
                                    print(f"Processing line {i}...")
                                
                                # Skip empty lines
                                if not line.strip():
                                    continue
                                
                                # Handle potential multiline values enclosed in quotes
                                if line.count('"') % 2 == 1:  # Odd number of quotes means we're in a multiline field
                                    temp = line
                                    j = i
                                    while j < len(lines):
                                        next_line = lines[j]
                                        temp += next_line
                                        if next_line.count('"') % 2 == 1:
                                            break
                                        j += 1
                                    line = temp
                                
                                # Try to parse the line
                                try:
                                    row_values = next(csv.reader([line]))
                                    # Make sure we have the right number of columns
                                    while len(row_values) < len(headers):
                                        row_values.append("")
                                    if len(row_values) > len(headers):
                                        row_values = row_values[:len(headers)]
                                    rows.append(row_values)
                                except Exception as row_error:
                                    print(f"Skipping problematic line {i}: {line[:50]}... Error: {row_error}")
                            
                            # Convert to dataframe
                            df = pd.DataFrame(rows, columns=headers)
                            print(f"Manual parsing succeeded, found {len(df)} rows")
                        except Exception as manual_error:
                            print(f"Manual parsing also failed: {manual_error}")
                            raise Exception("Could not parse the CSV file with any method")
        
        # Get original columns for reference
        columns = df.columns.tolist()
        print(f"Found {len(columns)} columns: {', '.join(columns)}")
        print(f"Found {len(df)} rows")
        
        # Sample before cleaning
        print("\nSample before cleaning:")
        if len(df) > 0:
            sample_row = df.iloc[0].to_dict()
            for col, val in sample_row.items():
                print(f"{col}: {val}")
        else:
            print("No rows found to sample")
        
        # Apply cleaning to all string columns
        for col in df.columns:
            if df[col].dtype == 'object':  # String columns
                print(f"Cleaning column: {col}")
                df[col] = df[col].apply(clean_text)
        
        # Sample after cleaning
        print("\nSample after cleaning:")
        if len(df) > 0:
            sample_row = df.iloc[0].to_dict()
            for col, val in sample_row.items():
                print(f"{col}: {val}")
        else:
            print("No rows found to sample")
        
        # Check if the directory exists, create if not
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Write to output file
        print(f"\nWriting cleaned data to: {output_file}")
        df.to_csv(output_file, index=False, quoting=csv.QUOTE_ALL)
        
        print(f"Successfully cleaned {len(df)} rows and saved to {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean CSV files by handling line breaks and HTML entities")
    parser.add_argument("--input", type=str, required=True, help="Input CSV file to clean")
    parser.add_argument("--output", type=str, required=True, help="Output CSV file to save cleaned data")
    
    args = parser.parse_args()
    
    clean_csv(args.input, args.output) 