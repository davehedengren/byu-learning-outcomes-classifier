import os
import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import urllib3.exceptions
import csv
from bs4 import BeautifulSoup

# Configuration
COURSE_URLS_FILE = "course_urls.txt"
COURSE_PAGES_DIR = "course_pages"
TARGET_COURSE_ID = "08778-001" # For specific debugging
TARGET_HTML_FILE = os.path.join(COURSE_PAGES_DIR, f"course_{TARGET_COURSE_ID}.html")
TARGET_COURSE_URL = f"https://catalog.byu.edu/courses/{TARGET_COURSE_ID}" # Corresponding URL
OUTPUT_CSV = "learning_outcomes.csv"
MAX_RETRIES = 3
PAGES_BEFORE_RESTART = 100 # Increased for debugging

# CSV Header
CSV_HEADERS = [
    'course_name', 
    'course_url', 
    'course_title',
    'department', 
    'college', 
    'learning_outcome_id', 
    'learning_outcome_title', 
    'learning_outcome_details'
]

def setup_driver(reload=False):
    """Set up and return a configured Chrome webdriver"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    
    # Reduce memory usage
    options.add_argument("--js-flags=--expose-gc")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-background-timer-throttling")
    
    # Add random user-agent to avoid detection
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)} BYU Learning Outcomes Scraper")
    
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        
        if reload:
            print("Restarting Chrome driver...")
        
        return driver
    except Exception as e:
        print(f"Error creating Chrome driver: {e}")
        time.sleep(10)
        return webdriver.Chrome(options=options)

def restart_browser(driver):
    """Safely quit the existing driver and create a new one"""
    try:
        if driver:
            driver.quit()
    except:
        pass
    
    print("Doing a complete browser restart...")
    time.sleep(5)
    return setup_driver(reload=True)

def init_csv():
    """Initialize the CSV file with headers if it doesn't exist or is empty."""
    write_header = False
    if not os.path.exists(OUTPUT_CSV):
        write_header = True
    else:
        # Check if the existing file is empty
        try:
            if os.path.getsize(OUTPUT_CSV) == 0:
                write_header = True
            else:
                # Optional: Check if the first line matches the header
                with open(OUTPUT_CSV, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    try:
                        first_row = next(reader)
                        if first_row != CSV_HEADERS:
                            print(f"Warning: Existing CSV header {first_row} doesn't match expected {CSV_HEADERS}. Overwriting.")
                            write_header = True # Overwrite if header mismatch
                    except StopIteration:
                        # File exists but is empty
                        write_header = True
        except OSError:
            # Handle potential race conditions or permission errors
            write_header = True 

    if write_header:
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
        print(f"Initialized {OUTPUT_CSV} with headers.")

def download_html_if_missing(url, filepath):
    """Downloads HTML using Selenium if the target file doesn't exist."""
    if os.path.exists(filepath):
        print(f"HTML file already exists: {filepath}")
        return True

    print(f"HTML file not found. Downloading {url} to {filepath}...")
    driver = None
    try:
        driver = setup_driver()
        driver.get(url)
        # Wait for a basic element to ensure page is loaded somewhat
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
        )
        
        # Create directory if it doesn't exist
        os.makedirs(COURSE_PAGES_DIR, exist_ok=True)
        
        # Save the page source
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("HTML downloaded successfully.")
        return True
    except (TimeoutException, WebDriverException, Exception) as e:
        print(f"Error downloading HTML from {url}: {e}")
        # Attempt to delete potentially incomplete file
        if os.path.exists(filepath):
             try: os.remove(filepath) 
             except OSError: pass
        return False
    finally:
        if driver:
            try: driver.quit() 
            except: pass

def extract_course_data(html_content, course_url):
    """Extract the required data from the provided HTML content using BeautifulSoup."""
    results = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    course_name = "Unknown"
    course_title = "Unknown" # Initialize course_title
    department = "Unknown"
    college = "Unknown"

    try:
        # --- Course Name Extraction (BS4 - Attempt 5: Prioritize Title Tag) ---
        # --- Try Title Tag First ---
        try:
            title_tag = soup.select_one('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                if "|" in title_text:
                    potential_name = title_text.split("|")[0].strip()
                    if potential_name.endswith(" Course"):
                         potential_name = potential_name[:-len(" Course")].strip()
                    if any(char.isdigit() for char in potential_name) and any(char.isalpha() for char in potential_name):
                         course_name = potential_name
                    else:
                         pass
                else:
                     pass
            else:
                 pass
        except Exception as e:
             pass

        # --- Fallback to H1 Tag if Title didn't yield a result ---
        if course_name == "Unknown":
            h1 = soup.select_one("h1")
            if h1:
                full_text = h1.get_text(separator=" ", strip=True)
                suffix = "Course Catalog"
                if full_text.endswith(suffix):
                    potential_name = full_text[:-len(suffix)].strip()
                    if any(char.isdigit() for char in potential_name) and any(char.isalpha() for char in potential_name):
                         course_name = potential_name
                    else:
                         if any(char.isdigit() for char in full_text) and any(char.isalpha() for char in full_text):
                              course_name = full_text
                         else:
                              pass
            else:
                pass
        
        if not course_name or course_name == "Unknown": 
            course_name = "Unknown"

        # --- Course Title Extraction ---
        try:
            title_h2 = soup.select_one("h2.heading-5") # Target h2.heading-5
            if title_h2:
                 course_title = title_h2.get_text(strip=True)
            else:
                 # Fallback: Maybe just the first h2 inside the article?
                 article = soup.select_one("article")
                 if article:
                      first_h2 = article.select_one("h2")
                      if first_h2:
                           course_title = first_h2.get_text(strip=True)
        except Exception as e:
            print(f"Error extracting course title: {e}") # Keep print for this new field

        # --- Department and College Extraction (BS4 - Attempt 4: Structure from Image) ---
        try:
            info_div = soup.select_one("div.text-small.mb-10")
            if not info_div:
                 info_div = soup.select_one("article div.text-small") 

            if info_div:
                dept_link = info_div.select_one("a")
                if dept_link:
                    department = dept_link.get_text(strip=True)
                else:
                    pass

                college_spans = info_div.select("span")
                if college_spans:
                     college_span = college_spans[-1]
                     if college_span:
                         college = college_span.get_text(strip=True)
                         if not college and len(college_spans) > 1:
                              college = college_spans[-2].get_text(strip=True)
                         
                         if college: 
                              pass
                         else:
                              college = "Unknown" 
                else:
                    pass
            else:
                 try:
                     labels = soup.find_all('h3', class_='field-label')
                     for label in labels:
                         label_text = label.get_text(strip=True)
                         if 'Department' in label_text:
                             value_div = label.find_next_sibling('div', class_='field-value')
                             if value_div:
                                 link = value_div.find('a')
                                 if link:
                                     department = link.get_text(strip=True)
                                     if department == "Unknown": break 
                         elif 'College' in label_text:
                             value_div = label.find_next_sibling('div', class_='field-value')
                             if value_div:
                                 link = value_div.find('a')
                                 if link:
                                     college = link.get_text(strip=True)
                                     if college == "Unknown": break 
                 except Exception as fallback_e:
                      pass

        except Exception as e:
             pass
                        
        if not department or department.lower() == "department": department = "Unknown"
        if not college or college.lower() == "college": college = "Unknown"

        print(f"Extracted - Name: '{course_name}', Title: '{course_title}', Dept: '{department}', College: '{college}'")

        # --- Learning Outcomes Extraction (BS4 - Revised for Title/Details Pair) ---\
        learning_outcomes = []
        outcome_id = 1
        
        # Find the main Learning Outcomes section container
        lo_section = None
        h3_labels = soup.select("h3.field-label")
        for label in h3_labels:
            if "Learning Outcomes" in label.get_text(strip=True):
                lo_section = label.find_parent('div', class_=lambda x: x and ('field-component' in x or 'multi-field' in x))
                if lo_section: break # Found it
        
        if not lo_section:
             lo_section = soup.select_one("#learningOutcomes")

        if lo_section:
            # Look for the containers holding pairs of Title/Description
            # Based on example: <div class="flex w-full"> holds a pair
            # These might be directly under the field-value of the main section, or nested
            pair_containers = lo_section.select("div.field-value div.flex.w-full") 
            # Fallback if not nested under field-value
            if not pair_containers:
                 pair_containers = lo_section.select("div.flex.w-full")

            print(f"Found {len(pair_containers)} potential outcome pair containers.")

            for container in pair_containers:
                outcome_title = ""
                outcome_details = ""
                
                # Find Title within the pair container
                # Try finding the h3 label first
                title_label = container.find('h3', string=lambda t: t and 'Title' in t)
                if title_label:
                    title_value_div = title_label.find_next_sibling('div', class_='field-value')
                    if title_value_div:
                        outcome_title = title_value_div.get_text(strip=True)
                else:
                    # Fallback: Try finding div with data-test=name if label method fails
                    title_div = container.select_one('div[data-test="name"] div.field-value')
                    if title_div:
                         outcome_title = title_div.get_text(strip=True)
               
                # Find Learning Outcome (Details) within the pair container
                details_label = container.find('h3', string=lambda t: t and 'Learning Outcome' in t)
                if details_label:
                     details_value_div = details_label.find_next_sibling('div', class_='field-value')
                     if details_value_div:
                          outcome_details = details_value_div.get_text(strip=True)
                else:
                    # Fallback: Try finding div with data-test=objective if label method fails
                     details_div = container.select_one('div[data-test="objective"] div.field-value')
                     if details_div:
                          outcome_details = details_div.get_text(strip=True)

                # Only add if we found both title and details for this pair
                if outcome_title and outcome_details:
                    print(f"  Outcome Pair {outcome_id}: Title='{outcome_title[:30]}...', Details='{outcome_details[:50]}...'")
                    learning_outcomes.append({
                        'id': outcome_id,
                        'title': outcome_title,
                        'details': outcome_details
                    })
                    outcome_id += 1
                else:
                     print(f"  Skipping pair container - Title or Details missing. Title: '{outcome_title}', Details found: {bool(outcome_details)}")

            # If the pair logic failed, attempt the previous broader fallback (optional, can be removed if pair structure is consistent)
            if not learning_outcomes:
                print("Pair extraction failed, trying previous fallback methods...")
                lo_value_div = lo_section.select_one("div.field-value")
                if lo_value_div:
                    # Fallback 1: Direct divs under field-value (used for EC EN 199R)
                    outcome_entries = lo_value_div.select(":scope > div") 
                    if not outcome_entries: 
                        # Fallback 2: List items or paragraphs
                        outcome_entries = lo_value_div.select("li, p")
                    
                    print(f"Found {len(outcome_entries)} potential outcome entries using direct div/li/p fallback.")
                    for entry in outcome_entries:
                        raw_details = entry.get_text(strip=True)
                        if raw_details:
                             # Use raw text as details, generate generic title
                             print(f"  Fallback Outcome {outcome_id}: Details='{raw_details[:50]}...'")
                             learning_outcomes.append({
                                 'id': outcome_id,
                                 'title': f"Outcome {outcome_id}", # Generic title for this fallback
                                 'details': raw_details
                             })
                             outcome_id += 1

        else:
             print("Could not find Learning Outcomes section.")
             
        # Create result rows
        if learning_outcomes:
            for outcome in learning_outcomes:
                results.append({
                    'course_name': course_name,
                    'course_url': course_url,
                    'course_title': course_title,
                    'department': department,
                    'college': college,
                    'learning_outcome_id': outcome['id'],
                    'learning_outcome_title': outcome['title'],
                    'learning_outcome_details': outcome['details']
                })
        else:
            # If no learning outcomes found by any method
            print("No learning outcomes extracted for this course.")
            results.append({
                'course_name': course_name,
                'course_url': course_url,
                'course_title': course_title,
                'department': department,
                'college': college,
                'learning_outcome_id': "",
                'learning_outcome_title': "",
                'learning_outcome_details': "No learning outcomes found"
            })
    
    except Exception as e:
        print(f"Error extracting data from HTML for {course_url}: {e}")
        # Return partial data if possible, or None
        if not results:
            results.append({ # Ensure at least one row with what we have
                    'course_name': course_name if course_name != "Unknown" else "",
                    'course_url': course_url,
                    'course_title': course_title if course_title != "Unknown" else "", # Added course_title
                    'department': department if department != "Unknown" else "",
                    'college': college if college != "Unknown" else "",
                    'learning_outcome_id': "",
                    'learning_outcome_title': "",
                    'learning_outcome_details': f"Extraction Error: {e}"
                })
    
    return results

def write_rows_to_csv(rows):
    """Append new rows to the CSV file"""
    if not rows:
        return
        
    # Determine if header needs writing (in case init_csv failed or file deleted)
    write_header = False
    if not os.path.exists(OUTPUT_CSV) or os.path.getsize(OUTPUT_CSV) == 0:
        write_header = True

    with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if write_header:
             print("Writing header to CSV...")
             writer.writeheader()
        for row in rows:
            writer.writerow(row)
    
    print(f"Added {len(rows)} rows to {OUTPUT_CSV}")

def main():
    print("Starting course page scraper...")
    
    # Get the list of course URLs to scrape
    all_urls = []
    if os.path.exists(COURSE_URLS_FILE):
        with open(COURSE_URLS_FILE, 'r', encoding='utf-8') as f:
            all_urls = [line.strip() for line in f if line.strip()]
    if not all_urls:
        print(f"Error: {COURSE_URLS_FILE} not found or empty. Run catalog scraper first. Exiting.")
        return
    
    print(f"Found {len(all_urls)} total course URLs to process")
    
    # Initialize the output CSV 
    init_csv()
    
    # Get already processed URLs to avoid duplicates
    processed_urls = set()
    if os.path.exists(OUTPUT_CSV):
        try:
            # Read only the necessary column
            df = pd.read_csv(OUTPUT_CSV, usecols=['course_url'], low_memory=False) 
            processed_urls = set(df['course_url'].unique())
        except (FileNotFoundError, pd.errors.EmptyDataError, ValueError) as e:
            print(f"Could not read processed URLs from {OUTPUT_CSV}: {e}. Starting fresh or appending.")
        except Exception as e:
            print(f"Unexpected error reading {OUTPUT_CSV}: {e}.")
            
    print(f"Already processed {len(processed_urls)} course URLs")
    
    # Filter out already processed URLs
    urls_to_scrape = [url for url in all_urls if url not in processed_urls]
    print(f"Remaining URLs to scrape: {len(urls_to_scrape)}")
    
    if not urls_to_scrape:
        print("All URLs already processed. Exiting.")
        return

    # Main scraping loop
    total_scraped_this_run = 0
    try:
        for i, course_url in enumerate(urls_to_scrape):
            print(f"\nProcessing URL {i+1}/{len(urls_to_scrape)}: {course_url}")
            course_id = course_url.split("/")[-1]
            target_html_file = os.path.join(COURSE_PAGES_DIR, f"course_{course_id}.html")

            # Ensure HTML file exists, download if not
            if not download_html_if_missing(course_url, target_html_file):
                print(f"Skipping {course_url} due to download failure.")
                continue # Skip to next URL

            # Read the local HTML file content
            try:
                with open(target_html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except Exception as e:
                print(f"Error reading HTML file {target_html_file}: {e}. Skipping.")
                continue # Skip to next URL
            
            # Extract data using BeautifulSoup
            course_data_list = extract_course_data(html_content, course_url)
            
            if course_data_list:
                write_rows_to_csv(course_data_list)
                total_scraped_this_run += 1 # Count successful scrapes
            else:
                 print(f"No data extracted for {course_url}.")
            
            # Random delay between requests (applied after processing)
            if i < len(urls_to_scrape) - 1:
                delay = random.uniform(1, 2) # Original delay range
                print(f"Waiting {delay:.2f} seconds before next request...")
                time.sleep(delay)

    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Progress has been saved.")
    finally:
        # No driver to quit here as it's handled in download_html_if_missing
        pass 
        
    # Print summary
    final_processed_count = len(processed_urls) + total_scraped_this_run
    print(f"\nScraper finished. Scraped {total_scraped_this_run} new courses this run.")
    print(f"Total courses in {OUTPUT_CSV}: {final_processed_count}")

if __name__ == "__main__":
    main() 